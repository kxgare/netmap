'use strict';
const map=L.map('map',{zoomControl:true,preferCanvas:true,minZoom:1,maxZoom:12,worldCopyJump:true}).setView([22,10],2);
map.attributionControl.setPrefix(false); map.attributionControl.addAttribution('Natural Earth');
const world=L.geoJSON(window.WORLD,{interactive:false,style:{color:'#9e9b8e',weight:.6,fillColor:'#d4c0aa',fillOpacity:1}}).addTo(map);
const canvas=L.canvas({padding:.3});
const layer=L.layerGroup().addTo(map),lines=L.layerGroup().addTo(map);
const objects=new Map(),lineObjects=new Map();
let paletteKey=null;
let bridge=null,selectedIP=null,payload={points:[],limit:500,animations:false,origin:null,tiles:false,mode:'simple'},tiles=null,originMarker=null;
const escapeHTML=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
new QWebChannel(qt.webChannelTransport,c=>{bridge=c.objects.bridge;});
function popup(p){
 const technical=payload.mode==='expert';
 const rows=p.connections.map(c=>technical?`${escapeHTML(c.process)} · PID ${escapeHTML(c.pid??'—')}<br>${escapeHTML(c.protocol)} : ${escapeHTML(c.port)} · ${escapeHTML(c.status)}`:escapeHTML(c.process)).join('<br>');
 return `<b>${escapeHTML(p.ip)}</b><br>${escapeHTML(p.country||'Страна не определена')} · ${escapeHTML(p.city||'')}<p>${rows||'Ранее обнаруженный адрес'}</p><small>Геолокация приблизительная${p.accuracy_km?' · радиус '+escapeHTML(p.accuracy_km)+' км':''}${technical?'<br>Первое: '+escapeHTML(p.first)+'<br>Последнее: '+escapeHTML(p.last):''}</small>`;
}
function draw(){
 const points=payload.points.slice().sort((a,b)=>Number(b.active)-Number(a.active)).slice(0,payload.limit);
 const buckets=new Map();
 for(const p of points){const pixel=map.project([p.latitude,p.longitude],map.getZoom());const key=`${Math.floor(pixel.x/38)}:${Math.floor(pixel.y/38)}`;if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(p);}
 const keep=new Set(),keepLines=new Set();let n=0;
 if(payload.origin){if(!originMarker)originMarker=L.circleMarker(payload.origin,{radius:6,color:'#c3a36c',weight:2,renderer:canvas}).bindTooltip('Исходная точка').addTo(map);else originMarker.setLatLng(payload.origin);}
 else if(originMarker){map.removeLayer(originMarker);originMarker=null;}
 for(const bucket of buckets.values()){
  bucket.sort((a,b)=>a.ip.localeCompare(b.ip));const p=bucket[0],position=[p.latitude,p.longitude];const cluster=bucket.length>1;
  const key=(cluster?'group:':'ip:')+bucket.map(p=>p.ip).join(',');keep.add(key);
  let item=objects.get(key);
  if(!item){
   const marker=cluster?L.marker(position,{icon:L.divIcon({className:'cluster',html:String(bucket.length),iconSize:[32,32],iconAnchor:[16,16]})}):L.circleMarker(position,{radius:5,weight:1.5,renderer:canvas});
   marker.addTo(layer);item={marker,content:null};objects.set(key,item);
   marker.on('click',()=>{const current=item.bucket;if(current.length>1&&map.getZoom()<12){map.setView(marker.getLatLng(),Math.min(12,map.getZoom()+2));return;}selectedIP=current[0].ip;marker.openPopup();if(bridge)bridge.select(selectedIP);});
  }
  item.bucket=bucket;if(!item.marker.getLatLng().equals(position))item.marker.setLatLng(position);
  if(!cluster){const styleKey=`${p.active}:${p.new}`;if(item.styleKey!==styleKey){item.marker.setStyle({color:p.active?'#527e66':'#877e71',fillColor:p.new?'#bf8b3e':p.active?'#47755d':'#a69b89',fillOpacity:1});item.styleKey=styleKey;}}
  const content=cluster?'<b>Группа адресов: '+bucket.length+'</b><p>Увеличьте масштаб, чтобы раскрыть группу.</p>'+bucket.map(popup).join('<hr>'):popup(p);
  if(content!==item.content){if(item.marker.getPopup())item.marker.getPopup().setContent(content);else item.marker.bindPopup(content);item.content=content;}
  if(!item.marker.getTooltip())item.marker.bindTooltip(cluster?'Адресов в группе: '+bucket.length:escapeHTML(p.ip));
  if(payload.origin&&bucket.some(p=>p.active)&&n++<80){
   keepLines.add(key);let target=[...position];if(target[1]-payload.origin[1]>180)target[1]-=360;else if(target[1]-payload.origin[1]<-180)target[1]+=360;
   if(!lineObjects.has(key))lineObjects.set(key,L.polyline([payload.origin,target],{color:'#6d8877',weight:1,opacity:.55,renderer:canvas,interactive:false}).addTo(lines));
   else {const old=lineObjects.get(key).getLatLngs();if(!old[0].equals(payload.origin)||!old[1].equals(target))lineObjects.get(key).setLatLngs([payload.origin,target]);}
  }
 }
 for(const [key,item]of objects)if(!keep.has(key)){layer.removeLayer(item.marker);objects.delete(key);}
 for(const [key,line]of lineObjects)if(!keepLines.has(key)){lines.removeLayer(line);lineObjects.delete(key);}
 document.getElementById('empty').style.display=points.length?'none':'block';
 document.getElementById('counter').textContent=`На карте: ${points.length} / ${payload.total_points??payload.points.length} IP · групп: ${buckets.size}`;
}
window.updateNetMap=data=>{
 payload=data;map.options.zoomAnimation=data.animations;
 if(data.palette&&JSON.stringify(data.palette)!==paletteKey){paletteKey=JSON.stringify(data.palette);const t=data.palette;document.documentElement.style.setProperty('--bg',t.bg);document.documentElement.style.setProperty('--ocean',t.ocean);document.documentElement.style.setProperty('--surface',t.surface);document.documentElement.style.setProperty('--text',t.text);document.documentElement.style.setProperty('--muted',t.muted);document.documentElement.style.setProperty('--line',t.line);world.setStyle({color:t.border,fillColor:t.land});}
 if(data.tiles&&!tiles){tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:12,opacity:.5,attribution:'© OpenStreetMap contributors'}).addTo(map);tiles.on('tileerror',()=>{document.getElementById('counter').textContent='Тайлы недоступны · локальная карта';});}
 else if(!data.tiles&&tiles){map.removeLayer(tiles);tiles=null;}
 draw();
};
window.focusIP=ip=>{const p=payload.points.find(p=>p.ip===ip);if(!p)return false;map.setView([p.latitude,p.longitude],6);selectedIP=ip;for(const item of objects.values())if(item.bucket.some(p=>p.ip===ip))item.marker.openPopup();return true;};
map.on('zoomend',draw);
