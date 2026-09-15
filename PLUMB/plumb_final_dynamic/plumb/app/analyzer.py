from __future__ import annotations
import ast, hashlib, json, os, re, subprocess, sys, tempfile, time, statistics, uuid, csv, io, math, shutil
from pathlib import Path
from dataclasses import asdict
from .models import Evidence, Requirement, DEPTH_ORDER

LANG_EXT={'.py':'Python','.js':'JavaScript','.jsx':'JavaScript','.ts':'TypeScript','.tsx':'TypeScript','.json':'JSON','.md':'Markdown','.html':'HTML','.css':'CSS'}
SECRET_RX=re.compile(r'(?i)(api[_-]?key|secret|token|password)\s*=\s*["\'][^"\']{10,}["\']')


def text_read(p: Path):
    try: return p.read_text(encoding='utf-8', errors='replace')
    except Exception: return ''

def discover(root: Path):
    files=[]; langs=set(); frameworks=set(); imports=[]; symbols=[]; tests=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(root).as_posix(); ext=p.suffix.lower()
        if any(part.startswith('.') and part not in {'.env'} for part in p.relative_to(root).parts): continue
        size=p.stat().st_size
        item={'path':rel,'size':size,'ext':ext,'language':LANG_EXT.get(ext,'Other'),'lines':0,'symbols':[]}
        if ext in LANG_EXT:
            langs.add(LANG_EXT[ext]); txt=text_read(p); item['lines']=txt.count('\n')+1 if txt else 0
            if p.name.startswith('test_') or p.name.endswith('_test.py') or '/tests/' in '/'+rel: tests.append(rel)
            if ext=='.py':
                try:
                    tree=ast.parse(txt, filename=rel)
                    for n in ast.walk(tree):
                        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                            kind='class' if isinstance(n,ast.ClassDef) else 'function'
                            symbols.append({'file':rel,'name':n.name,'kind':kind,'line':n.lineno,'end_line':getattr(n,'end_lineno',n.lineno)})
                            item['symbols'].append(n.name)
                        if isinstance(n,ast.Import):
                            for a in n.names: imports.append({'from':rel,'to':a.name,'kind':'import'})
                        if isinstance(n,ast.ImportFrom): imports.append({'from':rel,'to':('.'*n.level)+(n.module or ''),'kind':'import'})
                except SyntaxError as e:
                    item['syntax_error']=str(e)
            elif ext in {'.js','.jsx','.ts','.tsx'}:
                for m in re.finditer(r'\b(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)|\bclass\s+([A-Za-z_$][\w$]*)',txt):
                    name=m.group(1) or m.group(2); item['symbols'].append(name); symbols.append({'file':rel,'name':name,'kind':'function_or_class','line':txt.count('\n',0,m.start())+1})
                for m in re.finditer(r'\bfrom\s+[\"\']([^\"\']+)[\"\']|\bimport\s+[^;\n]+\s+from\s+[\"\']([^\"\']+)[\"\']',txt):
                    imports.append({'from':rel,'to':m.group(1) or m.group(2),'kind':'import'})
            if 'fastapi' in txt.lower(): frameworks.add('FastAPI')
            if 'flask' in txt.lower(): frameworks.add('Flask')
            if 'react' in txt.lower() and ext in {'.js','.jsx','.ts','.tsx'}: frameworks.add('React')
            if 'next' in txt.lower() and ext in {'.js','.jsx','.ts','.tsx'}: frameworks.add('Next.js')
        files.append(item)
    return {'files':files,'languages':sorted(langs),'frameworks':sorted(frameworks),'imports':imports,'symbols':symbols,'tests':tests}

