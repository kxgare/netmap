'use strict';
window.mapPerformance={draw_ms:0,cluster_ms:0,density_ms:0,updates:0,deferred:0};
class MapPerformanceManager {
 constructor(map,render){this.map=map;this.render=render;this.moving=false;this.pending=false;this.timer=null;map.on('movestart zoomstart',()=>{this.moving=true;});map.on('moveend',()=>{this.moving=false;if(this.pending)this.request();});map.on('zoomend',()=>{this.moving=false;this.request();});}
 request(){this.pending=true;if(this.moving){window.mapPerformance.deferred++;return;}if(this.timer)return;this.timer=setTimeout(()=>{this.timer=null;if(this.moving)return;this.pending=false;requestAnimationFrame(()=>{if(!this.moving)this.render();else this.pending=true;});},80);}
}
