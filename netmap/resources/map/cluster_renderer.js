'use strict';
class ClusterRenderer {
 constructor(){this.key=null;this.buckets=null;this.hits=0;}
 group(points,zoom,map){
  const key=zoom+'|'+points.map(p=>`${p.ip}:${p.latitude}:${p.longitude}`).join(';');
  if(key===this.key){this.hits++;return this.buckets;}
  const groups=new Map();
  for(const p of points){const pixel=map.project([p.latitude,p.longitude],zoom);const k=`${Math.floor(pixel.x/38)}:${Math.floor(pixel.y/38)}`;if(!groups.has(k))groups.set(k,[]);groups.get(k).push(p.ip);}
  this.key=key;this.buckets=[...groups.values()].map(ips=>ips.sort());return this.buckets;
 }
 prepare(sizes){this.sorted=sizes.filter(n=>n>1).sort((a,b)=>a-b);}
 style(count){
  const sorted=this.sorted||[];
  const quantile=q=>sorted[Math.floor((sorted.length-1)*q)]||2;
  const rank=count<=quantile(.25)?0:count<=quantile(.5)?1:count<=quantile(.8)?2:3;
  return {color:['#609c88','#b9a35e','#c38b5f','#bc7564'][rank],size:Math.min(58,Math.max(28,22+7*Math.log2(count))),rank};
 }
}
class DensityLayer extends L.Layer {
 onAdd(map){this.map=map;this.canvas=L.DomUtil.create('canvas','density-canvas',map.getPane('overlayPane'));this.canvas.style.pointerEvents='none';this.redraw=this.draw.bind(this);map.on('moveend zoomend resize',this.redraw);this.draw();}
 onRemove(map){map.off('moveend zoomend resize',this.redraw);this.canvas.remove();this.map=null;this.canvas=null;}
 setPoints(points){this.points=points;if(this.map&&this.canvas)this.draw();return this;}
 draw(){
  if(!this.canvas)return;
  const start=performance.now(),size=this.map.getSize(),dpr=Math.min(devicePixelRatio||1,2);
  this.canvas.width=size.x*dpr;this.canvas.height=size.y*dpr;this.canvas.style.width=size.x+'px';this.canvas.style.height=size.y+'px';
  L.DomUtil.setPosition(this.canvas,this.map.containerPointToLayerPoint([0,0]));
  const ctx=this.canvas.getContext('2d');ctx.scale(dpr,dpr);
  const cells=new Map(),seen=new Set();
  for(const p of this.points||[]){if(seen.has(p.ip))continue;seen.add(p.ip);const v=this.map.latLngToContainerPoint([p.latitude,p.longitude]);if(v.x< -50||v.x>size.x+50||v.y< -50||v.y>size.y+50)continue;const k=Math.floor(v.x/24)+':'+Math.floor(v.y/24);const c=cells.get(k)||{x:0,y:0,n:0};c.x+=v.x;c.y+=v.y;c.n++;cells.set(k,c);}
  const maximum=Math.max(1,...[...cells.values()].map(c=>c.n));
  for(const c of cells.values()){const x=c.x/c.n,y=c.y/c.n,weight=c.n===1?.15:Math.log1p(c.n)/Math.log1p(maximum),r=22+18*weight;const gradient=ctx.createRadialGradient(x,y,0,x,y,r);gradient.addColorStop(0,weight>.8?'rgba(188,117,100,.70)':weight>.5?'rgba(195,139,95,.65)':'rgba(96,156,136,.60)');gradient.addColorStop(1,'rgba(96,156,136,0)');ctx.fillStyle=gradient;ctx.fillRect(x-r,y-r,r*2,r*2);}
  window.mapPerformance.density_ms=performance.now()-start;
 }
}
