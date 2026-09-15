from dataclasses import dataclass
@dataclass
class Task:
    id: int
    title: str
    status: str = 'todo'
    priority: int = 1

def add_task(tasks, title, status='todo', priority=1):
    return tasks + [Task(len(tasks) + 1, title, status, priority)]

def list_tasks(tasks):
    return list(tasks)
