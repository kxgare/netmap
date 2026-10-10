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
state={'data':False,'click':False,'limit':False,'clear':False,'reuse':False,'focus':False}
fixture={'ip':'8.8.8.8','latitude':37.751,'longitude':-97.822,'country':'Тестовая запись','city':'',
         'accuracy_km':1000,'active':True,'connections':[{'process':'<test.exe>','pid':1,'protocol':'TCP','port':443,'status':'ESTABLISHED'}],
         'first':'2026-10-10T10:00:00+00:00','last':'2026-10-10T10:00:02+00:00'}
points=[fixture,{**fixture,'ip':'1.1.1.1'},{**fixture,'ip':'9.9.9.9','latitude':48.85,'longitude':2.35,'active':False}]


def checked(result):
    value=json.loads(result)
    state['data']=value['points']==3 and value['groups']==2 and value['escaped']
    print('MAP FIXTURE',value,flush=True)
    view.page().runJavaScript("window.savedMarkers=[...objects.values()].map(item=>item.marker)")
    view.update_data(points,Settings())
    view.page().runJavaScript("JSON.stringify({reuse:savedMarkers.every(marker=>[...objects.values()].some(item=>item.marker===marker)),focus:window.focusIP('9.9.9.9')})",reused)
    view.page().runJavaScript("bridge.select('8.8.8.8')")
    # Limit protects total markers; a large input should not create one object per IP.
    many=[{**fixture,'ip':f'test-{i}'} for i in range(1500)]
    view.update_data(many,Settings(map_limit=100,origin_enabled=True))
    QTimer.singleShot(300,check_limit)


def reused(result):
    value=json.loads(result);state['reuse']=value['reuse'];state['focus']=value['focus']

def check_limit():
    view.page().runJavaScript("JSON.stringify({count:document.getElementById('counter').textContent,layers:layer.getLayers().length})",limited)


def limited(result):
    value=json.loads(result)
    state['limit']='100 / 1500' in value['count'] and value['layers']<=5
    view.update_data([],Settings())
    QTimer.singleShot(300,check_clear)


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