def parse_requirements(spec: str):
    """Extract usable requirements from numbered lists, bullets, or plain prose.

    The old parser silently returned zero requirements unless every line started
    with ``1.``/``2.``. That made a normal pasted task look like it had been
    inspected when there was actually nothing to verify.
    """
    raw=(spec or '').strip()
    if not raw:
        return []
    candidates=[]
    for line in raw.splitlines():
        line=line.strip()
        if not line:
            continue
        if re.match(r'^HTTP_CHECK\b', line, re.I):
            continue
        # headings are useful context, but are not requirements by themselves
        cleaned=re.sub(r'^\s*(?:\d+[.)]|[-*+•]|REQ[-_ ]?\d+[:.)-]?)\s*', '', line, flags=re.I).strip()
        if cleaned and len(cleaned) >= 4:
            candidates.append(cleaned)
    # A paragraph-only specification is common. Split conservatively into
    # sentence-sized requirements instead of producing an empty inspection.
    if len(candidates) <= 1 and raw:
        prose=re.sub(r'\s+', ' ', raw)
        sentences=[x.strip(' -\t') for x in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', prose) if x.strip()]
        if len(sentences) > 1:
            candidates=sentences
    # De-duplicate while preserving order and keep the run bounded.
    seen=set(); unique=[]
    for c in candidates:
        key=c.casefold()
        if key not in seen:
            seen.add(key); unique.append(c)
    reqs=[]
    for idx,desc in enumerate(unique[:50],1):
        rid=f"REQ-{idx:03d}"
        parts=[x.strip() for x in re.split(r';|(?<=[.!?])\s+(?=[A-Z0-9])', desc) if x.strip()]
        title=(parts[0] if parts else desc).strip()
        if len(title)>90: title=title[:87].rstrip()+'...'
        criteria=[]
        for i,f in enumerate(parts[:8],1):
            criteria.append({'id':f'{rid}-AC-{i:02d}','text':f,'status':'INCONCLUSIVE','stage':'DETECTED','weight':0.2,'mapped_item_ids':[]})
        if not criteria:
            criteria=[{'id':f'{rid}-AC-01','text':desc,'status':'INCONCLUSIVE','stage':'DETECTED','weight':0.2,'mapped_item_ids':[]}]
        reqs.append((rid,title,desc,criteria))
    return reqs

def _tokens(s): return {t.lower() for t in re.findall(r'[A-Za-z_][A-Za-z0-9_]{2,}',s) if t.lower() not in {'the','and','for','with','must','should','that','into','from','only','this','when','then','return','have','has','can'}}

def map_requirements(req_tuples, discovery, claim, analysis_id):
    symbols=discovery['symbols']; files=discovery['files']
    output=[]
    for rid,title,desc,criteria in req_tuples:
        req_tokens=_tokens(desc+' '+title); items=[]
        for s in symbols:
            score=len(req_tokens & _tokens(s['name']))
            file_score=len(req_tokens & _tokens(s['file']))
            total=score*4+file_score
            if total>0:
                items.append({'id':str(uuid.uuid4()),'file_path':s['file'],'symbol':s['name'],'line':s.get('line'),'state':'PRESENT','score':total,'supports_ac_codes':[]})
        # semantic-ish heuristics: files containing distinctive keywords
        for f in files:
            if f['ext'] not in {'.py','.js','.jsx','.ts','.tsx'}: continue
            ft=_tokens(f['path']); sc=len(req_tokens & ft)
            if sc>=1 and not any(x['file_path']==f['path'] for x in items):
                items.append({'id':str(uuid.uuid4()),'file_path':f['path'],'symbol':f['path'],'line':1,'state':'PRESENT','score':sc,'supports_ac_codes':[]})
        items=sorted(items,key=lambda x:-x['score'])[:5]
        # map each criterion to best matching item(s)
        for ac in criteria:
            candidates=[]
            ac_tokens=_tokens(ac['text'])
            for it in items:
                s=len(ac_tokens & _tokens(it['symbol']+' '+it['file_path']))
                candidates.append((s,it))
            candidates.sort(key=lambda z:-z[0])
            if candidates and candidates[0][0]>0:
                ac['mapped_item_ids']=[candidates[0][1]['id']]
            else: ac['mapped_item_ids']=[]
        output.append({'id':rid,'title':title,'description':desc,'criteria':criteria,'implementation_items':items})
    return output

def static_findings(root: Path):
    findings=[]
    for p in root.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in {'.py','.js','.ts','.jsx','.tsx'}: continue
        txt=text_read(p); rel=p.relative_to(root).as_posix()
        for i,line in enumerate(txt.splitlines(),1):
            if SECRET_RX.search(line): findings.append({'id':str(uuid.uuid4()),'severity':'HIGH','rule':'hardcoded-secret','file':rel,'line':i,'evidence':line.strip()})
            for rule,pat,sev in [('shell-true',r'subprocess\.(run|Popen|call).*shell\s*=\s*True','HIGH'),('eval-exec',r'\b(eval|exec)\s*\(','HIGH'),('pickle-load',r'pickle\.loads?\s*\(','HIGH'),('bare-except',r'^\s*except\s*:\s*$','MEDIUM')]:
                if re.search(pat,line): findings.append({'id':str(uuid.uuid4()),'severity':sev,'rule':rule,'file':rel,'line':i,'evidence':line.strip()})
    return findings

def complexity(root: Path, discovery):
    vals=[]
    for s in discovery['symbols']:
        if s['kind']!='function': continue
        p=root/s['file']; lines=text_read(p).splitlines(); start=max(1,s['line']); end=min(len(lines),s.get('end_line',start))
        body='\n'.join(lines[start-1:end]); c=1+sum(body.count(k) for k in ['if ','elif ','for ','while ',' and ',' or ',' except ',' case '])
        vals.append(c)
    if not vals: return {'count':0,'mean':0,'max':0,'distribution':[]}
    return {'count':len(vals),'mean':round(statistics.mean(vals),2),'max':max(vals),'distribution':vals}

def run_cmd(cmd, cwd, timeout=20):
    t=time.perf_counter()
    try:
        r=subprocess.run(cmd,cwd=str(cwd),capture_output=True,text=True,timeout=timeout,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1'})
        return {'returncode':r.returncode,'stdout':r.stdout[-12000:],'stderr':r.stderr[-12000:],'duration_ms':round((time.perf_counter()-t)*1000,2),'timed_out':False}
    except subprocess.TimeoutExpired as e:
        return {'returncode':None,'stdout':getattr(e,'stdout','') or '','stderr':getattr(e,'stderr','') or '','duration_ms':round((time.perf_counter()-t)*1000,2),'timed_out':True}

def execute_tests(root: Path):
    tests=list(root.rglob('test_*.py'))+list(root.rglob('*_test.py'))
    if not tests: return {'status':'UNSUPPORTED','passed':0,'failed':0,'skipped':0,'duration_ms':0,'output':'No Python test files found.'}
    res=run_cmd([sys.executable,'-m','pytest','-q','--disable-warnings'],root,25)
    out=(res['stdout']+'\n'+res['stderr']).strip()
    m=re.search(r'(\d+) passed',out); passed=int(m.group(1)) if m else 0
    m=re.search(r'(\d+) failed',out); failed=int(m.group(1)) if m else 0
    m=re.search(r'(\d+) skipped',out); skipped=int(m.group(1)) if m else 0
    status='PASSED' if res['returncode']==0 else 'FAILED'
    return {'status':status,'passed':passed,'failed':failed,'skipped':skipped,'duration_ms':res['duration_ms'],'output':out}



def _norm_words(text: str):
    """Small normalization layer for semantic planning, not project-specific rules."""
    words=[]
    for w in re.findall(r'[A-Za-z][A-Za-z0-9_-]*', (text or '').lower()):
        w=w.replace('_','-')
        for part in w.split('-'):
            if len(part)>1:
                if part.endswith('ies') and len(part)>4: part=part[:-3]+'y'
                elif part.endswith('s') and len(part)>3 and not part.endswith(('ss','us','is')): part=part[:-1]
                words.append(part)
    return words

def _literal_project_data(src: str):
    """Extract literal top-level data that can serve as an independent local oracle."""
    out={}
    try:
        tree=ast.parse(src)
    except Exception:
        return out
    for node in tree.body:
        if not isinstance(node,(ast.Assign,ast.AnnAssign)): continue
        targets=node.targets if isinstance(node,ast.Assign) else [node.target]
        try: value=ast.literal_eval(node.value)
        except Exception: continue
        for target in targets:
            if isinstance(target,ast.Name): out[target.id]=value
    return out

def _semantic_similarity(a: str, b: str):
    """Domain-neutral lexical similarity used only to align discovered project entities.

    It never decides a verdict. Verdicts come from executed evidence/oracles.
    """
    aw=_norm_words(a); bw=_norm_words(b)
    if not aw or not bw: return 0.0
    aset=set(aw); bset=set(bw)
    inter=aset & bset
    union=aset | bset
    # Repeated/path-local concepts get a little more weight without any domain allowlist.
    coverage=len(inter)/max(1,len(aset))
    jaccard=len(inter)/max(1,len(union))
    return 0.20*coverage + 0.80*jaccard

def _route_score(route: str, requirement_text: str):
    """Align a discovered route to a proposition without endpoint-specific rules."""
    rt=(route or '').lower(); txt=(requirement_text or '').lower()
    if rt and re.search(re.escape(rt)+r'(?=$|[\s\"\'.,;:)])',txt): return 1000.0
    # Compare path segments to the full proposition. Structural specificity naturally
    # favors /x/closed/count over /x/count when both "closed" and "count" are present.
    return round(_semantic_similarity(rt.replace('/',' '), txt)*100.0, 6)

def _infer_aggregate(text: str):
    """Map language onto mathematical primitives, not business domains."""
    words=set(_norm_words(text))
    if words & {'average','avg','mean'}: return 'mean'
    if words & {'count','number','quantity'}: return 'count'
    if words & {'sum','total','revenue','amount','weight','value'}: return 'sum'
    return None

def _project_literal_data(root: Path):
    out={}
    for p in root.rglob('*.py'):
        if any(x in p.parts for x in ('.venv','venv','__pycache__')): continue
        for k,v in _literal_project_data(text_read(p)).items():
            out[f'{p.relative_to(root).as_posix()}::{k}']=v
    return out

def _derive_oracle(requirement_text: str, route: str, literals: dict, output_keys=None):
    """Synthesize an independent deterministic oracle from submitted literal data.

    The planner is domain-neutral. It discovers a dataset, categorical filters and a
    mathematical aggregate from the proposition. Ambiguity returns None rather than a guess.
    """
    txt=(requirement_text or '').lower(); req_words=set(_norm_words(txt)); route_words=set(_norm_words(route)); output_keys=list(output_keys or [])
    # Explicit JSON-like assertions are independent propositions. Bind a quoted value
    # to the nearest field name before it instead of collapsing multiple assertions.
    pairs=[]
    for m in re.finditer(r'([A-Za-z_][A-Za-z0-9_-]*)\s+(?:as|is|=|equals?)?\s*[\"\']([^\"\']+)[\"\']', requirement_text or '', re.I):
        key=m.group(1).lower().replace('-','_'); val=m.group(2)
        if key not in {'with','and','return','returns','identify','service','as','is'}: pairs.append((key,val))
    # Common grammar: `status "ok"` and `service as "ledger"`.
    for key in ('status','service'):
        m=re.search(r'\b'+key+r'\b(?:\s+(?:as|is|=|equals?))?\s*[\"\']([^\"\']+)[\"\']', requirement_text or '', re.I)
        if m and (key,m.group(1)) not in pairs: pairs.append((key,m.group(1)))
    if pairs:
        return {'kind':'json_pairs','pairs':pairs,'description':' and '.join(f'{k}={v}' for k,v in pairs)}
    # Composite formulas require an expression tree. Never misrepresent them as a
    # simple sum/mean merely because those words also occur. Until a safe independent
    # expression is synthesized, correctness remains INCONCLUSIVE.
    composite=bool(re.search(r'\b(minus|subtract(?:ed)?|multipl(?:y|ied)|divid(?:e|ed)|ratio|percent(?:age)?)\b',txt))
    if composite: return None
    op=_infer_aggregate(txt)
    if not op: return None

    datasets=[]
    for name,val in literals.items():
        if isinstance(val,list) and val and all(isinstance(x,dict) for x in val):
            score=_semantic_similarity(name, txt+' '+route)
            datasets.append((score,name,val))
        elif op=='count' and isinstance(val,(list,tuple,set,dict)):
            score=_semantic_similarity(name, txt+' '+route)
            datasets.append((score,name,val))
    if not datasets: return None
    datasets.sort(key=lambda x:(-x[0],x[1]))
    # If multiple datasets are equally unrelated, independent truth is ambiguous.
    if len(datasets)>1 and datasets[0][0]==datasets[1][0]==0: return None
    data=datasets[0][2]
    if not isinstance(data,list) or not data or not all(isinstance(x,dict) for x in data):
        if op=='count': return {'kind':'number','value':len(data),'description':f'count={len(data)}'}
        return None

    selected=list(data); filters=[]
    # Values literally named in the proposition become filters. This supports arbitrary
    # domains (region/status/type/category/etc.) without field/value allowlists.
    for field in sorted({k for row in data for k in row}):
        values={str(row.get(field)).lower() for row in data if isinstance(row.get(field),str)}
        mentioned=[v for v in values if re.search(r'\b'+re.escape(v)+r'\b',txt)]
        if len(mentioned)==1:
            val=mentioned[0]
            selected=[r for r in selected if str(r.get(field,'')).lower()==val]
            filters.append((field,val))
        # Boolean predicates are inferred structurally from the field name itself.
        # E.g. a discovered field `resolved: bool` and proposition containing
        # `resolved` grounds to True; explicit negation grounds to False.
        bool_vals=[row.get(field) for row in data if field in row]
        if bool_vals and all(isinstance(v,bool) for v in bool_vals) and field.lower() in req_words:
            neg=bool(re.search(r'\b(?:not|un|non)[ -]?'+re.escape(field.lower())+r'\b',txt))
            want=not neg
            selected=[r for r in selected if r.get(field) is want]
            filters.append((field,want))
    # Numeric threshold predicates are grounded from language (`risk score at least 6`,
    # `amount > 10`, `score no more than 5`) against discovered numeric fields.
    for field in sorted({k for row in data for k in row}):
        if not all(isinstance(row.get(field),(int,float)) and not isinstance(row.get(field),bool) for row in data if field in row): continue
        if field.lower() not in req_words and _semantic_similarity(field, txt) < .08: continue
        fm=re.search(r'(?:'+re.escape(field.lower())+r')(?:\s+score)?\s+(?:is\s+)?(at least|minimum|>=|greater than or equal to|more than|>|at most|maximum|<=|less than or equal to|less than|<)\s*(-?\d+(?:\.\d+)?)',txt)
        if fm:
            opx,n=fm.group(1),float(fm.group(2))
            pred=(lambda x:x>=n) if opx in {'at least','minimum','>=','greater than or equal to'} else ((lambda x:x>n) if opx in {'more than','>'} else ((lambda x:x<=n) if opx in {'at most','maximum','<=','less than or equal to'} else (lambda x:x<n)))
            selected=[r for r in selected if isinstance(r.get(field),(int,float)) and pred(float(r[field]))]
            filters.append((field,opx,n))
    if op=='count':
        val=len(selected)
        return {'kind':'number','value':val,'description':f'count={val}','filters':filters,'dataset':datasets[0][1]}
    if not selected: return None

    numeric=[]
    for field in sorted({k for row in selected for k in row}):
        vals=[r.get(field) for r in selected]
        if vals and all(isinstance(v,(int,float)) and not isinstance(v,bool) for v in vals):
            # IDs/ordinal keys are structurally identifiers when unique across nearly all rows.
            unique_ratio=len(set(vals))/max(1,len(vals))
            # Ground the projected field using both the proposition and the actual
            # response schema. Aggregation wrappers such as average_minutes/total_minutes
            # are stripped before matching, so new domains do not need synonym rules.
            schema_terms=[]
            for key in output_keys:
                parts=[x for x in _norm_words(str(key)) if x not in {'average','avg','mean','sum','total','count','number','quantity'}]
                schema_terms.extend(parts)
            grounding_text=txt+' '+route+' '+' '.join(schema_terms)
            name_score=_semantic_similarity(field, grounding_text)
            if field.lower() in schema_terms: name_score += 1.0
            identifier_penalty=1.0 if field.lower() in {'id','index','rank'} and unique_ratio>.8 else 0.0
            numeric.append((name_score-identifier_penalty,field,vals))
    if not numeric: return None
    numeric.sort(key=lambda x:(-x[0],x[1]))
    if numeric[0][0] <= 0: return None
    if len(numeric)>1 and abs(numeric[0][0]-numeric[1][0]) < 1e-9: return None
    _,field,vals=numeric[0]
    value=(sum(float(v) for v in vals)/len(vals)) if op=='mean' else sum(float(v) for v in vals)
    value=round(value,6)
    label='average' if op=='mean' else 'total'
    return {'kind':'number','value':value,'description':f'{label}={value:g}','field':field,'filters':filters,'dataset':datasets[0][1]}

def _json_has_number(body: str, expected):
    try: obj=json.loads(body)
    except Exception: return False
    nums=[]
    def walk(v):
        if isinstance(v,bool): return
        if isinstance(v,(int,float)): nums.append(float(v))
        elif isinstance(v,dict):
            for x in v.values(): walk(x)
        elif isinstance(v,list):
            for x in v: walk(x)
    walk(obj)
    return any(math.isclose(x,float(expected),rel_tol=1e-9,abs_tol=1e-6) for x in nums)

def runtime_http_verify(root: Path, spec: str, timeout=6):
    checks=[]
    for line in spec.splitlines():
        m=re.match(r'^\s*HTTP_CHECK\s+(GET|POST|PUT|DELETE|PATCH)\s+(\S+)\s+(\d{3})(?:\s+(.+))?\s*$', line.strip())
        if m:
            candidate={'method':m.group(1),'path':m.group(2),'expected_code':int(m.group(3)),'contains':m.group(4) or ''}
            if candidate not in checks: checks.append(candidate)
    # Detect a small local Python HTTP service. Support either a PORT constant or a
    # literal port passed to HTTPServer((host, port), ...). This keeps discovery
    # deterministic while avoiding filename/fixture-specific assumptions.
    candidates=[]
    for pth in root.rglob('*.py'):
        txt=text_read(pth)
        recognized=('HTTPServer' in txt or 'BaseHTTPRequestHandler' in txt or 'FastAPI' in txt or 'Flask' in txt)
        port_m=(re.search(r'PORT\s*=\s*(\d+)',txt) or
                re.search(r'HTTPServer\s*\(\s*\(\s*[\"\'][^\"\']*[\"\']\s*,\s*(\d+)\s*\)',txt))
        if recognized and port_m:
            candidates.append((pth,int(port_m.group(1))))
    if not candidates:
        return {'status':'UNSUPPORTED','reason':'No supported local HTTP server entry point with a deterministic port was detected.','checks':[]}
    entry,port=candidates[0]
    src=text_read(entry)

    # Build a project-specific verification plan from discovered routes and the
    # submitted requirements. The planner uses generic semantic scoring and deterministic
    # local oracles; it has no endpoint-name allowlist or fixture-specific verdicts.
    if not checks:
        literals=_project_literal_data(root)
        routes=[]
        for m in re.finditer(r'(?:self\.path\s*==|route\s*\(|@\w+\.(?:get|post|put|delete|patch)\s*\()\s*["\']([^"\']+)["\']',src,re.I):
            route=m.group(1)
            if route.startswith('/') and route not in routes: routes.append(route)
        # Also discover route literals used through parsed-path dispatch (urlparse,
        # startswith, split routing). Literal discovery is framework-neutral; semantic
        # alignment against the submitted specification decides whether a route is probed.
        for m in re.finditer(r'["\'](/[^"\'\s?#]*)["\']', src):
            route=m.group(1)
            if route.startswith('/') and route != '/' and not route.endswith('/') and route not in routes and not any(x in route for x in ['{','<']):
                routes.append(route)
        req_lines=[x.strip() for x in spec.splitlines() if x.strip() and not x.strip().upper().startswith('HTTP_CHECK')]
        # Route identity includes HTTP method. Baseline discovery probes only GET surfaces;
        # mutating routes are exercised later by synthesized transactional plans.
        get_block=src
        _gm=re.search(r'def\s+do_GET\s*\([^)]*\)\s*:',src)
        if _gm:
            _end_candidates=[m.start() for m in re.finditer(r'\n\s*def\s+do_[A-Z]+\s*\(',src[_gm.end():])]
            _end=(_gm.end()+_end_candidates[0]) if _end_candidates else len(src)
            get_block=src[_gm.start():_end]
        def _implemented_as_get(route):
            return (route in get_block) or bool(re.search(r'@\w+\.get\s*\(\s*[\"\']'+re.escape(route)+r'[\"\']',src,re.I))
        for route in routes:
            if not _implemented_as_get(route):
                continue
            ranked=sorted(((_route_score(route,r),r) for r in req_lines), key=lambda x:-x[0])
            if not ranked or ranked[0][0] <= 0: continue
            # When several propositions explicitly name the same route, baseline probing
            # represents the simplest direct surface proposition. Procedural propositions
            # are verified later with before/action/after experiments.
            explicit_ranked=[x for x in ranked if route.lower() in x[1].lower()]
            if explicit_ranked:
                proc_terms={'after','before','then','successful','successfully','cancel','cancelling','create','creating','modify','increase','decrease','reduce','restore','twice'}
                explicit_ranked.sort(key=lambda x:(bool(set(_norm_words(x[1])) & proc_terms),len(x[1])))
                best_score,best_req=explicit_ranked[0]
            else:
                best_score,best_req=ranked[0]
            # Oracle synthesis is attempted against every semantically related proposition;
            # the strongest independently derivable oracle wins. This prevents a nearby
            # existence requirement from suppressing a correctness experiment.
            oracle=None; oracle_req=None; oracle_score=-1.0
            for score,req in ranked:
                if score <= 0: continue
                # An explicit route proposition is authoritative for that route. Do not
                # borrow an oracle from a merely similar neighbouring requirement; if the
                # explicit proposition needs response-schema grounding, defer synthesis to
                # the second planning phase after the probe returns its schema.
                if best_score >= 999.0 and score < 999.0: continue
                _proc_terms={'after','before','then','successful','successfully','cancel','cancelling','create','creating','modify','increase','decrease','reduce','restore','twice'}
                if set(_norm_words(req)) & _proc_terms:
                    continue
                candidate=_derive_oracle(req,route,literals)
                if candidate is not None and score > oracle_score:
                    oracle,oracle_req,oracle_score=candidate,req,score
            if oracle is None and best_score >= 999.0:
                # Requirements are often expressed as a capability proposition followed by
                # a behavioral proposition. When the exact-path proposition omits context
                # already established by its immediately preceding capability statement,
                # compose both propositions before late oracle synthesis. This is structural
                # discourse context, not a domain keyword rule.
                context_req=best_req
                try:
                    idx=req_lines.index(best_req)
                    if idx>0:
                        prev=req_lines[idx-1]
                        pw=set(_norm_words(prev))
                        if 'endpoint' in pw and bool(pw & {'provide','expose','offer','create'}) and _route_score(route,prev)>0:
                            context_req=prev+' '+best_req
                except Exception:
                    pass
                oracle_req=context_req; oracle_score=best_score
            contains=''; expected_value=None
            if oracle:
                if oracle['kind']=='json_pairs': contains=oracle['description']
                elif oracle['kind']=='json_pair': contains=f"{oracle['key']}={oracle['value']}"
                elif oracle['kind']=='number': expected_value=oracle['value']; contains=oracle['description']
            checks.append({'method':'GET','path':route,'expected_code':200,'contains':contains,
                           'expected_value':expected_value,'oracle':oracle,'planned_from':oracle_req or best_req,
                           'plan_score':oracle_score if oracle else best_score})
    if not checks:
        return {'status':'UNSUPPORTED','reason':'No explicit or safely derivable HTTP checks matched the submitted requirements.','checks':[]}
    # Use a dedicated short-lived process, then kill it.
    cmd=[sys.executable, entry.name]
    proc=subprocess.Popen(cmd,cwd=str(entry.parent),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1'})
    checks_out=[]; started=False
    try:
        deadline=time.time()+timeout
        while time.time()<deadline:
            if proc.poll() is not None: break
            try:
                import socket
                with socket.create_connection(('127.0.0.1',port),timeout=.25): started=True; break
            except OSError: time.sleep(.05)
        if not started:
            err=(proc.stderr.read() if proc.stderr else '')[-4000:]
            return {'status':'FAILED','entry':entry.relative_to(root).as_posix(),'checks':[],'reason':'Server did not become reachable before timeout.','stderr':err}
        import urllib.request, urllib.error
        all_pass=True
        for c in checks:
            url=f'http://127.0.0.1:{port}{c["path"]}'
            try:
                req=urllib.request.Request(url,method=c['method'])
                with urllib.request.urlopen(req,timeout=2) as resp:
                    body=resp.read(4096).decode('utf-8',errors='replace')
                    code=resp.status
                contains_ok=True
                # Two-phase adaptive planning: runtime response schema can ground a
                # projection that natural language alone leaves ambiguous (e.g. `time`
                # represented by `minutes`). This selects a field; it never trusts the
                # returned value as the expected value.
                if not c.get('oracle') and c.get('planned_from'):
                    try:
                        observed_obj=json.loads(body)
                        keys=list(observed_obj.keys()) if isinstance(observed_obj,dict) else []
                    except Exception:
                        keys=[]
                    late_oracle=_derive_oracle(c.get('planned_from',''),c.get('path',''),literals,keys)
                    if late_oracle:
                        c['oracle']=late_oracle
                        if late_oracle.get('kind')=='number':
                            c['expected_value']=late_oracle['value']; c['contains']=late_oracle['description']
                        elif late_oracle.get('kind')=='json_pairs': c['contains']=late_oracle['description']
                        elif late_oracle.get('kind')=='json_pair':
                            c['contains']=f"{late_oracle['key']}={late_oracle['value']}"
                if c.get('expected_value') is not None:
                    contains_ok=_json_has_number(body,c['expected_value'])
                elif (c.get('oracle') or {}).get('kind')=='json_pairs':
                    try:
                        parsed=json.loads(body); contains_ok=all(str(parsed.get(k))==str(v) for k,v in c['oracle']['pairs'])
                    except Exception: contains_ok=False
                elif c['contains']:
                    if '=' in c['contains']:
                        k,v=c['contains'].split('=',1); k=k.strip(' "\''); v=v.strip(' "\'')
                        try:
                            parsed=json.loads(body); contains_ok=str(parsed.get(k))==v
                        except Exception:
                            contains_ok=f'"{k}"' in body and v in body
                    else:
                        contains_ok=c['contains'] in body
                ok=(code==c['expected_code'] and contains_ok)
                if not ok: all_pass=False
                checks_out.append({'method':c['method'],'path':c['path'],'expected_code':c['expected_code'],'observed_code':code,'expected_contains':c['contains'],'expected_value':c.get('expected_value'),'oracle':c.get('oracle'),'planned_from':c.get('planned_from'),'observed_body':body[:500],'status':'VERIFIED' if ok else 'FAILED'})
            except Exception as e:
                all_pass=False; checks_out.append({'method':c['method'],'path':c['path'],'expected_code':c['expected_code'],'observed_code':None,'expected_contains':c['contains'],'observed_body':'','status':'FAILED','error':repr(e)})
        # Stateful/procedural verification synthesis. If the specification exposes a
        # parameterized transition/action endpoint and describes state sequences, construct
        # bounded experiments from those propositions. This is driven by discovered response
        # state and specification arrows/status codes, not by domain-specific job names.
        transition_m=re.search(r'(POST|PUT|PATCH)\s+([^\s]+(?:transition|state|status)[^\s]*)',spec,re.I)
        sequence_specs=re.findall(r'(?:sequence\s+)?([A-Za-z0-9_-]+(?:\s*->\s*[A-Za-z0-9_-]+){1,})[^\n]*?(?:attempts?\s+(?:equal\s+to|=)\s*(\d+))?',spec,re.I)
        if transition_m and sequence_specs:
            def _request(method,path):
                url=f'http://127.0.0.1:{port}{path}'
                req=urllib.request.Request(url,method=method)
                try:
                    with urllib.request.urlopen(req,timeout=2) as resp:
                        return resp.status,resp.read(4096).decode('utf-8',errors='replace')
                except urllib.error.HTTPError as e:
                    return e.code,e.read(4096).decode('utf-8',errors='replace')
            # Discover a collection and concrete identifiers from successful GET responses.
            ids=[]
            for prior in checks_out:
                if prior.get('method')!='GET' or prior.get('observed_code')!=200: continue
                try: obj=json.loads(prior.get('observed_body',''))
                except Exception: continue
                if isinstance(obj,dict):
                    for val in obj.values():
                        if isinstance(val,dict): ids.extend(str(k) for k in val.keys())
                        elif isinstance(val,list):
                            ids.extend(str(x.get('id')) for x in val if isinstance(x,dict) and x.get('id') is not None)
            ids=list(dict.fromkeys(x for x in ids if x and x!='None'))
            template=transition_m.group(2)
            method=transition_m.group(1).upper()
            def concrete_path(identifier,state):
                path=template
                path=re.sub(r'\{[^}]*id[^}]*\}|<[^>]*id[^>]*>',identifier,path,flags=re.I)
                path=re.sub(r'\{[^}]*state[^}]*\}|<[^>]*state[^>]*>',state,path,flags=re.I)
                if '<state>' in path: path=path.replace('<state>',state)
                if '{state}' in path: path=path.replace('{state}',state)
                return path
            for seq_index,(seq_text,attempt_text) in enumerate(sequence_specs):
                if seq_index>=len(ids): break
                states=[x.strip() for x in re.split(r'\s*->\s*',seq_text) if x.strip()]
                if len(states)<2: continue
                ident=ids[seq_index]
                ok_seq=True; last_body=''; last_code=None
                for state in states[1:]:
                    path=concrete_path(ident,state)
                    last_code,last_body=_request(method,path)
                    try: obj=json.loads(last_body)
                    except Exception: obj={}
                    state_ok=(last_code==200 and isinstance(obj,dict) and str(obj.get('state','')).lower()==state.lower())
                    ok_seq=ok_seq and state_ok
                if attempt_text:
                    try: obj=json.loads(last_body); ok_seq=ok_seq and int(obj.get('attempts',-999))==int(attempt_text)
                    except Exception: ok_seq=False
                checks_out.append({'method':'SEQUENCE','path':template,'expected_code':200,'observed_code':last_code,
                    'expected_contains':f'{seq_text}'+(f' attempts={attempt_text}' if attempt_text else ''),
                    'observed_body':last_body[:500],'planned_from':seq_text,'status':'VERIFIED' if ok_seq else 'FAILED',
                    'procedural':True,'sequence':states,'identifier':ident})
                if not ok_seq: all_pass=False
            # Terminal-state invariant: when the specification explicitly says a terminal
            # state rejects further transitions, exercise one more transition from that state
            # and require a 4xx response. The target state is inferred from the prose.
            terminal_m=re.search(r'\b([A-Za-z_-]+)\s+(?:job\s+)?(?:is|be)\s+terminal\b[^\n]{0,100}\breject',spec,re.I)
            if terminal_m and ids:
                terminal=terminal_m.group(1)
                # Use the first completed sequence identifier and choose a different state
                # observed in the same sequence as the attempted reopening state.
                seq_states=[x.strip() for x in re.split(r'\s*->\s*',sequence_specs[0][0]) if x.strip()]
                reopen=(seq_states[1] if len(seq_states)>1 else (seq_states[0] if seq_states else ''))
                if reopen:
                    path=concrete_path(ids[0],reopen)
                    code,body=_request(method,path)
                    ok=(400<=code<500)
                    checks_out.append({'method':method,'path':path,'expected_code':409,'observed_code':code,
                        'expected_contains':f'{terminal} is terminal; transition rejected','observed_body':body[:500],
                        'planned_from':terminal_m.group(0),'status':'VERIFIED' if ok else 'FAILED','procedural':True})
                    if not ok: all_pass=False
        # Generic constraint/consistency experiment synthesis for resource-creation APIs.
        # This is schema-driven: discover a POST collection route, a returned collection of
        # records containing ISO-like interval values, and a metadata mapping containing a
        # numeric limit. Then derive boundary/conflict cases from observed state rather than
        # relying on project/domain names.
        post_routes=[]
        for m in re.finditer(r'(?:p\.path|self\.path)\s*(?:==|!=)\s*["\'](/[^"\']+)["\']',src):
            rp=m.group(1)
            # Keep routes implemented inside do_POST blocks when identifiable.
            before=src[:m.start()]
            if before.rfind('def do_POST') > before.rfind('def do_GET') and rp not in post_routes:
                post_routes.append(rp)
        if post_routes:
            def _http(method,path):
                u=f'http://127.0.0.1:{port}{path}'
                rq=urllib.request.Request(u,method=method)
                try:
                    with urllib.request.urlopen(rq,timeout=2) as rr:
                        return rr.status,rr.read(4096).decode('utf-8',errors='replace')
                except urllib.error.HTTPError as e:
                    return e.code,e.read(4096).decode('utf-8',errors='replace')
            observed=[]
            for c0 in checks_out:
                if c0.get('method')!='GET' or c0.get('observed_code')!=200: continue
                try: ob=json.loads(c0.get('observed_body',''))
                except Exception: continue
                observed.append((c0.get('path',''),ob))
            collections=[]; mappings=[]
            for path0,ob in observed:
                if not isinstance(ob,dict): continue
                for k,v in ob.items():
                    if isinstance(v,list) and v and all(isinstance(x,dict) for x in v): collections.append((path0,k,v))
                    if isinstance(v,dict) and v and all(isinstance(x,dict) for x in v.values()): mappings.append((path0,k,v))
            def isoish(v):
                if not isinstance(v,str): return False
                try: __import__('datetime').datetime.fromisoformat(v); return True
                except Exception: return False
            experiment=None
            for _,_,rows in collections:
                row=rows[0]
                time_fields=[k for k,v in row.items() if isoish(v)]
                if len(time_fields)<2: continue
                # infer ordered interval pair by actual values
                pair=None
                for a in time_fields:
                    for b in time_fields:
                        if a==b: continue
                        try:
                            da=__import__('datetime').datetime.fromisoformat(row[a]); db=__import__('datetime').datetime.fromisoformat(row[b])
                            if da<db: pair=(a,b,da,db); break
                        except Exception: pass
                    if pair: break
                if not pair: continue
                sf,ef,ds,de=pair
                # infer categorical resource key shared with a metadata mapping
                for _,_,mp in mappings:
                    shared=[k for k,v in row.items() if str(v) in {str(x) for x in mp.keys()}]
                    if not shared: continue
                    rf=shared[0]; rid=str(row[rf]); meta=mp.get(row[rf],mp.get(rid,{}))
                    numeric_limits=[(k,v) for k,v in meta.items() if isinstance(v,(int,float)) and not isinstance(v,bool)] if isinstance(meta,dict) else []
                    numeric_row=[(k,v) for k,v in row.items() if isinstance(v,(int,float)) and not isinstance(v,bool) and k not in {'id'}]
                    # infer quantity field as one whose value fits a discovered numeric limit
                    qf=None; limit=None
                    for lk,lv in numeric_limits:
                        for qk,qv in numeric_row:
                            if qv<=lv: qf=qk; limit=lv; break
                        if qf: break
                    mid=ds+(de-ds)/2; conflict_end=de+(de-ds)/2
                    experiment={'row':row,'resource_field':rf,'resource':rid,'start_field':sf,'end_field':ef,
                                'start':mid.isoformat(timespec='minutes'),'end':conflict_end.isoformat(timespec='minutes'),
                                'quantity_field':qf,'quantity':row.get(qf,1),'limit':limit,'collection_rows':rows}
                    break
                if experiment: break
            if experiment:
                from urllib.parse import urlencode
                post_path=post_routes[0]
                params={experiment['resource_field']:experiment['resource'],experiment['start_field']:experiment['start'],experiment['end_field']:experiment['end']}
                if experiment.get('quantity_field'): params[experiment['quantity_field']]=experiment['quantity']
                # Find a GET route whose specification describes availability/consistency and
                # execute it with the exact same synthesized input as the POST action.
                get_candidates=[]
                for c0 in checks_out:
                    if c0.get('method')=='GET':
                        cp=c0.get('path','')
                        related=[ln for ln in spec.splitlines() if any(x in ln.lower() for x in ['available','availability','consistent','whether'])]
                        score=max((_route_score(cp,ln) for ln in related),default=0)
                        # Exact route mention is structural evidence and must dominate lexical similarity.
                        if any(cp and cp.lower() in ln.lower() for ln in related): score += 10000
                        if score>0: get_candidates.append((score,cp))
                # If a discovered GET route is literally named in a related requirement,
                # discard merely similar routes before choosing the experiment surface.
                exact_candidates=[x for x in get_candidates if any(x[1] and x[1].lower() in ln.lower() for ln in spec.splitlines() if any(t in ln.lower() for t in ['available','availability','consistent','whether']))]
                if exact_candidates: get_candidates=exact_candidates
                get_candidates.sort(reverse=True)
                before_count=len(experiment['collection_rows'])
                avail_result=None
                if get_candidates:
                    # Prefer an explicit GET path from the relevant specification proposition.
                    explicit_surface=None
                    for ln in spec.splitlines():
                        if any(t in ln.lower() for t in ['availability','consistent','whether']):
                            mm=re.search(r'GET\s+(/[^?\s]+)',ln,re.I)
                            if mm: explicit_surface=mm.group(1); break
                    surface=explicit_surface or get_candidates[0][1]
                    gp=surface+'?'+urlencode({k:params[k] for k in [experiment['resource_field'],experiment['start_field'],experiment['end_field']]})
                    gc,gb=_http('GET',gp)
                    try: go=json.loads(gb)
                    except Exception: go={}
                    bools=[v for v in go.values() if isinstance(v,bool)] if isinstance(go,dict) else []
                    avail_result=bools[0] if bools else None
                    checks_out.append({'method':'EXPERIMENT','path':gp,'expected_code':200,'observed_code':gc,'expected_contains':'availability derived from existing interval state','observed_body':gb[:500],'status':'INCONCLUSIVE','procedural':True,'experiment_kind':'availability'})
                pc,pb=_http('POST',post_path+'?'+urlencode(params))
                conflict_rejected=(400<=pc<500)
                checks_out.append({'method':'EXPERIMENT','path':post_path,'expected_code':409,'observed_code':pc,'expected_contains':'overlapping interval rejected without mutation','observed_body':pb[:500],
                                   'status':'VERIFIED' if conflict_rejected else 'FAILED','procedural':True,'experiment_kind':'conflict','params':params})
                if not conflict_rejected: all_pass=False
                # Cross-surface consistency: if a preflight boolean says available, creation
                # of the identical interval must not reject it as a conflict.
                if avail_result is not None:
                    consistent=(avail_result != conflict_rejected)
                    checks_out.append({'method':'INVARIANT','path':post_path,'expected_code':None,'observed_code':pc,
                        'expected_contains':'preflight availability and creation behavior agree for identical synthesized input',
                        'observed_body':f'availability={avail_result}; POST status={pc}',
                        'status':'VERIFIED' if consistent else 'FAILED','procedural':True,'experiment_kind':'cross_surface_consistency','params':params})
                    if not consistent: all_pass=False
        # Generic transactional before/action/after synthesis.
        # Parse mutating HTTP surfaces and query parameters from the specification, then
        # generate concrete values from observed GET state. This is independent of domain names.
        mut_specs=[]
        for mm in re.finditer(r'\b(POST|PUT|PATCH|DELETE)\s+(/[^\s]+)',spec,re.I):
            meth=mm.group(1).upper(); raw=mm.group(2).rstrip('.,;')
            base=raw.split('?',1)[0]
            params=re.findall(r'([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(?:<[^>]+>|\{[^}]+\})',raw)
            mut_specs.append((meth,base,params,mm.group(0)))
        if mut_specs:
            from urllib.parse import urlencode
            def _tx_http(method,path):
                rq=urllib.request.Request(f'http://127.0.0.1:{port}{path}',method=method)
                try:
                    with urllib.request.urlopen(rq,timeout=2) as rr:
                        return rr.status,rr.read(8192).decode('utf-8',errors='replace')
                except urllib.error.HTTPError as e:
                    return e.code,e.read(8192).decode('utf-8',errors='replace')
            # Fresh observable snapshots from every successful GET collection/mapping surface.
            get_surfaces=[]
            for cc in checks_out:
                if cc.get('method')=='GET' and cc.get('observed_code')==200 and '?' not in cc.get('path',''):
                    try: oo=json.loads(cc.get('observed_body',''))
                    except Exception: continue
                    if isinstance(oo,dict): get_surfaces.append((cc.get('path'),oo))
            # Prefer an action with the most parameters as the creation/mutation step.
            primary=max(mut_specs,key=lambda x:len(x[2]))
            if primary[2]:
                meth,base,param_names,_=primary
                concrete={}
                # Candidate scalar values come from observed mappings/records. Parameter names
                # are aligned structurally/lexically to discovered keys, never to a domain list.
                scalars=[]
                for _,oo in get_surfaces:
                    for top,val in oo.items():
                        if isinstance(val,dict):
                            for k,v in val.items():
                                if isinstance(v,(str,int,float)) and not isinstance(v,bool): scalars.append((str(top),str(k),v))
                                if isinstance(v,dict):
                                    for kk,vv in v.items():
                                        if isinstance(vv,(str,int,float)) and not isinstance(vv,bool): scalars.append((str(k),str(kk),vv))
                generated_id='PLUMB-'+str(int(time.time()*1000))[-7:]
                for pn in param_names:
                    pwords=set(_norm_words(pn)); best=None; bestscore=-1
                    for parent,key,val in scalars:
                        score=_semantic_similarity(pn,key+' '+parent)
                        if score>bestscore: bestscore=score; best=val
                    # Identifier-like parameters should be fresh to avoid mutating existing entities.
                    if pn.lower() in {'id','identifier','key','rid'} or pn.lower().endswith('_id'):
                        concrete[pn]=generated_id
                    elif best is not None and bestscore>0:
                        concrete[pn]=best
                    else:
                        # Numeric-looking quantity parameters are safely synthesized as 1; otherwise a neutral token.
                        concrete[pn]=1 if any(w in pwords for w in {'qty','quantity','count','amount','number','size'}) else 'PLUMB'
                # If one parameter value names a key in a numeric mapping, choose that key and a
                # bounded positive quantity no larger than its current value.
                numeric_maps=[]
                for gp,oo in get_surfaces:
                    for top,val in oo.items():
                        if isinstance(val,dict) and val and all(isinstance(x,(int,float)) and not isinstance(x,bool) for x in val.values()):
                            numeric_maps.append((gp,top,val))
                if numeric_maps:
                    gp,top,nmap=numeric_maps[0]; entity_key=next(iter(nmap)); initial_num=nmap[entity_key]
                    # Assign the categorical key to the parameter most semantically aligned with map/key context.
                    non_id=[x for x in param_names if x.lower() not in {'id','identifier','key','rid'} and not x.lower().endswith('_id')]
                    numericish=[x for x in non_id if set(_norm_words(x)) & {'qty','quantity','count','amount','number','size'}]
                    categorical=[x for x in non_id if x not in numericish]
                    cat=(categorical[0] if len(categorical)==1 else max(non_id,key=lambda x:_semantic_similarity(x,top+' key')))
                    concrete[cat]=entity_key
                    remaining=[x for x in param_names if x!=cat and x.lower() not in {'id','identifier','key','rid'} and not x.lower().endswith('_id')]
                    if remaining:
                        q=max(remaining,key=lambda x:_semantic_similarity(x,'quantity amount count number'))
                        concrete[q]=max(1,min(2,int(initial_num)))
                    before_code,before_body=_tx_http('GET',gp)
                    create_code,create_body=_tx_http(meth,base+'?'+urlencode(concrete))
                    after_code,after_body=_tx_http('GET',gp)
                    try:
                        before_obj=json.loads(before_body); after_obj=json.loads(after_body)
                        before_map=before_obj[top]; after_map=after_obj[top]
                        delta=float(before_map[entity_key])-float(after_map[entity_key])
                        requested=float(concrete.get(q,0)) if remaining else None
                        create_delta_ok=(200<=create_code<300 and requested is not None and abs(delta-requested)<1e-9)
                    except Exception:
                        create_delta_ok=False; delta=None; requested=None
                    checks_out.append({'method':'TRANSACTION','path':base,'expected_code':201,'observed_code':create_code,
                        'expected_contains':'successful mutation changes observed numeric state by exactly the requested amount',
                        'observed_body':f'before={before_body[:240]}; action={create_body[:240]}; after={after_body[:240]}; delta={delta}; requested={requested}',
                        'status':'VERIFIED' if create_delta_ok else 'FAILED','procedural':True,'experiment_kind':'state_delta_create','params':concrete})
                    if not create_delta_ok: all_pass=False
                    # Find a second mutating action sharing the generated identifier and test restoration/conservation.
                    secondary=next((x for x in mut_specs if x!=primary and any(p in x[2] for p in param_names)),None)
                    if secondary:
                        sm,sb,sparams,_=secondary
                        sp={p:concrete[p] for p in sparams if p in concrete}
                        if sp:
                            cancel_code,cancel_body=_tx_http(sm,sb+'?'+urlencode(sp))
                            final_code,final_body=_tx_http('GET',gp)
                            try:
                                final_obj=json.loads(final_body); final_map=final_obj[top]
                                restored=(float(final_map[entity_key])==float(before_map[entity_key]))
                            except Exception: restored=False
                            checks_out.append({'method':'TRANSACTION','path':sb,'expected_code':200,'observed_code':cancel_code,
                                'expected_contains':'inverse/follow-up action restores the observed numeric invariant',
                                'observed_body':f'initial={before_body[:240]}; after_first={after_body[:240]}; followup={cancel_body[:240]}; final={final_body[:240]}',
                                'status':'VERIFIED' if (200<=cancel_code<300 and restored) else 'FAILED','procedural':True,'experiment_kind':'state_restoration','params':sp})
                            if not (200<=cancel_code<300 and restored): all_pass=False
                            # Observe collection/status surfaces after both actions for traceability.
                            for cp,co in get_surfaces:
                                if cp==gp: continue
                                cc,bb=_tx_http('GET',cp)
                                checks_out.append({'method':'OBSERVE','path':cp,'expected_code':200,'observed_code':cc,
                                    'expected_contains':'post-transaction observable state','observed_body':bb[:500],
                                    'status':'VERIFIED' if cc==200 else 'FAILED','procedural':True,'experiment_kind':'post_transaction_observation','params':sp})
        return {'status':'VERIFIED' if all_pass else 'FAILED','entry':entry.relative_to(root).as_posix(),'port':port,'checks':checks_out}
    finally:
        if proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=1)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=1)

def build_verify(root: Path, discovery):
    py=[f for f in discovery['files'] if f['ext']=='.py']
    if py:
        res=run_cmd([sys.executable,'-m','compileall','-q','.'],root,20)
        return {'status':'PASSED' if res['returncode']==0 else 'FAILED','command':'python -m compileall -q .',**res}
    return {'status':'UNSUPPORTED','command':'','reason':'No Python build target is available in the current local verifier.'}

def security_summary(findings):
    sev={s:0 for s in ['CRITICAL','HIGH','MEDIUM','LOW','INFO']}
    for f in findings: sev[f['severity']]=sev.get(f['severity'],0)+1
    return {'findings':findings,'severity':sev,'status':'FINDINGS' if findings else 'NO_TESTED_ISSUES'}

def performance_summary(root, discovery):
    build=build_verify(root,discovery)
    vals=[]
    for _ in range(5):
        r=run_cmd([sys.executable,'-m','compileall','-q','.'],root,20)
        if not r['timed_out']: vals.append(r['duration_ms'])
    stats={}
    if vals:
        s=sorted(vals); stats={'samples':vals,'n':len(vals),'mean':round(statistics.mean(vals),3),'median':round(statistics.median(vals),3),'p90':round(s[min(len(s)-1,max(0,math.ceil(.9*len(s))-1))],3),'p95':round(s[min(len(s)-1,max(0,math.ceil(.95*len(s))-1))],3),'p99':round(s[min(len(s)-1,max(0,math.ceil(.99*len(s))-1))],3),'min':min(vals),'max':max(vals),'stdev':round(statistics.stdev(vals),3) if len(vals)>1 else 0}
    out={'BUILD':{'command':build.get('command',''),'status':build['status'],'stats':stats},'RUNTIME':None,'SERVICE':None,'SCALING':None}
    # Generic one-list-argument runtime/scaling timing for supported Python functions.
    import inspect, importlib.util
    candidates=[s for s in discovery['symbols'] if s['kind']=='function']
    for sym in candidates:
        if not any(k in sym['name'].lower() for k in ['duplicate','export','filter']): continue
        try:
            sp=root/sym['file']; spec=importlib.util.spec_from_file_location('plumb_perf_'+uuid.uuid4().hex,sp); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); fn=getattr(mod,sym['name']); sig=inspect.signature(fn); params=list(sig.parameters.values())
            required=[q for q in params if q.default is inspect._empty and q.kind in (q.POSITIONAL_ONLY,q.POSITIONAL_OR_KEYWORD)]
            if len(required)!=1: continue
            sizes=[25,50,100,200]
            samples=[]
            for n in sizes:
                data=list(range(n)); t0=time.perf_counter(); fn(data); elapsed=(time.perf_counter()-t0)*1000; samples.append({'input_size':n,'duration_ms':round(elapsed,4)})
            if samples:
                ratios=[]
                for i in range(1,len(samples)): ratios.append(samples[i]['duration_ms']/max(samples[i-1]['duration_ms'],1e-6))
                growth=samples[-1]['duration_ms']/max(samples[0]['duration_ms'],1e-6)
                out['RUNTIME']={'function':sym['name'],'file':sym['file'],'samples':samples}
                out['SCALING']={'function':sym['name'],'samples':samples,'growth_ratio':round(growth,2),'observed_pattern':'observed runtime growth; no formal Big-O claim'}
                break
        except Exception:
            continue
    return out

