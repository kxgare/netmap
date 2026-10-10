"""Isolated synthetic benchmark. Never imported by the monitoring application."""
import json, os, tempfile
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('NETMAP_DATA_DIR',tempfile.mkdtemp(prefix='netmap-benchmark-'))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from netmap.ui.map_view import MapView
app=QApplication([]); view=MapView(); view.resize(1100,700); view.show()
source="""(()=>{const results=[];for(const count of [50,200,500,1000]){const points=Array.from({length:count},(_,i)=>({ip:'fixture-'+i,latitude:-55+(i*37%130),longitude:-170+(i*71%340),active:true,connections:[{process:'benchmark',pid:1,protocol:'TCP',port:443,status:'ESTABLISHED'}],first:'fixture',last:'fixture'}));payload={points,limit:1000,animations:false,origin:null,tiles:false,mode:'simple'};const times=[];for(let j=0;j<21;j++){const start=performance.now();draw();times.push(performance.now()-start);}const first=times.shift();times.sort((a,b)=>a-b);results.push({ips:count,first_ms:first,median_ms:times[10],p95_ms:times[18],objects:objects.size});if(window.measureDensity&&typeof DensityLayer!=="undefined"){payload.representation="density";const heat=[];for(let j=0;j<21;j++){const start=performance.now();draw();heat.push(performance.now()-start);}heat.shift();heat.sort((a,b)=>a-b);results[results.length-1].density_median_ms=heat[10];results[results.length-1].density_p95_ms=heat[18];payload.representation="points";}}return JSON.stringify({viewport:[innerWidth,innerHeight],zoom:map.getZoom(),results});})()"""
def done(result):
 print(result,flush=True); view.dispose(); QTimer.singleShot(100,view.close)
def loaded(ok):
 if not ok: app.exit(1); return
 view.page().runJavaScript('window.measureDensity='+('true' if os.environ.get('NETMAP_BENCHMARK_DENSITY') else 'false'))
 QTimer.singleShot(500,lambda:view.page().runJavaScript(source,done))
view.ready.connect(loaded);
if os.environ.get('NETMAP_BENCHMARK_MAP'):
 from PySide6.QtCore import QUrl
 view.setUrl(QUrl.fromLocalFile(str(Path(os.environ['NETMAP_BENCHMARK_MAP'])/'index.html')))
QTimer.singleShot(30000,lambda:app.exit(2)); raise SystemExit(app.exec())
