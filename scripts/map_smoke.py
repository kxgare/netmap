"""Isolated map fixture test, including grouping, filters and Qt click bridge.

The points are test fixtures, never included in production monitoring.
"""
import json
import os
import tempfile
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('NETMAP_DATA_DIR',tempfile.mkdtemp(prefix='netmap-map-'))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from netmap.core.settings import Settings
from netmap.ui.map_view import MapView

app=QApplication([])
view=MapView()
view.resize(1100,700)
view.show()
state={'data':False,'click':False,'limit':False,'clear':False,'reuse':False,'focus':False,'unique':False,'density':False,'zoom':False,'deferred':False,'styles':False}
fixture={'ip':'8.8.8.8','latitude':37.751,'longitude':-97.822,'country':'Тестовая запись','city':'',
         'accuracy_km':1000,'active':True,'connections':[{'process':'<test.exe>','pid':1,'protocol':'TCP','port':443,'status':'ESTABLISHED'}],
         'first':'2026-10-10T10:00:00+00:00','last':'2026-10-10T10:00:02+00:00'}
points=[fixture,{**fixture,'ip':'1.1.1.1'},{**fixture,'ip':'9.9.9.9','latitude':48.85,'longitude':2.35,'active':False}]


def checked(result):
    value=json.loads(result)
    state['data']=value['points']==3 and value['groups']==2 and value['escaped']
    print('MAP FIXTURE',value,flush=True)
    view.page().runJavaScript("window.fixturePoint=payload.points[0];window.savedMarkers=[...objects.values()].map(item=>item.marker)")
    view.update_data(points,Settings())
    view.page().runJavaScript("JSON.stringify({reuse:savedMarkers.every(marker=>[...objects.values()].some(item=>item.marker===marker)),focus:window.focusIP('9.9.9.9')})",reused)
    view.page().runJavaScript("bridge.select('8.8.8.8')")
    # Limit protects total markers; a large input should not create one object per IP.
    many=[{**fixture,'ip':f'test-{i}'} for i in range(1500)]
    view.update_data(many,Settings(map_limit=100,origin_enabled=True))
    QTimer.singleShot(650,check_limit)


def reused(result):
    value=json.loads(result);state['reuse']=value['reuse'];state['focus']=value['focus']

def check_limit():
    view.page().runJavaScript("JSON.stringify({count:document.getElementById('counter').textContent,layers:layer.getLayers().length})",limited)


def limited(result):
    value=json.loads(result)
    state['limit']='100 / 1500' in value['count'] and value['layers']<=5
    view.update_data([],Settings())
    QTimer.singleShot(650,check_density)


def check_density():
    # Duplicate fixture IPs must count once, regardless of socket metadata.
    view.page().runJavaScript("""payload={...payload,points:[...Array.from({length:25},(_,i)=>({...window.fixturePoint,ip:'unique-'+i})),window.fixturePoint,window.fixturePoint],limit:1000,representation:'density'};draw();JSON.stringify({unique:document.getElementById('counter').textContent.includes('26 /'),density:map.hasLayer(densityLayer)&&densityLayer.canvas.width>0})""",density_checked)

def density_checked(result):
    value=json.loads(result);state['unique']=value['unique'];state['density']=value['density']
    view.page().runJavaScript("""payload={...payload,points:[{...window.fixturePoint,ip:'a',latitude:20,longitude:0},{...window.fixturePoint,ip:'b',latitude:20,longitude:1}],representation:'points'};map.setZoom(2,{animate:false});draw();const low=objects.size;map.setZoom(10,{animate:false});draw();const zoom=objects.size>low;clusterRenderer.prepare([2,3,10,100]);const small=clusterRenderer.style(2),large=clusterRenderer.style(100);const before=mapPerformance.updates;map.fire('movestart');updateNetMap(payload);JSON.stringify({zoom,styles:large.size>small.size&&large.color!==small.color,deferred:scheduler.moving&&scheduler.pending&&mapPerformance.updates===before})""",map_checked)

def map_checked(result):
    value=json.loads(result)
    for key in ('zoom','styles','deferred'):state[key]=value[key]
    view.page().runJavaScript("map.fire('moveend')")
    view.last_serialized=None;view.update_data([],Settings())
    QTimer.singleShot(650,check_clear)

def check_clear():
    view.page().runJavaScript("JSON.stringify({empty:document.getElementById('empty').style.display,layers:layer.getLayers().length})",cleared)


def cleared(result):
    value=json.loads(result)
    state['clear']=value['empty']=='block' and value['layers']==0
    print('RESULT',state,flush=True)
    view.dispose()
    QTimer.singleShot(100,view.close)


def loaded(ok):
    if not ok:
        app.exit(1); return
    view.update_data(points,Settings())
    QTimer.singleShot(400,lambda:view.page().runJavaScript("JSON.stringify({points:payload.points.length,groups:layer.getLayers().length,escaped:popup(payload.points[0]).includes('&lt;test.exe&gt;')})",checked))


view.ready.connect(loaded)
view.bridge.selected.connect(lambda ip:state.update(click=ip=='8.8.8.8'))
QTimer.singleShot(12000,lambda:app.exit(2))
code=app.exec()
if code or not all(state.values()): raise SystemExit(1)
print('MAP SMOKE PASSED: clustered markers, escaped popup, Qt selection, 100-object limit, empty state')