def mutation_summary(root, discovery, max_mutations=6):
    # Mutate only a temporary copy: the submitted project must never be modified.
    targets=[]; killed=0; survived=0; attempted=0; skipped=0
    baseline=execute_tests(root)
    if baseline['status'] != 'PASSED':
        return {'status':'INCONCLUSIVE','attempted':0,'killed':0,'survived':0,'skipped':0,'score':None,
                'mutations':[],'reason':'Baseline test suite did not pass; mutation score would be misleading.'}
    for s in discovery['symbols']:
        if attempted >= max_mutations or s['kind']!='function':
            if attempted >= max_mutations: break
            continue
        rel=s['file']
        norm='/' + rel.replace('\\','/')
        if '/tests/' in norm or rel.startswith('tests/') or rel.endswith('_test.py') or Path(rel).name.startswith('test_'):
            continue
        source_path=root/rel
        txt=text_read(source_path)
        start_line=s.get('line',1); end_line=s.get('end_line',start_line)
        lines=txt.splitlines()
        snippet='\n'.join(lines[start_line-1:end_line])
        m=re.search(r'(?<![=<>])(?:>=|<=|==|>|<)(?![=>])',snippet)
        if not m: continue
        old=m.group(0)
        repl={'>=':'>','<=':'<','==':'!=','>':'<=','<':'>='}[old]
        mutated_snippet=snippet[:m.start()]+repl+snippet[m.end():]
        with tempfile.TemporaryDirectory(prefix='plumb_mut_') as td:
            tmp=Path(td)/'project'
            shutil.copytree(root,tmp,dirs_exist_ok=True)
            tp=tmp/rel
            ttxt=tp.read_text(encoding='utf-8',errors='replace')
            base=ttxt.splitlines()
            # Replace the first matching operator within the discovered function span.
            span='\n'.join(base[start_line-1:end_line])
            sm=re.search(r'(?<![=<>])(?:>=|<=|==|>|<)(?![=>])',span)
            if not sm: continue
            full_prefix='\n'.join(base[:start_line-1])
            abs_idx=len(full_prefix) + (1 if start_line>1 else 0) + sm.start()
            ttxt=ttxt[:abs_idx]+repl+ttxt[abs_idx+len(old):]
            tp.write_text(ttxt,encoding='utf-8')
            res=execute_tests(tmp)
            outcome='killed' if res['status']=='FAILED' else ('survived' if res['status']=='PASSED' else 'skipped')
            if outcome=='skipped':
                skipped+=1
            else:
                attempted+=1
                if outcome=='killed': killed+=1
                else: survived+=1
            targets.append({'file':rel,'symbol':s['name'],'operator':f'{old}->{repl}','outcome':outcome,
                            'before':snippet,'after':mutated_snippet})
    score=round(killed/attempted,3) if attempted else None
    return {'status':'RAN' if attempted else 'UNSUPPORTED','attempted':attempted,'killed':killed,'survived':survived,
            'skipped':skipped,'score':score,'mutations':targets}

