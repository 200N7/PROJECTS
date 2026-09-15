from taskmgr.store import add_task, list_tasks, Task
from taskmgr.export import export_csv
from taskmgr.merge import merge_import

def test_add_and_list_tasks():
    tasks=add_task([], 'A','todo',2); assert list_tasks(tasks)[0].title=='A'

def test_filter_by_status():
    tasks=[Task(1,'A','todo'),Task(2,'B','done')]; assert sum(1 for t in tasks if t.status=='done')==1

def test_export_returns_csv_string():
    tasks=[Task(1,'A','todo'),Task(2,'B','done')]; assert 'id,title,status,priority' in export_csv(tasks)

def test_merge_import_no_overlap():
    a=[Task(1,'A','todo')]; b=[Task(2,'B','todo')]; assert len(merge_import(a,b))==2
