from __future__ import annotations
import json, shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .db import init_db, save_analysis, get_analysis, list_history, delete_history, clear_history
from .session import get_session_id
from .ingest import ingest_zip, IngestionError
from .analyzer import analyze
from .report import generate_pdf

ROOT=Path(__file__).resolve().parents[2]
templates=Jinja2Templates(directory=str(ROOT/'plumb/templates'))
app=FastAPI(title='PLUMB',version='1.0.0')
app.mount('/static', StaticFiles(directory=str(ROOT/'plumb/static')), name='static')

@app.get('/healthz')
def healthz():
    return {'status':'ok','service':'PLUMB'}

@app.on_event('startup')
def startup(): init_db()

@app.get('/',response_class=HTMLResponse)
def home(request: Request):
    response=templates.TemplateResponse('home.html',{'request':request}); get_session_id(request,response); return response

@app.post('/api/analyses')
async def create_analysis(request: Request, project_name: str=Form(...), task_spec_text: str=Form(...), ai_completion_message: str=Form(''), project_archive: UploadFile=File(...)):
    response=JSONResponse({})
    sid=get_session_id(request,response)
    data=await project_archive.read()
    try: root, phash=ingest_zip(data)
    except IngestionError as e: raise HTTPException(400,str(e))
    try:
        payload=analyze(root,project_name,task_spec_text,ai_completion_message)
        payload['project_hash']=phash
        save_analysis(sid,payload)
        return JSONResponse({'analysis_id':payload['analysis_id'],'verdict':payload['verdict']},headers={'Set-Cookie':response.headers.get('set-cookie','')})
    finally:
        shutil.rmtree(root,ignore_errors=True)

@app.get('/api/analyses/{analysis_id}')
def api_analysis(request: Request,analysis_id: str):
    a=get_analysis(analysis_id,get_session_id(request));
    if not a: raise HTTPException(404,'Analysis not found')
    return a