def _load_module_from_file(root: Path, rel: str):
    import importlib.util
    path=root/rel
    name='plumb_target_'+uuid.uuid4().hex
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: return None
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _find_symbol_file(discovery, name_patterns, kind='function'):
    for s in discovery['symbols']:
        if s['kind']==kind and all(k in s['name'].lower() for k in name_patterns): return s
    return None

def _make_task_instance(cls, ident, title, status='todo', priority=1):
    import inspect
    try:
        sig=inspect.signature(cls)
        kwargs={}
        for p in sig.parameters.values():
            if p.name in {'self'}: continue
            if p.name in {'id','task_id','identifier'}: kwargs[p.name]=ident
            elif p.name in {'title','name','label','text'}: kwargs[p.name]=title
            elif p.name in {'status','state'}: kwargs[p.name]=status
            elif p.name in {'priority','rank'}: kwargs[p.name]=priority
        if kwargs: return cls(**kwargs)
    except Exception: pass
    try: return cls(ident,title,status,priority)
    except Exception: return None

def targeted_probes(root: Path, discovery, reqs):
    results=[]
    task_cls=None
    for s in discovery['symbols']:
        if s['kind']=='class' and s['name'].lower() in {'task','todo','taskitem'}:
            task_cls=s; break
    add_s=_find_symbol_file(discovery,['add','task'])
    export_s=_find_symbol_file(discovery,['export'])
    merge_s=_find_symbol_file(discovery,['merge'])

    # Add-task probe: verify supplied fields survive the operation.
    for r in reqs:
        text=(r['title']+' '+r['description']).lower()
        if add_s and ('add task' in text or 'adding a task' in text):
            mod=_load_module_from_file(root,add_s['file'])
            if mod and hasattr(mod,add_s['name']):
                fn=getattr(mod,add_s['name'])
                try:
                    out=fn([], 'PLUMB_PROBE', 'done', 7)
                    t=out[0]
                    ok=(getattr(t,'title',None)=='PLUMB_PROBE' and getattr(t,'status',None)=='done' and getattr(t,'priority',None)==7)
                    results.append({'requirement_id':r['id'],'criterion_id':r['criteria'][0]['id'],'strategy':'RUNTIME','status':'VERIFIED' if ok else 'FAILED','hypothesis':'data_preservation','expected':'title=PLUMB_PROBE, status=done, priority=7','observed':f'title={getattr(t,"title",None)!r}, status={getattr(t,"status",None)!r}, priority={getattr(t,"priority",None)!r}','file':add_s['file'],'line':add_s.get('line')})
                    if len(r['criteria'])>1:
                        results.append({'requirement_id':r['id'],'criterion_id':r['criteria'][1]['id'],'strategy':'RUNTIME','status':'VERIFIED' if ok else 'FAILED','hypothesis':'data_preservation','expected':'All supplied task fields preserved','observed':f'{t!r}','file':add_s['file'],'line':add_s.get('line')})
                except Exception as e:
                    results.append({'requirement_id':r['id'],'criterion_id':r['criteria'][0]['id'],'strategy':'RUNTIME','status':'INCONCLUSIVE','hypothesis':'data_preservation','expected':'Add task probe executes successfully','observed':f'Exception: {e!r}','file':add_s['file'],'line':add_s.get('line')})

        # Export probe: actual filtering and empty-header behaviour.
        if export_s and ('export' in text or 'filtered' in text):
            mod=_load_module_from_file(root,export_s['file'])
            clsmod=_load_module_from_file(root,task_cls['file']) if task_cls else mod
            cls=getattr(clsmod,task_cls['name'],None) if task_cls and clsmod else None
            fn=getattr(mod,export_s['name'],None) if mod else None
            if fn and cls:
                t1=_make_task_instance(cls,1,'TODO-A','todo',1); t2=_make_task_instance(cls,2,'DONE-B','done',2)
                try:
                    out=fn([t1,t2],status='todo'); lines=list(csv.reader(io.StringIO(out)))
                    header_ok=lines and lines[0]==['id','title','status','priority']
                    rows_ok=header_ok and len(lines)==2 and lines[1][2]=='todo'
                    empty=fn([t1,t2],status='blocked'); elines=list(csv.reader(io.StringIO(empty))); empty_ok=(elines==[['id','title','status','priority']])
                    cands=[a for a in r['criteria']]
                    for idx,ok,exp,obs,hyp in [(0,header_ok,'Valid CSV output with required header',f'header={lines[0] if lines else None!r}','csv_shape'),(1,rows_ok,'Only records matching requested status are exported',f'rows={lines[1:]!r}','filter_exclusivity'),(2 if len(cands)>2 else None,empty_ok,'Empty filter returns header only',f'empty_rows={elines!r}','empty_header')]:
                        if idx is not None and idx < len(cands): results.append({'requirement_id':r['id'],'criterion_id':cands[idx]['id'],'strategy':'RUNTIME','status':'VERIFIED' if ok else 'FAILED','hypothesis':hyp,'expected':exp,'observed':obs,'file':export_s['file'],'line':export_s.get('line')})
                except Exception as e:
                    for idx in range(min(3,len(r['criteria']))): results.append({'requirement_id':r['id'],'criterion_id':r['criteria'][idx]['id'],'strategy':'RUNTIME','status':'INCONCLUSIVE','hypothesis':'csv_probe','expected':'Export probe executes safely','observed':f'Exception: {e!r}','file':export_s['file'],'line':export_s.get('line')})

        # Merge probe: exact duplicates removed, distinct same-title retained, and retained order preserved.
        if merge_s and ('merge' in text or 'incoming batch' in text or 'distinct tasks' in text or 'same title' in text):
            mod=_load_module_from_file(root,merge_s['file']); clsmod=_load_module_from_file(root,task_cls['file']) if task_cls else mod; cls=getattr(clsmod,task_cls['name'],None) if task_cls and clsmod else None; fn=getattr(mod,merge_s['name'],None) if mod else None
            if fn and cls:
                a=_make_task_instance(cls,1,'ALPHA','todo',1); dup=_make_task_instance(cls,2,'SHARED','todo',1); distinct=_make_task_instance(cls,3,'SHARED','done',2)
                try:
                    out=fn([a,dup],[dup,distinct]); ids=[getattr(x,'id',None) for x in out]; titles=[getattr(x,'title',None) for x in out]; statuses=[getattr(x,'status',None) for x in out]
                    exact_removed=(ids.count(2)==1); distinct_retained=(ids.count(2)==1 and ids.count(3)==1); order_ok=(ids[:2]==[1,2])
                    cands=r['criteria']
                    for idx,ok,exp,obs,hyp in [(0,exact_removed,'Exact duplicate occurs once in merged result',f'ids={ids!r}','exact_duplicate'),(1,distinct_retained,'Distinct records sharing a title remain distinct',f'ids={ids!r}, titles={titles!r}, statuses={statuses!r}','duplicate_preservation'),(2 if len(cands)>2 else None,order_ok,'Retained records preserve insertion order',f'ids={ids!r}','ordering_preservation')]:
                        if idx is not None and idx < len(cands): results.append({'requirement_id':r['id'],'criterion_id':cands[idx]['id'],'strategy':'RUNTIME','status':'VERIFIED' if ok else 'FAILED','hypothesis':hyp,'expected':exp,'observed':obs,'file':merge_s['file'],'line':merge_s.get('line')})
                except Exception as e:
                    for idx in range(min(3,len(r['criteria']))): results.append({'requirement_id':r['id'],'criterion_id':r['criteria'][idx]['id'],'strategy':'RUNTIME','status':'INCONCLUSIVE','hypothesis':'merge_probe','expected':'Merge probe executes safely','observed':f'Exception: {e!r}','file':merge_s['file'],'line':merge_s.get('line')})

    # Performance/scaling acceptance criteria: use actual measured scaling data when the requirement is about larger workloads.
    for r in reqs:
        text=(r['title']+' '+r['description']).lower()
        if any(k in text for k in ['larger workload','runtime growth','performance','scaling']):
            # The caller populates SCALING after this function, so this is deliberately left for analyze() to attach.
            pass
    return results

