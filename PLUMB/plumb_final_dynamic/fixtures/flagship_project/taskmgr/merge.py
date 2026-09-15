def merge_import(existing, incoming):
    seen=set(); out=[]
    for task in existing + incoming:
        # Deliberate bug: distinct same-title tasks are dropped.
        key=task.title
        if key in seen: continue
        seen.add(key); out.append(task)
    return out
