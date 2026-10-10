"""One factual IP summary shared by the map and connection explorer."""
import html
from netmap.ui.table import display_time

def ip_html(ip,connections=(),historical=()):
    esc=html.escape
    rows=[c for c in connections if c.remote_ip==ip]
    past=[r for r in historical if r['remote_ip']==ip]
    country=next((c.location.country for c in rows if c.location.country),next((r['country'] for r in past if r['country']),''))
    city=next((c.location.city for c in rows if c.location.city),next((r['city'] for r in past if r['city']),''))
    loc=next((c.location for c in rows if c.location.mapped),None)
    coords=(loc.latitude,loc.longitude) if loc else next(((r['latitude'],r['longitude']) for r in past if r['latitude'] is not None and r['longitude'] is not None),None)
    names=sorted({c.process for c in rows}|{r['process'] for r in past})
    protocols=sorted({c.protocol for c in rows}|{r['protocol'] for r in past})
    ports=sorted({c.remote_port for c in rows}|{r['remote_port'] for r in past})
    first=[c.first_seen or c.observed for c in rows]+[r['first_seen'] for r in past]
    last=[c.observed for c in rows]+[r['last_seen'] for r in past]
    text='<h2>'+esc(ip)+'</h2><p>'+esc(' · '.join(v for v in (country,city) if v) or 'География не определена')+'</p>'
    if coords: text+=f'<p>Приблизительные координаты: {coords[0]:.4f}, {coords[1]:.4f}</p>'
    text+='<p>Геолокация IP не доказывает физическое расположение сервера.</p>'
    text+='<h3>Связанные программы</h3><p>'+esc(', '.join(names) or 'Данные не обнаружены')+'</p>'
    if rows: text+=f'<p>{len(rows)} наблюдаемых сокетов</p>'
    else: text+='<p>Текущее подключение не наблюдается.</p>'
    if protocols: text+='<p>Протоколы: '+esc(', '.join(protocols))+'</p>'
    if ports: text+='<p>Удалённые порты: '+', '.join(map(str,ports))+'</p>'
    if first: text+='<p>Первое наблюдение: '+esc(display_time(min(first)))+'<br>Последнее: '+esc(display_time(max(last)))+'</p>'
    for action,title in [('copy','Скопировать IP'),('map','На карте'),('history','История'),('connections','Соединения')]:
        text+=f'<p><a href="{action}:{esc(ip,quote=True)}">{title}</a></p>'
    return text
