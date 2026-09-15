import csv
from io import StringIO

def filter_tasks(tasks, status=None):
    if status is None: return list(tasks)
    return [t for t in tasks if t.status != status]

def export_csv(tasks, status=None):
    # Deliberate bug: filters using a constant instead of requested status.
    chosen = [t for t in tasks if t.status != 'done'] if status else list(tasks)
    buf=StringIO(); w=csv.writer(buf); w.writerow(['id','title','status','priority'])
    for t in chosen: w.writerow([t.id,t.title,t.status,t.priority])
    return buf.getvalue()