@app.get('/api/analyses/{analysis_id}/analytics')
def analytics(request: Request,analysis_id: str):
    a=get_analysis(analysis_id,get_session_id(request));
    if not a: raise HTTPException(404,'Analysis not found')
    counts={s:sum(1 for r in a['requirements'] if r['status']==s) for s in ['VERIFIED','PARTIALLY_VERIFIED','FAILED','INCONCLUSIVE','UNSUPPORTED']}
    heat=[]
    for r in a['requirements']:
        for ac in r['criteria']:
            heat.append({'requirement':r.get('requirement_id') or r.get('id'),'criterion':ac['id'],'status':ac['status'],'stage':ac.get('stage'),'text':ac['text']})
    raw_arch=a['metrics'].get('architecture_edges',[])
    source_files={f['path'] for f in a['files']}
    py_modules={Path(x).with_suffix('').as_posix().replace('/','.') for x in source_files if x.endswith('.py')}
    stems={Path(x).stem for x in source_files if x.endswith('.py')}
    arch=[]
    for edge in raw_arch:
        src=edge.get('from',''); dst=edge.get('to','').lstrip('.')
        dst_norm=dst.replace('/','.')
        if dst_norm in py_modules or dst in py_modules or Path(dst).stem in stems:
            target=next((x for x in source_files if Path(x).stem==Path(dst).stem), dst)
            arch.append({'from':src,'to':target,'kind':edge.get('kind','import')})
    # Build a semantic architecture model. Architecture is not just imports: it shows
    # project -> modules -> code symbols/capabilities, plus tests, runtime routes and risks.
    code_files=[f['path'] for f in a['files'] if f.get('language') in {'Python','JavaScript','TypeScript'}]
    test_files=set(a['metrics'].get('test_files',[]) or [])
    nodes_by_id={}
    def add_node(node_id, label, kind='module', status=None, detail=None, parent=None):
        if not node_id or not label: return
        cur=nodes_by_id.setdefault(node_id, {'id':node_id,'label':label,'kind':kind})
        cur['kind']=kind
        if status: cur['status']=status
        if detail: cur['detail']=detail
        if parent: cur['parent']=parent
    root_id='project:root'
    add_node(root_id, a.get('project_name') or 'Project', 'project')
    for f in code_files:
        is_test=f in test_files or Path(f).name.startswith('test_') or '/test' in f
        fid='file:'+f
        add_node(fid, f, 'test' if is_test else 'module', parent=root_id)
        arch.append({'from':root_id,'to':fid,'kind':'contains'})
    # Source-level functions/classes make tiny projects informative instead of two-file diagrams.
    for sym in a.get('symbols',[]) or []:
        fp=sym.get('file'); name=sym.get('name')
        if not fp or not name or fp not in code_files: continue
        if fp in test_files or Path(fp).name.startswith('test_') or '/test' in fp: continue
        sid=f"symbol:{fp}:{name}:{sym.get('line','')}"
        label=name + ('()' if sym.get('kind')=='function' else '')
        add_node(sid,label,'function' if sym.get('kind')=='function' else 'component',detail=f"{fp}:{sym.get('line','')}",parent='file:'+fp)
        arch.append({'from':'file:'+fp,'to':sid,'kind':'contains'})
    # Normalize discovered import relationships onto file node ids.
    normalized=[]
    for e in arch[:]:
        if str(e.get('from','')).startswith(('project:','file:','symbol:')): continue
        src=e.get('from'); dst=e.get('to')
        if src in code_files and dst in code_files:
            normalized.append({'from':'file:'+src,'to':'file:'+dst,'kind':e.get('kind','import')})
    arch=[e for e in arch if str(e.get('from','')).startswith(('project:','file:','symbol:'))] + normalized
    runtime=a.get('runtime') or {}
    entry=runtime.get('entry')
    entry_id='file:'+entry if entry else None
    for check in runtime.get('checks',[]) or []:
        endpoint=check.get('endpoint') or check.get('path') or check.get('name')
        if endpoint:
            label=str(endpoint)
            if not label.upper().startswith(('GET ','POST ','PUT ','PATCH ','DELETE ')):
                label=f"{check.get('method','GET')} {label}"
            eid='endpoint:'+label
            add_node(eid,label,'endpoint',status=check.get('status'),detail=check.get('observed'),parent=entry_id)
            if entry_id: arch.append({'from':entry_id,'to':eid,'kind':'serves'})
    # Risks are annotations attached to the affected component, never replacements for it.
    for i,finding in enumerate(a.get('findings',[]) or []):
        fp=finding.get('file') or finding.get('path')
        if not fp: continue
        rule=finding.get('rule') or finding.get('title') or 'security finding'
        line=finding.get('line')
        rid=f"risk:{i}:{fp}:{rule}"
        add_node(rid,rule,'risk',status='FAILED',detail=(f"{fp}:{line}" if line else fp),parent='file:'+fp)
        if 'file:'+fp in nodes_by_id: arch.append({'from':'file:'+fp,'to':rid,'kind':'risk'})
    # Test relationships are explicit. Prefer discovered imports; otherwise connect tests to
    # the runtime entry or the sole production module as a bounded, clearly-labelled relation.
    production=[f for f in code_files if f not in test_files and not Path(f).name.startswith('test_') and '/test' not in f]
    for tf in test_files:
        tid='file:'+tf
        targets=[]
        for e in raw_arch:
            if e.get('from')==tf:
                dst=e.get('to','').lstrip('.'); match=next((x for x in production if Path(x).stem==Path(dst).stem),None)
                if match: targets.append(match)
        if not targets and entry in production: targets=[entry]
        if not targets and len(production)==1: targets=production
        for target in dict.fromkeys(targets): arch.append({'from':tid,'to':'file:'+target,'kind':'tests'})
    nodes=list(nodes_by_id.values())
    cats=['boundary','duplicate','ordering','type','security','runtime','performance','build']
    values={(r.get('requirement_id') or r.get('id')):{c:0 for c in cats} for r in a['requirements']}
    for r in a['requirements']:
        for ac in r['criteria']:
            if ac['status']!='FAILED': continue
            txt=ac['text'].lower()
            flags=[]
            if 'duplicate' in txt or 'distinct' in txt: flags.append('duplicate')
            if 'order' in txt or 'insertion' in txt: flags.append('ordering')
            if any(x in txt for x in ['status','filtered','endpoint','http','/health','/items']): flags.append('runtime')
            if any(x in txt for x in ['performance','larger','workload','growth']): flags.append('performance')
            if any(x in txt for x in ['credential','unsafe','command','security','secret']): flags.append('security')
            if 'boundary' in txt: flags.append('boundary')
            if 'type' in txt or 'invalid' in txt: flags.append('type')
            if not flags: flags=['build']
            for f in set(flags): values[(r.get('requirement_id') or r.get('id'))][f]+=1
    treemap=[]
    for f in a['files']:
        if f.get('language') in {'Python','JavaScript','TypeScript'}:
            treemap.append({'label':f['path'],'value':f.get('size',0)})
    return {'requirement_counts':counts,'closure':a['metrics']['closure'],'depth':a['metrics']['depth'],'heatmap':[{**x,'has_evidence':any(e.get('acceptance_criterion_id')==x['criterion'] for e in a['evidences'])} for x in heat],'architecture':arch,'architecture_nodes':nodes,'mutations':a['mutations'],'performance':a['performance'],'security':a['security'],'failure_heatmap':{'categories':cats,'values':values},'treemap':treemap,'evidence_coverage':len([e for e in a['evidences'] if e.get('status')]),'requirements':a['requirements']}

