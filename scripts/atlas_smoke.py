"""Version 0.2 interactions and screenshots, using only live collected data."""
import json,os,tempfile,socket
from dataclasses import replace
from pathlib import Path
os.environ.setdefault('NETMAP_DATA_DIR',tempfile.mkdtemp(prefix='netmap-atlas-'))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from netmap.core.settings import Settings
from netmap.ui.main_window import MainWindow

server=socket.socket();server.bind(("127.0.0.1",0));server.listen(1)
app=QApplication([])
window=MainWindow(Settings(interval=.5,onboarding_done=True)); window.show()
state={'modes':False,'navigation':False,'theme':False,'small':False,'history':False,'shutdown':False}
errors=[]
window.worker.error.connect(errors.append)
root=Path(os.environ['NETMAP_DATA_DIR'])

def capture(name):
    app.processEvents(); window.grab().save(str(root/(name+'.png')))

def interactions():
    capture('atlas-initial')
    page=window.connections_page
    window.navigate(1); window.set_mode('expert'); page.search.setText('127')
    page.table.setCurrentIndex(page.proxy.index(0,0))
    selected=page.selected().key if page.selected() else None
    window.set_mode('simple'); window.set_mode('expert')
    state['modes']=page.search.text()=='127' and (not selected or page.selected().key==selected) and Settings.load().mode=='expert'
    for i in range(6):
        window.navigate(i)
        if window.pages.currentIndex()!=i: raise AssertionError('Navigation')
    state['navigation']=True
    window.navigate(4); window.history_page.query()
    window.worker.history_ready.connect(history)
    window.apply_settings(replace(window.settings,theme='light',mode='simple'))
    window.navigate(0)
    QTimer.singleShot(700,light)

def history(payload):
    if payload['query'].get('_target')=='history': state['history']=payload.get('total',0)>0 and len(payload['rows'])>0

def light():
    capture('atlas-light')
    window.map_page.map.page().runJavaScript("JSON.stringify({ocean:getComputedStyle(document.documentElement).getPropertyValue('--ocean'),light:payload.palette.bg})",palette)
    window.resize(980,640)
    QTimer.singleShot(350,small)

def palette(result):
    value=json.loads(result); state['theme']=value['light']=='#f5f3ed' and value['ocean']=='#dce6e6'

def small():
    capture('atlas-small')
    nav=window.navigation; buttons=nav.buttons+list(nav.modes.values())
    state['small']=all(a.geometry().right()<b.geometry().left() for a,b in zip(buttons,buttons[1:])) and buttons[-1].geometry().right()<nav.width()
    window.resize(1440,900); window.apply_settings(replace(window.settings,theme='dark',mode='simple')); window.navigate(0)
    QTimer.singleShot(400,dark)

def dark():
    capture("atlas-dark")
    window.set_mode("expert"); window.navigate(1)
    QTimer.singleShot(400,expert)

def expert():
    capture('atlas-expert')
    print('ATLAS',state,'screenshots:',root,flush=True)
    window.close()

window.thread.finished.connect(lambda:state.update(shutdown=True))
QTimer.singleShot(2000,interactions)
QTimer.singleShot(12000,lambda:app.exit(2))
code=app.exec()
server.close()
assert not code and all(state.values()) and not errors,(state,errors)
print('ATLAS SMOKE PASSED')