def make_evidence(analysis_id, reqs, findings, build, tests, probe_results):
    ev=[]
    for r in reqs:
        for ac in r['criteria']:
            prs=[x for x in probe_results if x.get('criterion_id')==ac['id']]
            if prs:
                pr=prs[-1]; ac_status=pr['status']
                ac['status']=ac_status
                if ac_status=='VERIFIED': ac['stage']='VERIFIED'; ac['weight']=1.0
                elif ac_status=='FAILED': ac['stage']='OBSERVED'; ac['weight']=0.2
                else: ac['stage']='TESTED'; ac['weight']=0.6
                ev.append(Evidence(str(uuid.uuid4()),analysis_id,r['id'],ac['id'],pr['strategy'],pr['hypothesis'],pr['expected'],pr['observed'],pr.get('file'),pr.get('line'),pr.get('line'),'Actual verification probe executed against the submitted implementation.',ac_status,pr))
            else:
                ac['status']='INCONCLUSIVE'; ac['stage']='IMPLEMENTED'; ac['weight']=0.5
                ev.append(Evidence(str(uuid.uuid4()),analysis_id,r['id'],ac['id'],'static','No dedicated behavioral probe',ac['text'],'Implementation was detected, but no direct behavioral evidence in the current probe set proves this criterion.',None,None,None,'Criterion remains unresolved rather than being promoted to VERIFIED.','INCONCLUSIVE'))
    for f in findings:
        ev.append(Evidence(str(uuid.uuid4()),analysis_id,None,None,'security',f['rule'],None,f['evidence'],f['file'],f['line'],f['line'],f'{f["severity"]} severity security finding','FAILED',f))
    if build.get('status'):
        ev.append(Evidence(str(uuid.uuid4()),analysis_id,None,None,'build','Build verification',build.get('command'),build.get('status'),None,None,None,build.get('stderr',''),build.get('status')))
    if tests.get('status'):
        ev.append(Evidence(str(uuid.uuid4()),analysis_id,None,None,'tests','Existing test suite','all discovered tests',f"{tests.get('passed',0)} passed, {tests.get('failed',0)} failed",None,None,None,tests.get('output',''),'VERIFIED' if tests['status']=='PASSED' else 'FAILED'))
    return ev

