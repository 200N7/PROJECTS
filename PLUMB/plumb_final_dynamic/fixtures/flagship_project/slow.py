def find_duplicates(items):
    out=[]
    for i, x in enumerate(items):
        for y in items[i+1:]:
            if x != y and x not in out:
                out.append(x)
    return out