@app.get('/api/analyses/{analysis_id}/evidence')
def evidence(request: Request,analysis_id: str,requirement: str|None=None,criterion: str|None=None):
    a=get_analysis(analysis_id,get_session_id(request));
    if not a: raise HTTPException(404,'Analysis not found')
    ev=a['evidences']
    if requirement: ev=[e for e in ev if e.get('requirement_id')==requirement]
    if criterion: ev=[e for e in ev if e.get('acceptance_criterion_id')==criterion]
    return {'evidence':ev}

@app.get('/api/history')
def history(request: Request): return list_history(get_session_id(request))
@app.delete('/api/history/{analysis_id}')
def del_hist(request: Request,analysis_id: str):
    n=delete_history(get_session_id(request),analysis_id)
    if not n: raise HTTPException(404,'History entry not found')
    return {'deleted':1}
@app.delete('/api/history')
def clear_hist(request: Request): return {'deleted':clear_history(get_session_id(request))}

@app.get('/api/analyses/{analysis_id}/report')
def report(request: Request,analysis_id: str):
    a=get_analysis(analysis_id,get_session_id(request));
    if not a: raise HTTPException(404,'Analysis not found')
    return JSONResponse({'analysis_id':analysis_id,'report':{'verdict':a['verdict'],'score':a['score'],'metrics':a['metrics'],'requirements':a['requirements'],'evidence':a['evidences']}})

@app.get('/api/analyses/{analysis_id}/export/pdf')
def pdf(request: Request,analysis_id: str):
    a=get_analysis(analysis_id,get_session_id(request));
    if not a: raise HTTPException(404,'Analysis not found')
    p=generate_pdf(a); return FileResponse(p,media_type='application/pdf',filename=f'PLUMB-{analysis_id}.pdf')

@app.get('/analysis/{analysis_id}',response_class=HTMLResponse)
def analysis_page(request: Request,analysis_id: str):
    a=get_analysis(analysis_id,get_session_id(request));
    if not a: raise HTTPException(404,'Analysis not found')
    return templates.TemplateResponse('analysis.html',{'request':request,'a':a})

@app.get('/analysis/{analysis_id}/analytics',response_class=HTMLResponse)
def analytics_page(request: Request,analysis_id: str):
    a=get_analysis(analysis_id,get_session_id(request));
    if not a: raise HTTPException(404,'Analysis not found')
    return templates.TemplateResponse('analytics.html',{'request':request,'a':a})

@app.get('/evidence/{analysis_id}',response_class=HTMLResponse)
def evidence_page(request: Request,analysis_id: str,requirement: str|None=None):
    a=get_analysis(analysis_id,get_session_id(request));
    if not a: raise HTTPException(404,'Analysis not found')
    ev=[e for e in a['evidences'] if not requirement or e.get('requirement_id')==requirement]
    return templates.TemplateResponse('evidence.html',{'request':request,'a':a,'evidence':ev,'requirement':requirement})

@app.get('/history',response_class=HTMLResponse)
def history_page(request: Request): return templates.TemplateResponse('history.html',{'request':request,'items':list_history(get_session_id(request))})