def score(requirements, tests, findings, mutation, performance):
    total=sum(len(r['criteria']) for r in requirements) or 1
    verified=sum(1 for r in requirements for a in r['criteria'] if a['status']=='VERIFIED')
    failed=sum(1 for r in requirements for a in r['criteria'] if a['status']=='FAILED')
    closure=verified/total
    depth=sum(sum(float(a.get('weight',0)) for a in r['criteria'])/max(1,len(r['criteria'])) for r in requirements)/max(1,len(requirements))
    test_strength=(mutation.get('score') or 0) if mutation.get('status')=='RAN' else 0
    security=max(0,1-len(findings)/10)
    score=round(100*(0.45*closure+0.25*depth+0.15*test_strength+0.15*security),1)
    if failed: verdict='FAILED'
    elif closure>=0.999: verdict='VERIFIED'
    elif closure>0: verdict='PARTIALLY_VERIFIED'
    else: verdict='INCONCLUSIVE'
    return {'score':score,'verdict':verdict,'closure':round(closure*100,1),'depth':round(depth*100,1),'verified':verified,'failed':failed,'total_criteria':total}

def analyze(root: Path, project_name: str, spec: str, claim: str):
    analysis_id=str(uuid.uuid4()); created_at=__import__('datetime').datetime.utcnow().isoformat()+'Z'
    d=discover(root); rq=map_requirements(parse_requirements(spec),d,claim,analysis_id)
    adv=targeted_probes(root,d,rq)
    findings=static_findings(root)
    build=build_verify(root,d); tests=execute_tests(root); mutation=mutation_summary(root,d); perf=performance_summary(root,d); security=security_summary(findings)
    # Runtime directives may live in the submitted project (task_spec.txt/README) even
    # when the user pastes a clean human-readable specification into the form. Use
    # those files only as verification hints; they do not create extra requirements.
    runtime_spec=spec
    for hint_name in ('task_spec.txt','TASK_SPEC.txt','spec.txt'):
        hp=root/hint_name
        if hp.exists(): runtime_spec += '\n' + text_read(hp)
    runtime=runtime_http_verify(root,runtime_spec)
    # Attach actual scaling evidence to performance-oriented acceptance criteria.
    sc=perf.get('SCALING')
    if sc:
        for r in rq:
            rtext=(r['title']+' '+r['description']).lower()
            if any(k in rtext for k in ['larger workload','runtime growth','performance','scaling','responsive','number of stored items grows']):
                for ac in r['criteria']:
                    if any(k in ac['text'].lower() for k in ['larger','workload','runtime','performance','growth','scaling','responsive','grows']):
                        growth=sc.get('growth_ratio',1)
                        status='FAILED' if growth > 12 else 'VERIFIED'
                        adv.append({'requirement_id':r['id'],'criterion_id':ac['id'],'strategy':'SCALING','status':status,'hypothesis':'scaling_behavior','expected':'No disproportionate runtime growth as input size increases','observed':f"Observed {growth}x runtime growth from input {sc['samples'][0]['input_size']} to {sc['samples'][-1]['input_size']}",'file':sc.get('file'), 'line':None})
    ev=make_evidence(analysis_id,rq,findings,build,tests,adv)

    def attach_criterion(r, ac, kind, hypothesis, expected, observed, status, details='', source=None, line=None, raw=None):
        ac['status']=status
        ac['stage']='VERIFIED' if status=='VERIFIED' else ('OBSERVED' if status=='FAILED' else 'TESTED')
        ac['weight']=1.0 if status=='VERIFIED' else (0.2 if status=='FAILED' else 0.6)
        ev.append(Evidence(str(uuid.uuid4()),analysis_id,r['id'],ac['id'],kind,hypothesis,expected,observed,source,line,line,details,status,raw))

    # Deterministic build/test evidence must resolve requirements that explicitly ask for it.
    for r in rq:
        for ac in r['criteria']:
            txt=(r['title']+' '+r['description']+' '+ac['text']).lower()
            if any(k in txt for k in ['compile successfully','source code must compile','source code should compile','compile and run successfully']):
                if build.get('status') in {'PASSED','FAILED'}:
                    attach_criterion(r,ac,'build','Build verification',build.get('command','compile'),build.get('status'),
                                     'VERIFIED' if build['status']=='PASSED' else 'FAILED',
                                     'The submitted source was compiled by the verifier.',raw=build)
            if any(k in txt for k in ['all automated tests must pass','automated test suite should pass','test suite must pass','tests must pass']):
                if tests.get('status') in {'PASSED','FAILED'}:
                    attach_criterion(r,ac,'tests','Existing test suite','All discovered tests pass',
                                     f"{tests.get('passed',0)} passed, {tests.get('failed',0)} failed",
                                     'VERIFIED' if tests['status']=='PASSED' else 'FAILED',
                                     'The submitted automated test suite was executed.',raw=tests)
            if any(k in txt for k in ['adequately detect','strongly detect','detect behavioral regressions','test resilience','mutation']):
                if mutation.get('attempted',0)>0 and mutation.get('score') is not None:
                    ms=float(mutation['score'])
                    st='VERIFIED' if ms>=0.8 else ('FAILED' if ms<0.5 else 'INCONCLUSIVE')
                    attach_criterion(r,ac,'mutation','Mutation resilience','Tests should detect injected behavioral faults',
                                     f"{mutation.get('killed',0)} of {mutation.get('attempted',0)} injected faults detected ({ms*100:.0f}%)",st,
                                     'Mutation testing directly evaluates whether the tests detect implementation regressions.',raw=mutation)

    # Bind synthesized procedural evidence to state/sequence requirements. The binding
    # compares state-transition propositions extracted from the requirement with the actual
    # executed sequence; it does not depend on application/domain vocabulary.
    procedural=[c for c in runtime.get('checks',[]) if c.get('procedural')]
    for r in rq:
        for ac in r['criteria']:
            text=(r['title']+' '+r['description']+' '+ac['text']).lower()
            arrow_states=[x.strip().lower() for x in re.split(r'\s*->\s*', text) if x.strip()] if '->' in text else []
            matched=None
            if arrow_states:
                for pc in procedural:
                    seq=[str(x).lower() for x in pc.get('sequence',[])]
                    if len(seq)>=2 and all(st in text for st in seq):
                        matched=pc; break
            if matched is None and 'terminal' in text and 'reject' in text:
                matched=next((pc for pc in procedural if 'terminal' in str(pc.get('expected_contains','')).lower()),None)
            if matched is None:
                # Atomic transition proposition: infer source and destination states from an
                # executed sequence only when both appear in order in the requirement.
                for pc in procedural:
                    seq=[str(x).lower() for x in pc.get('sequence',[])]
                    for a,b in zip(seq,seq[1:]):
                        if a in text and b in text and any(k in text for k in ['transition','retried','retry']):
                            matched=pc; break
                    if matched: break
            if matched:
                attach_criterion(r,ac,'runtime_http','Procedural verification plan',ac['text'],
                                 matched.get('observed_body',''),matched.get('status','INCONCLUSIVE'),
                                 'A multi-step stateful experiment was synthesized from the requirement and executed against the submitted service.',
                                 runtime.get('entry'),raw=matched)

    # Bind generic synthesized invariants (for example consistency between a preflight
    # surface and a mutating action) by proposition shape. These experiments are generated
    # from observed schema/state and are not tied to a particular application domain.
    invariant_checks=[c for c in procedural if c.get('experiment_kind') in {'cross_surface_consistency','conflict'}]
    for r in rq:
        for ac in r['criteria']:
            if ac.get('status') != 'INCONCLUSIVE': continue
            text=(r['title']+' '+r['description']+' '+ac['text']).lower()
            matched=None
            if any(k in text for k in ['consistent','whether','availability']):
                matched=next((c for c in invariant_checks if c.get('experiment_kind')=='cross_surface_consistency'),None)
            elif any(k in text for k in ['conflict','overlap']):
                matched=next((c for c in invariant_checks if c.get('experiment_kind')=='conflict'),None)
            if matched:
                attach_criterion(r,ac,'runtime_http','Synthesized cross-operation invariant',matched.get('expected_contains',''),
                                 matched.get('observed_body',''),matched.get('status','INCONCLUSIVE'),
                                 'PLUMB synthesized identical input from observed project state, exercised related operations, and compared their behavioral contract.',
                                 runtime.get('entry'),raw=matched)

    # Bind generic transactional state-delta evidence. The experiment is synthesized
    # from route signatures and observed state; binding uses proposition shape only.
    tx_checks=[c for c in procedural if c.get('experiment_kind') in {'state_delta_create','state_restoration','post_transaction_observation'}]
    for r in rq:
        for ac in r['criteria']:
            if ac.get('status')!='INCONCLUSIVE': continue
            text=(r.get('title','')+' '+r.get('description','')+' '+ac.get('text','')).lower()
            words=set(_norm_words(text)); matched=None
            if words & {'restore','restores','restoration','conservation','conserve'}:
                matched=next((c for c in tx_checks if c.get('experiment_kind')=='state_restoration'),None)
            elif words & {'reduce','reduces','decrease','decreases','increment','increase'}:
                matched=next((c for c in tx_checks if c.get('experiment_kind')=='state_delta_create'),None)
            if matched:
                attach_criterion(r,ac,'runtime_http','Synthesized transactional invariant',matched.get('expected_contains',''),
                    matched.get('observed_body',''),matched.get('status','INCONCLUSIVE'),
                    'PLUMB captured state before the action, executed a synthesized mutation, captured state after it, and evaluated the numeric invariant.',
                    runtime.get('entry'),raw=matched)

    # Adaptive evidence binding: each criterion chooses the best discovered capability
    # from the project model. There is no endpoint-name allowlist.
    for r_idx,r in enumerate(rq):
        for ac in r['criteria']:
            # Earlier deterministic/procedural evidence is authoritative; generic route
            # alignment must not downgrade a criterion already resolved by a stronger plan.
            if ac.get('status') != 'INCONCLUSIVE':
                continue
            txt=(r['title']+' '+r['description']+' '+ac['text']).lower()
            # Structural discourse grounding: a capability statement is commonly followed
            # by its behavioral criterion. If the next requirement names an actual discovered
            # route, use that route-bearing proposition as context for alignment. This avoids
            # choosing a nearby route by lexical similarity and requires no domain vocabulary.
            _w=set(_norm_words(txt))
            if 'endpoint' in _w and bool(_w & {'provide','expose','offer','create'}) and r_idx+1 < len(rq):
                nxt=(rq[r_idx+1]['title']+' '+rq[r_idx+1]['description']).lower()
                if any((rc.get('path','').lower() in nxt) for rc in runtime.get('checks',[]) if rc.get('path')):
                    txt += ' ' + nxt
            ranked=[]
            for rc in runtime.get('checks',[]):
                route_match_score=_route_score(rc.get('path',''),txt)
                if route_match_score>0: ranked.append((route_match_score,rc))
            if not ranked: continue
            ranked.sort(key=lambda x:-x[0]); best_score,rc=ranked[0]
            # Require a meaningful semantic relationship, not a coincidental shared noun.
            if best_score < 5: continue
            endpoint_exists=rc.get('observed_code') is not None and int(rc.get('observed_code') or 0) < 500
            explicit_path=(rc.get('path','').lower() in txt)
            try:
                _obj=json.loads(rc.get('observed_body','')); _keys=list(_obj.keys()) if isinstance(_obj,dict) else []
            except Exception:
                _keys=[]
            # A before/action/after proposition cannot be proven from a static snapshot.
            # Force it through procedural evidence rather than inventing a snapshot oracle.
            procedural_shape=bool(set(_norm_words(txt)) & {'after','before','then','successful','successfully','cancel','cancelling','create','creating','modify','changing','increase','decrease','reduce','restore','restoration','reuse','reusing','twice','rejected','reject','exceeds','without','unknown','invalid'})
            criterion_oracle=None if procedural_shape else _derive_oracle(txt,rc.get('path',''),_project_literal_data(root) if runtime.get('entry') else {},_keys)
            if (not procedural_shape) and explicit_path and rc.get('oracle') is not None:
                criterion_oracle=rc.get('oracle')
            has_oracle=criterion_oracle is not None
            words=set(_norm_words(txt))
            # Parse proposition shape rather than business vocabulary. A request to provide/
            # expose an endpoint is a capability proposition even when it describes what the
            # endpoint returns. Exact-path behavioral requirements can use synthesized oracles.
            capability_form=('endpoint' in words and bool(words & {'provide','expose','offer','create'}))
            correctness=has_oracle and not capability_form
            existence=capability_form and best_score >= 5
            if existence:
                resolved='VERIFIED' if endpoint_exists else 'FAILED'
                expected=f'{rc["method"]} {rc["path"]} is reachable and provides the requested capability'
                detail='Adaptive planner matched this requirement to the discovered route; runtime execution confirms capability existence.'
            elif correctness:
                if not endpoint_exists:
                    resolved='FAILED'
                elif criterion_oracle.get('kind')=='number':
                    resolved='VERIFIED' if _json_has_number(rc.get('observed_body',''),criterion_oracle['value']) else 'FAILED'
                elif criterion_oracle.get('kind')=='json_pairs':
                    try:
                        obj=json.loads(rc.get('observed_body','')); resolved='VERIFIED' if all(str(obj.get(k))==str(v) for k,v in criterion_oracle['pairs']) else 'FAILED'
                    except Exception: resolved='FAILED'
                elif criterion_oracle.get('kind')=='json_pair':
                    try:
                        obj=json.loads(rc.get('observed_body','')); resolved='VERIFIED' if str(obj.get(criterion_oracle['key']))==str(criterion_oracle['value']) else 'FAILED'
                    except Exception:
                        resolved='FAILED'
                else:
                    resolved='INCONCLUSIVE'
                expected=f"HTTP {rc['expected_code']} {criterion_oracle.get('description','')}".strip()
                detail=('A deterministic project-derived oracle was executed for this value/behavior requirement.' if has_oracle
                        else 'The behavior was exercised, but no independent deterministic oracle could be established; correctness is not guessed.')
            else:
                # Availability is not correctness. An explicit route proves only reachability
                # unless the proposition itself is merely a capability/existence request.
                behavioral=bool(words & {'correct','correctly','accurate','exact','equal','equals','must','should'})
                if explicit_path and behavioral:
                    resolved='INCONCLUSIVE' if endpoint_exists else 'FAILED'
                    expected='Independent deterministic oracle required'
                    detail='The route executed, but no independent deterministic oracle could be synthesized; HTTP success is not treated as correctness.'
                else:
                    resolved='VERIFIED' if endpoint_exists and explicit_path else 'INCONCLUSIVE'
                    expected=f'HTTP {rc["expected_code"]}'
                    detail='Runtime surface was exercised by the adaptive verification plan.'
            observed=f'HTTP {rc.get("observed_code")} {rc.get("observed_body","")[:120]}'
            attach_criterion(r,ac,'runtime_http',f'{rc["method"]} {rc["path"]}',expected,observed,resolved,detail,runtime.get('entry'),raw=rc)

    # Broad runtime claims are resolved only when an explicit runtime probe set exists.
    # Any failed required check contradicts the claim; a fully successful supplied check set
    # can verify a requirement that explicitly asks the application to run/work correctly.
    if runtime.get('checks') and runtime.get('status')=='VERIFIED':
        # A broad correctness claim is verified only when every exercised correctness/value
        # requirement had an independently derived assertion. Otherwise successful HTTP status
        # proves runtime availability but not arbitrary business correctness.
        # Aggregate correctness cannot be VERIFIED while any required runtime-facing
        # criterion remains unresolved. A subset of successful probes proves only that subset.
        unresolved_value=any(
            ac.get('status')=='INCONCLUSIVE' and any(k in (r.get('title','')+' '+r.get('description','')+' '+ac.get('text','')).lower()
                for k in ['runtime','http','get /','post /','put /','patch /','delete /','transition','booking','state','availability','overlap','capacity'])
            for r in rq for ac in r.get('criteria',[])
        )
        for r in rq:
            rt=(r['description']+' '+r['title']).lower()
            if any(k in rt for k in ['work correctly at runtime','compile and run successfully','run successfully']):
                for ac in r['criteria']:
                    if unresolved_value:
                        attach_criterion(r,ac,'runtime_http','Aggregate runtime verification',ac['text'],
                                         'Runtime executed, but at least one business-value requirement lacked an independently derived expected value.','INCONCLUSIVE',
                                         'Availability checks passed; full business correctness was not established.',runtime.get('entry'),raw=runtime)
                    else:
                        attach_criterion(r,ac,'runtime_http','Aggregate runtime verification',ac['text'],
                                         'All supplied runtime checks with required assertions passed.','VERIFIED',
                                         'The submitted application started and all deterministically checkable required runtime behaviors passed.',runtime.get('entry'),raw=runtime)
    if any(c.get('status')=='FAILED' for c in runtime.get('checks', [])):
        for r in rq:
            rt=(r['description']+' '+r['title']).lower()
            if 'runtime' in rt and any(k in rt for k in ['functionality','work correctly','ready','behavior','behaviour']):
                for ac in r['criteria']:
                    attach_criterion(r,ac,'runtime_http','Aggregate runtime verification',ac['text'],
                                     'At least one required runtime HTTP check failed.','FAILED',
                                     'A broad runtime-success claim is contradicted by a concrete failed endpoint check.',runtime.get('entry'),raw=runtime)

    # Map only the security rule that semantically contradicts a criterion. Do not fail an
    # unrelated security requirement merely because some other finding exists.
    for r in rq:
        for ac in r['criteria']:
            txt=(r['title']+' '+r['description']+' '+ac['text']).lower()
            relevant=[]
            if any(k in txt for k in ['secret','credential','token','password','api key']):
                relevant=[f for f in findings if f.get('rule')=='hardcoded-secret']
            elif any(k in txt for k in ['command','shell','system command']):
                relevant=[f for f in findings if f.get('rule') in {'shell-true','eval-exec'}]
            elif any(k in txt for k in ['pickle','deserialize','deserializ','untrusted bytes']):
                relevant=[f for f in findings if f.get('rule')=='pickle-load']
            elif 'secure coding' in txt or 'security practices' in txt:
                relevant=[f for f in findings if f.get('severity') in {'CRITICAL','HIGH'}]
            if relevant:
                f=relevant[0]
                attach_criterion(r,ac,'security',f['rule'],ac['text'],f['evidence'],'FAILED',
                                 'Deterministic static finding directly contradicts this acceptance criterion.',
                                 f['file'],f['line'],f)
            elif any(k in txt for k in ['hardcoded secret','hardcoded credential','hardcoded password','hardcoded api key']):
                attach_criterion(r,ac,'security','hardcoded-secret scan',ac['text'],
                                 'No matching hardcoded-secret pattern detected in scanned source.','VERIFIED',
                                 'Verified within the deterministic hardcoded-secret rule coverage; this is not a guarantee against every possible secret representation.',raw={'rule':'hardcoded-secret','matches':0})
            elif any(k in txt for k in ['unsafe shell','shell execution','unsafe system command']):
                attach_criterion(r,ac,'security','unsafe-command scan',ac['text'],
                                 'No matching unsafe shell/eval/exec pattern detected in scanned source.','VERIFIED',
                                 'Verified within the deterministic unsafe-command rule coverage.',raw={'rule':'unsafe-command','matches':0})

    # Concrete API requirements can be disproved by exhaustive inspection of a detected
    # BaseHTTPRequestHandler server. This avoids calling an obviously absent POST/create
    # path merely INCONCLUSIVE while remaining conservative for unknown frameworks.
    server_text='\n'.join(text_read(root/f['path']) for f in d['files'] if f['ext']=='.py' and (root/f['path']).exists())
    recognized_http=('BaseHTTPRequestHandler' in server_text or 'HTTPServer' in server_text)
    if recognized_http:
        has_post=('def do_POST' in server_text or '@app.post' in server_text or 'methods=[\"POST\"]' in server_text)
        for r in rq:
            rt=(r['description']+' '+r['title']).lower()
            for ac in r['criteria']:
                at=ac['text'].lower()
                if ac['status']!='INCONCLUSIVE': continue
                reason=None
                if any(k in rt+' '+at for k in ['create and retrieve','create item','add item']) and not has_post:
                    reason='No POST handler or POST route was found in the detected HTTP server.'
                elif 'invalid' in rt+' '+at and not has_post:
                    reason='The requested write/input-validation behavior cannot be exercised because the detected HTTP server exposes no POST handler or POST route.'
                if reason:
                    ac['status']='FAILED'; ac['stage']='OBSERVED'; ac['weight']=0.2
                    ev.append(Evidence(str(uuid.uuid4()),analysis_id,r['id'],ac['id'],'static_capability','Required API capability absent',ac['text'],reason,None,None,None,'Exhaustive inspection of the recognized local HTTP server found the required capability absent.','FAILED'))

    # Remove superseded generic criterion placeholders. Preserve global build/test/security
    # records, but expose only the strongest/latest conclusion for each acceptance criterion.
    latest={}
    for i,e in enumerate(ev):
        cid=e.acceptance_criterion_id
        if cid:
            rank={'static':0,'STATIC':0,'RUNTIME':2,'SCALING':3,'runtime_http':4,'security':4,'static_capability':4}.get(e.kind,1)
            cur=latest.get(cid)
            if cur is None or rank>=cur[0]: latest[cid]=(rank,i)
    keep_idx={v[1] for v in latest.values()}
    ev=[e for i,e in enumerate(ev) if not e.acceptance_criterion_id or i in keep_idx]

    # Recalculate metrics after runtime/security/capability evidence updates.
    metrics=score(rq,tests,findings,mutation,perf)
    for r in rq:
        r['status']='VERIFIED' if all(a['status']=='VERIFIED' for a in r['criteria']) else ('FAILED' if any(a['status']=='FAILED' for a in r['criteria']) else 'INCONCLUSIVE')
        r['depth_percent']=round(sum(a.get('weight',0) for a in r['criteria'])/max(1,len(r['criteria']))*100,1)
    capability={'static_analysis':'EXECUTED','python_compile':'EXECUTED' if 'Python' in d['languages'] else 'UNSUPPORTED','pytest':'EXECUTED' if d['tests'] else 'UNSUPPORTED','runtime_http':('EXECUTED' if runtime.get('checks') else ('ERROR' if runtime.get('status')=='FAILED' else 'UNSUPPORTED')),'mutation_python':('EXECUTED' if mutation.get('attempted',0)>0 else ('AVAILABLE' if 'Python' in d['languages'] else 'UNSUPPORTED')),'performance':('EXECUTED' if perf.get('SCALING') or perf.get('TIMING') else 'AVAILABLE'),'container_isolation':'UNSUPPORTED','ai_assisted_reasoning':'UNSUPPORTED'}
    payload={'analysis_id':analysis_id,'project_name':project_name,'project_hash':hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest(),'created_at':created_at,'claim':claim,'specification':spec,'languages':d['languages'],'frameworks':d['frameworks'],'files':d['files'],'symbols':d['symbols'],'requirements':rq,'evidences':[x.to_dict() for x in ev],'findings':findings,'tests':tests,'performance':perf,'mutations':mutation,'security':security,'runtime':runtime,'verdict':metrics['verdict'],'score':metrics['score'],'capability':capability,'metrics':{**metrics,'complexity':complexity(root,d),'architecture_edges':d['imports'],'test_files':d['tests']},'adversarial':adv}
    return payload
