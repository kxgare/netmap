import csv
from pathlib import Path

def csv_value(value):
    text='' if value is None else str(value)
    return "'"+text if text.lstrip().startswith(('=','+','-','@')) else text

def write_csv(path,rows,columns):
    path=Path(path)
    # A sibling temporary file keeps an existing export intact if writing fails.
    import tempfile,os
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    count=0
    try:
        with os.fdopen(fd,'w',encoding='utf-8-sig',newline='') as file:
            writer=csv.writer(file); writer.writerow(columns)
            for row in rows:
                writer.writerow([csv_value(row.get(c)) for c in columns]); count+=1
        Path(tmp).replace(path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True); raise
    return count
