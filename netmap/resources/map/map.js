'use strict';
const map = L.map('map',{zoomControl:true,attributionControl:true,preferCanvas:true,minZoom:1,maxZoom:12,worldCopyJump:true}).setView([24,12],2);
map.attributionControl.setPrefix(false);
map.attributionControl.addAttribution('Natural Earth · общедоступные данные');
L.geoJSON(window.WORLD,{interactive:false,style:{color:'#38526c',weight:.6,fillColor:'#20354b',fillOpacity:.85}}).addTo(map);
let selectedIP=null, redrawing=false;
let bridge=null, payload={points:[],limit:500,animations:true,origin:null,tiles:false}, tiles=null;
const layer=L.layerGroup().addTo(map);
const canvas=L.canvas({padding:.3});
const escapeHTML = value => String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
new QWebChannel(qt.webChannelTransport,channel=>{bridge=channel.objects.bridge;});
function popup(point) {
    const connections=point.connections.map(c=>`${escapeHTML(c.process)} · PID ${escapeHTML(c.pid??'—')}<br>${escapeHTML(c.protocol)} : ${escapeHTML(c.port)} · ${escapeHTML(c.status)}`).join('<hr>');
    return `<b>${escapeHTML(point.ip)}</b>${point.new?' · новое наблюдение':''}<br>${escapeHTML(point.country||'Страна не определена')} · ${escapeHTML(point.city||'Город не определён')}<br><small>Приблизительная геолокация${point.accuracy_km?' · радиус '+escapeHTML(point.accuracy_km)+' км':''}</small><hr>${connections||'Ранее обнаруженный адрес'}<hr><small>Первое: ${escapeHTML(point.first)}<br>Последнее: ${escapeHTML(point.last)}</small>`;
}
function draw() {
    redrawing=true;
    layer.clearLayers();
    const points=payload.points.slice().sort((a,b)=>Number(b.active)-Number(a.active)).slice(0,payload.limit);
    // Spatial buckets merge coincident / nearby markers. Limit applies before object creation.
    const buckets=new Map();
    for (const point of points) {
        const px=map.project([point.latitude,point.longitude],map.getZoom());
        const key=`${Math.floor(px.x/38)}:${Math.floor(px.y/38)}`;
        if (!buckets.has(key)) buckets.set(key,[]);
        buckets.get(key).push(point);
    }
    let origin=payload.origin;
    if (origin) L.circleMarker(origin,{radius:7,color:'#f1d39b',weight:2,fillColor:'#aa8455',fillOpacity:1,renderer:canvas}).bindTooltip('Исходная точка, заданная вручную').addTo(layer);
    let lineCount=0;
    for (const bucket of buckets.values()) {
        const point=bucket[0], latlng=[point.latitude,point.longitude];
        if (bucket.length>1) {
            const icon=L.divIcon({className:'cluster',html:String(bucket.length),iconSize:[34,34],iconAnchor:[17,17]});
            const marker=L.marker(latlng,{icon}).addTo(layer);
            marker.bindTooltip(`Группа: ${bucket.length} адресов`);
            marker.on('click',()=>{
                if(map.getZoom()<12) { map.setView(latlng,map.getZoom()+2); return; }
                marker.bindPopup(bucket.map(p=>popup(p)).join('<hr>')).openPopup();
                if(bridge) bridge.select(point.ip);
            });
        } else {
            const color=point.active?(point.new?'#d0f9ff':'#67ddf5'):'#9786ce';
            if(point.active&&payload.animations) L.circleMarker(latlng,{radius:11,color,weight:0,fillOpacity:.10,renderer:canvas,interactive:false}).addTo(layer);
            const marker=L.circleMarker(latlng,{radius:point.active?5:4,color,weight:1.5,fillOpacity:.85,renderer:canvas}).addTo(layer);
            marker.bindTooltip(`${escapeHTML(point.ip)} · ${escapeHTML(point.city||point.country||'Координаты из базы')}`);
            marker.bindPopup(popup(point));
            if(selectedIP===point.ip) marker.openPopup();
            marker.on('click',()=>{selectedIP=point.ip;if(bridge) bridge.select(point.ip);});
        }
        if(origin&&bucket.some(p=>p.active)&&lineCount++<80) {
            // Split dateline crossings to avoid drawing a long line across the map.
            let dest=[...latlng];
            if(dest[1]-origin[1]>180) dest[1]-=360;
            else if(dest[1]-origin[1]<-180) dest[1]+=360;
            L.polyline([origin,dest],{color:'#59b7d5',weight:1,opacity:.32,renderer:canvas,interactive:false}).addTo(layer);
        }
    }
    document.getElementById('empty').style.display=points.length?'none':'block';
    document.getElementById('counter').textContent=`На карте: ${points.length} / ${payload.points.length} IP · групп: ${buckets.size}`;
    redrawing=false;
}
window.updateNetMap = data => {
    payload=data;
    map.options.zoomAnimation=data.animations;
    if(data.tiles&&!tiles) {
        tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:12,opacity:.45,attribution:'© OpenStreetMap contributors',crossOrigin:false}).addTo(map);
        tiles.on('tileerror',()=>{document.getElementById('counter').textContent='Тайлы недоступны · используется локальная карта';});
    } else if(!data.tiles&&tiles) { map.removeLayer(tiles); tiles=null; }
    draw();
};
map.on('zoomend',draw);

map.on('popupclose',()=>{if(!redrawing) selectedIP=null;});
