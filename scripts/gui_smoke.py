"""GUI integration test with a real loopback socket. No fabricated runtime data.

Run from the repository root. For Linux headless checks:
QT_QPA_PLATFORM=offscreen NETMAP_DATA_DIR=/tmp/netmap-gui-test python scripts/gui_smoke.py
"""
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading

# Never open the user's production database during smoke checks.
os.environ.setdefault('NETMAP_DATA_DIR',tempfile.mkdtemp(prefix='netmap-gui-'))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from netmap.core.settings import Settings
from netmap.ui.main_window import MainWindow

app=QApplication([])
server=socket.socket(); server.bind(('127.0.0.1',0)); server.listen(1)
client=socket.socket(); client.connect(server.getsockname())
accepted,_=server.accept()
def serve_diagnostics():
    for _ in range(5):
        sock,_=server.accept()
        sock.close()
threading.Thread(target=serve_diagnostics,daemon=True).start()
window=MainWindow(Settings(interval=.5))
window.show()
state={'snapshot':False,'map':False,'history':False,'pause':False,'diagnostic':False,'closed':False}
errors=[]


def fail(message):
    errors.append(message)
    print('FAIL:',message,flush=True)


def snapshot(payload):
    if any(c.local_port==client.getsockname()[1] and c.protocol=='TCP' for c in payload['connections']):
        state['snapshot']=True


window.worker.updated.connect(snapshot)
window.worker.error.connect(fail)
window.worker.history_ready.connect(lambda p: state.update(history=bool(p['rows'])))
window.worker.diagnostics_ready.connect(lambda r: state.update(diagnostic=bool(r)))


def map_check(result):
    try:
        value=json.loads(result)
        state['map']=value['leaflet']=='object' and value['world']>100 and value['bridge']
        print('MAP:',value,flush=True)
    except Exception as exc: fail(f'JavaScript: {exc}; result={result!r}')


def check_pages():
    for i in range(6): window.navigate(i)
    window.map_page.map.page().runJavaScript("JSON.stringify({leaflet:typeof L,world:window.WORLD.features.length,bridge:!!bridge})",map_check)
    window.navigate(0)
    screenshot=Path(os.environ['NETMAP_DATA_DIR'])/'smoke.png'
    window.grab().save(str(screenshot))
    print('SCREENSHOT:',screenshot,flush=True)
    window.toggle_monitor()
    QTimer.singleShot(750,check_pause)


def check_pause():
    state['pause']=not window.worker.enabled
    window.toggle_monitor()
    window.start_probe('127.0.0.1',server.getsockname()[1])


def finish():
    print('CHECKS:',state,flush=True)
    if not all(state[k] for k in ('snapshot','map','history','pause','diagnostic')):
        fail('Required check did not complete')
    window.close()


def closed():
    state['closed']=True


window.thread.finished.connect(closed)
QTimer.singleShot(2200,check_pages)
QTimer.singleShot(5500,finish)
QTimer.singleShot(12000,lambda: (fail('Shutdown timed out'),app.exit(2)))
exit_code=app.exec()
for sock in (accepted,client,server): sock.close()
if errors or not all(state.values()):
    print('FAILED',state,errors)
    raise SystemExit(1)
print('GUI SMOKE PASSED: real collector, history, local Leaflet/WebChannel, pause/resume, TCP diagnostics, orderly shutdown')
raise SystemExit(exit_code)
