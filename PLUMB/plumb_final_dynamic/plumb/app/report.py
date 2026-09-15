from __future__ import annotations
from pathlib import Path
from collections import Counter, defaultdict
import html
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether, HRFlowable
from reportlab.lib.units import mm
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports'/'generated'; OUT.mkdir(parents=True,exist_ok=True)
NAVY='#0b2239'; CYAN='#1ea7bd'; TEAL='#45d6e5'; RED='#d94f63'; AMBER='#d9982b'; GRID='#d8e2e8'; PALE='#eef6f8'; TEXT='#223440'; MUTED='#6d818e'

def _p(text, style): return Paragraph(str(text).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'),style)
def _labelled(label, value, style): return Paragraph(f'<b>{html.escape(str(label))}</b>: {html.escape(str(value))}', style)
def _rich_observation(title, details, expected, observed, style):
    return Paragraph(f'<b>{html.escape(str(title))}</b>: {html.escape(str(details))} Expected: {html.escape(str(expected))}. Observed: {html.escape(str(observed))}.', style)

def chart(name, figsize=(6.4,3.1)):
    return OUT/f'{name}.png'

def savefig(fig,path):
    fig.tight_layout(); fig.savefig(path,dpi=190,bbox_inches='tight',facecolor='white'); plt.close(fig); return path

def chart_closure(a):
    m=a['metrics']; p=chart('closure')
    fig,ax=plt.subplots(figsize=(6.2,3.2)); labels=['Verified','Failed','Remaining']; vals=[m['verified'],m['failed'],m['total_criteria']-m['verified']-m['failed']]
    ax.bar(labels,vals,color=[TEAL,RED,'#b9cbd4']); ax.set_ylabel('Acceptance criteria'); ax.set_title('Verification closure'); ax.spines[['top','right']].set_visible(False); ax.grid(axis='y',alpha=.2)
    for i,v in enumerate(vals): ax.text(i,v+0.05,str(v),ha='center',fontsize=9)
    return savefig(fig,p)

def chart_req_status(a):
    p=chart('req_status'); c=Counter(r['status'] for r in a['requirements']); labels=list(c); vals=[c[x] for x in labels]
    fig,ax=plt.subplots(figsize=(6.2,3.2)); ax.bar(labels,vals,color=[TEAL if x=='VERIFIED' else RED if x=='FAILED' else AMBER for x in labels]); ax.set_ylabel('Requirements'); ax.set_title('Requirement outcomes'); ax.tick_params(axis='x',rotation=24); ax.spines[['top','right']].set_visible(False); ax.grid(axis='y',alpha=.2)
    return savefig(fig,p)

def chart_depth(a):
    p=chart('depth'); rs=sorted(a['requirements'],key=lambda r:r.get('depth_percent',0)); labels=[r['id'] for r in rs]; vals=[r['depth_percent'] for r in rs]
    fig,ax=plt.subplots(figsize=(6.2,3.4)); ax.barh(labels,vals,color=CYAN); ax.set_xlim(0,100); ax.set_xlabel('Implementation depth (%)'); ax.set_title('Depth by requirement'); ax.grid(axis='x',alpha=.2); ax.spines[['top','right']].set_visible(False)
    for y,v in enumerate(vals): ax.text(min(v+2,98),y,f'{v:.0f}%',va='center',fontsize=8)
    return savefig(fig,p)

def chart_claim_gap(a):
    p=chart('claim_gap'); stage_idx={'DETECTED':1,'IMPLEMENTED':2,'TESTED':3,'MEASURED':4,'VERIFIED':5,'OBSERVED':3,'FAILED':3,'INCONCLUSIVE':2,'UNSUPPORTED':1}
    labels=[]; vals=[]
    for r in a['requirements']:
        weakest=min((stage_idx.get(ac.get('stage','DETECTED'),1) for ac in r['criteria']),default=1)
        labels.append(r['id']); vals.append(weakest)
    fig,ax=plt.subplots(figsize=(6.2,3.5)); ax.scatter(vals,range(len(labels)),s=90,color=CYAN); ax.set_yticks(range(len(labels)),labels); ax.set_xticks([1,2,3,4,5],['Detected','Implemented','Tested','Measured','Verified']); ax.set_xlim(.6,5.4); ax.set_title('Claim -> observed verification depth'); ax.grid(axis='x',alpha=.2); ax.spines[['top','right']].set_visible(False)
    return savefig(fig,p)

def chart_failure_heatmap(a):
    cats=['boundary','duplicate','ordering','type','security','runtime','performance','build']
    reqs=[r['id'] for r in a['requirements']]
    mat=np.zeros((len(reqs),len(cats)))
    for ri,r in enumerate(a['requirements']):
        for ac in r['criteria']:
            if ac['status']!='FAILED': continue
            txt=ac['text'].lower()
            hyp=[]
            if 'duplicate' in txt or 'distinct' in txt: hyp.append('duplicate')
            if 'order' in txt or 'insertion' in txt: hyp.append('ordering')
            if 'status' in txt or 'filtered' in txt: hyp.append('runtime')
            if 'larger' in txt or 'performance' in txt or 'growth' in txt: hyp.append('performance')
            if 'credential' in txt or 'unsafe' in txt or 'command' in txt: hyp.append('security')
            if '/health' in txt or '/items' in txt: hyp.append('runtime')
            if not hyp: hyp=['build']
            for h in set(hyp): mat[ri,cats.index(h)]+=1
    p=chart('failure_heatmap',(7.0,3.6)); fig,ax=plt.subplots(figsize=(7.0,3.6))
    if not mat.any():
        ax.set_axis_off(); ax.text(.5,.58,'NO REQUIREMENT CONTRADICTIONS OBSERVED',ha='center',va='center',fontsize=15,fontweight='bold',color=NAVY); ax.text(.5,.43,'No failed acceptance criteria were recorded in this verification run.',ha='center',va='center',fontsize=10,color=MUTED)
    else:
        im=ax.imshow(mat,aspect='auto',cmap='Blues',vmin=0,vmax=max(1,float(mat.max()))); ax.set_xticks(range(len(cats)),cats,rotation=35,ha='right'); ax.set_yticks(range(len(reqs)),reqs); ax.set_title('Evidence contradiction matrix')
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                if mat[i,j]: ax.text(j,i,int(mat[i,j]),ha='center',va='center',fontsize=9)
        fig.colorbar(im,ax=ax,label='Contradicted criteria')
    return savefig(fig,p)

def chart_mutation(a):
    p=chart('mutation'); m=a['mutations']; vals=[m.get('killed',0),m.get('survived',0),m.get('skipped',0)]; labels=['Killed','Survived','Skipped']
    fig,ax=plt.subplots(figsize=(6.2,3.1)); ax.bar(labels,vals,color=[TEAL,RED,'#b9cbd4']); ax.set_title('Mutation outcomes'); ax.set_ylabel('Mutations'); ax.spines[['top','right']].set_visible(False); return savefig(fig,p)

def chart_perf(a):
    p=chart('perf',(6.2,3.2)); s=a['performance'].get('BUILD',{}).get('stats') or {}; fig,ax=plt.subplots(figsize=(6.2,3.2))
    if s:
        ax.boxplot(s['samples'],vert=True,widths=.45); ax.scatter(np.ones(len(s['samples'])),s['samples'],color=CYAN,s=28); ax.set_ylabel('Build time (ms)'); ax.set_title('Observed build-time distribution'); ax.set_xticks([1],['5 runs'])
    else: ax.text(.5,.5,'No build performance measurements',ha='center',va='center'); ax.set_axis_off()
    ax.spines[['top','right']].set_visible(False); return savefig(fig,p)

def chart_scaling(a):
    p=chart('scaling',(6.2,3.2)); sc=a['performance'].get('SCALING')
    fig,ax=plt.subplots(figsize=(6.2,3.2))
    if sc and sc.get('samples'):
        x=[s['input_size'] for s in sc['samples']]; y=[s['duration_ms'] for s in sc['samples']]; ax.plot(x,y,marker='o',color=CYAN); ax.set_xlabel('Input size'); ax.set_ylabel('Observed runtime (ms)'); ax.set_title(f"Scaling: {sc['function']}"); ax.grid(alpha=.2)
    else: ax.text(.5,.5,'No scaling measurement available',ha='center',va='center'); ax.set_axis_off()
    ax.spines[['top','right']].set_visible(False); return savefig(fig,p)

def chart_security(a):
    p=chart('security',(6.2,3.2)); sev=a['security']['severity']; keys=[k for k,v in sev.items() if v]; vals=[sev[k] for k in keys]; fig,ax=plt.subplots(figsize=(6.2,3.2))
    if keys: ax.bar(keys,vals,color=RED); ax.set_title('Security findings by severity'); ax.set_ylabel('Findings'); ax.grid(axis='y',alpha=.2)
    else: ax.text(.5,.5,'No tested security issues detected',ha='center',va='center'); ax.set_axis_off()
    ax.spines[['top','right']].set_visible(False); return savefig(fig,p)

def chart_arch(a):
    p=chart('arch',(6.4,4.0)); edges=[]
    for e in a['metrics'].get('architecture_edges',[]):
        src=e.get('from',''); dst=e.get('to','')
        dst_base=dst.lstrip('.')
        candidates={Path(x['path']).with_suffix('').as_posix() for x in a['files'] if x.get('ext')=='.py'}
        if dst_base.replace('/','.') in candidates or dst_base in candidates or Path(dst).stem in {Path(x['path']).stem for x in a['files']}:
            edges.append((src,Path(dst).stem))
    fig,ax=plt.subplots(figsize=(6.4,4.0)); G=nx.DiGraph(); G.add_edges_from(edges)
    if G.nodes:
        pos=nx.spring_layout(G,seed=7); nx.draw_networkx_nodes(G,pos,ax=ax,node_color=TEAL,node_size=800); nx.draw_networkx_labels(G,pos,ax=ax,font_size=7); nx.draw_networkx_edges(G,pos,ax=ax,arrows=True,arrowstyle='-|>',arrowsize=12,edge_color=NAVY)
        ax.set_title('Project-internal dependency graph'); ax.axis('off')
    else: ax.text(.5,.5,'No project-internal import relationships detected',ha='center',va='center'); ax.axis('off')
    return savefig(fig,p)

def footer(canvas,doc):
    canvas.saveState(); canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor(MUTED)); canvas.drawString(15*mm,9*mm,'PLUMB | Evidence-first software verification'); canvas.drawRightString(195*mm,9*mm,f'Page {doc.page}');
    if doc.page == 1:
        canvas.setTitle('PLUMB Evidence-first Verification Report'); canvas.setAuthor('PLUMB'); canvas.setSubject('Software verification assessment')
    canvas.restoreState()

def make_table(data,widths,header=True):
    wrapped=[]
    styles=getSampleStyleSheet(); cell=ParagraphStyle('Cell',fontSize=7.8,leading=10,textColor=colors.HexColor(TEXT)); head=ParagraphStyle('Head',fontSize=7.8,leading=9,textColor=colors.white)
    for ridx,row in enumerate(data): wrapped.append([_p(x,head if ridx==0 and header else cell) for x in row])
    t=Table(wrapped,colWidths=widths,repeatRows=1 if header else 0,hAlign='LEFT')
    cmds=[('GRID',(0,0),(-1,-1),.3,colors.HexColor(GRID)),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]
    if header: cmds += [('BACKGROUND',(0,0),(-1,0),colors.HexColor(NAVY))]
    cmds += [('ROWBACKGROUNDS',(0,1 if header else 0),(-1,-1),[colors.white,colors.HexColor('#f7fafc')])]
    t.setStyle(TableStyle(cmds)); return t

def generate_pdf(a):
    # remove prior generated PDFs for clean deliverable directory
    for old in OUT.glob('plumb_*.pdf'):
        try: old.unlink()
        except OSError: pass
    p=OUT/f"PLUMB-{a['analysis_id']}.pdf"
    styles=getSampleStyleSheet(); styles.add(ParagraphStyle('CoverMain',fontSize=34,leading=38,alignment=TA_CENTER,textColor=colors.HexColor(NAVY),spaceAfter=7)); styles.add(ParagraphStyle('Sub',fontSize=13,leading=17,alignment=TA_CENTER,textColor=colors.HexColor(CYAN))); styles.add(ParagraphStyle('Section',fontSize=19,leading=23,textColor=colors.HexColor(NAVY),spaceAfter=6)); styles.add(ParagraphStyle('H2x',fontSize=12,leading=15,textColor=colors.HexColor(NAVY),spaceAfter=3)); styles.add(ParagraphStyle('Bodyx',fontSize=9.2,leading=13,textColor=colors.HexColor(TEXT))); styles.add(ParagraphStyle('Smallx',fontSize=7.6,leading=10,textColor=colors.HexColor(MUTED)))
    story=[]; m=a['metrics']; req_verified=sum(r['status']=='VERIFIED' for r in a['requirements']); req_total=len(a['requirements']); rem=m['total_criteria']-m['verified']; unresolved=[]
    for r in a['requirements']:
        for ac in r['criteria']:
            if ac['status']!='VERIFIED': unresolved.append((r['id'],ac['id'],ac['status'],ac['text']))
    # Cover
    story += [Spacer(1,16*mm),Paragraph('PLUMB',styles['CoverMain']),Paragraph('SOFTWARE VERIFICATION & ASSURANCE',styles['Sub']),Spacer(1,9*mm),HRFlowable(width='36%',thickness=2,color=colors.HexColor(CYAN),hAlign='CENTER'),Spacer(1,14*mm),Paragraph(html.escape(str(a['project_name'])),ParagraphStyle('ProjectTitle',parent=styles['Section'],fontSize=24,leading=29,alignment=TA_CENTER,spaceAfter=8)),Paragraph('Independent Verification Report',ParagraphStyle('ReportTitle',parent=styles['Bodyx'],fontSize=13,leading=17,alignment=TA_CENTER,textColor=colors.HexColor(MUTED))),Spacer(1,18*mm)]
    cover_data=[['Assessment status',str(a['verdict']).replace('_',' ')],['Verification coverage',f"{m['closure']}%"],['Implementation depth',f"{m['depth']}%"],['Verification ID',str(a['analysis_id'])],['Generated',str(a['created_at'])]]
    cover=make_table(cover_data,[52*mm,90*mm],header=False); cover.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#eef4f7')),('TEXTCOLOR',(0,0),(0,-1),colors.HexColor(NAVY)),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('BOX',(0,0),(-1,-1),.7,colors.HexColor(GRID)),('INNERGRID',(0,0),(-1,-1),.3,colors.HexColor(GRID)),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)])); story += [cover,Spacer(1,18*mm),Paragraph('<b>Client-ready assurance statement</b>',styles['H2x']),Paragraph('This report records the evidence observed during an independent verification run. It distinguishes executed runtime observations, test outcomes, deterministic static findings, measurements, and unsupported capabilities. Requirement-level evidence is authoritative; the summary score is contextual only.',styles['Bodyx']),Spacer(1,12*mm),HRFlowable(width='100%',thickness=1,color=colors.HexColor(GRID)),Spacer(1,4*mm),Paragraph('CONFIDENTIAL · Prepared for project stakeholders and client review',ParagraphStyle('Conf',parent=styles['Smallx'],alignment=TA_CENTER,textColor=colors.HexColor(MUTED))),PageBreak()]
    # Executive decision page
    failed_req=sum(r['status']=='FAILED' for r in a['requirements']); inconc=sum(r['status']=='INCONCLUSIVE' for r in a['requirements']); recommendation='DO NOT RELEASE / ACCEPT AS COMPLETE' if a['verdict']!='VERIFIED' else 'ACCEPT VERIFIED SCOPE'
    story += [Paragraph('Executive decision summary',styles['Section']),Paragraph('Decision-oriented summary for engineering leadership, delivery teams, and client stakeholders.',styles['Bodyx']),Spacer(1,5*mm)]
    decision=make_table([['Release recommendation',recommendation],['Verified requirements',f"{req_verified} / {req_total}"],['Failed requirements',str(failed_req)],['Inconclusive requirements',str(inconc)],['Tests executed',f"{a['tests']['passed']+a['tests']['failed']+a['tests']['skipped']} ({a['tests']['passed']} passed)"],['Security findings',str(len(a['findings']))],['Mutation resilience',f"{a['mutations'].get('killed',0)} of {a['mutations'].get('attempted',0)} injected faults detected"]],[62*mm,90*mm],header=False); story += [decision,Spacer(1,7*mm),Paragraph('Assessment interpretation',styles['H2x']),Paragraph(f"The run reached <b>{m['closure']}%</b> acceptance-criteria verification. {failed_req} requirement(s) are contradicted by recorded evidence and {inconc} remain unresolved. A passing unit-test suite is not treated as proof of requirement completion.",styles['Bodyx']),Spacer(1,6*mm),Paragraph('Priority actions',styles['H2x'])]
    priorities=[]
    for r in a['requirements']:
        if r['status']=='FAILED': priorities.append(f"<b>{r['id']}</b> — {html.escape(r['title'])}")
    if priorities: story.append(Paragraph('<br/>'.join(priorities[:6]),styles['Bodyx']))
    story += [Spacer(1,7*mm),Paragraph('Evidence integrity',styles['H2x']),Paragraph(f"Trace ID <b>{a['analysis_id']}</b>. Project hash <b>{a['project_hash'][:24]}…</b>. All report conclusions are generated from the same stored verification record used by the application.",styles['Bodyx']),PageBreak()]
    # Executive dashboard
    story += [Paragraph('1. Verification dashboard',styles['Section']),Paragraph('A compact view of what reached verification and what remains unresolved.',styles['Bodyx']),Spacer(1,4*mm)]
    kpi=[['Acceptance criteria verified',f"{m['verified']} / {m['total_criteria']} ({m['closure']}%)"],['Acceptance criteria remaining',f"{rem} / {m['total_criteria']} ({100-m['closure']:.1f}%)"],['Requirements fully verified',f"{req_verified} / {req_total} ({(100*req_verified/req_total) if req_total else 0:.1f}%)"],['Implementation depth',f"{m['depth']}%"],['Verification score',f"{a['score']} / 100"],['Existing test suite',f"{a['tests']['passed']} passed / {a['tests']['failed']} failed"],['Security findings',str(len(a['findings']))],['Mutation score',f"{a['mutations'].get('score',0)*100:.0f}% ({a['mutations'].get('killed',0)} of {a['mutations'].get('attempted',0)} injected faults caught)" if a['mutations'].get('score') is not None else 'N/A']]
    story += [make_table([['Metric','Result']]+kpi,[65*mm,75*mm]),Spacer(1,5*mm),Image(str(chart_closure(a)),width=88*mm,height=45*mm),Image(str(chart_req_status(a)),width=88*mm,height=45*mm),PageBreak()]
    # Requirements & claim reality
    story += [Paragraph('2. Requirements: completion and remaining gap',styles['Section']),Paragraph(a['specification'],styles['Bodyx']),Spacer(1,4*mm)]
    rows=[['Requirement','Status','Depth','Verified','Remaining']]
    for r in a['requirements']:
        v=sum(ac['status']=='VERIFIED' for ac in r['criteria']); rows.append([r['id']+' - '+r['title'],r['status'],f"{r['depth_percent']}%",f'{v}/{len(r["criteria"])}',str(len(r['criteria'])-v)])
    story += [make_table(rows,[66*mm,34*mm,24*mm,28*mm,24*mm]),Spacer(1,4*mm),Image(str(chart_depth(a)),width=145*mm,height=72*mm),PageBreak(),Paragraph('Verification depth and evidence posture',styles['Section']),Paragraph('This view shows how far each requirement progressed from detection toward direct verification. It is an evidence-stage view, not a completion claim.',styles['Bodyx']),Spacer(1,4*mm),Image(str(chart_claim_gap(a)),width=155*mm,height=82*mm),Spacer(1,5*mm),Paragraph('How to read this report',styles['H2x']),Paragraph('Executed runtime observations, test results, static findings, measurements, and unsupported capabilities are kept distinct. FAILED means evidence contradicted the criterion; INCONCLUSIVE means the available evidence was insufficient.',styles['Bodyx']),Spacer(1,5*mm),Paragraph('Evidence classes used in this assessment',styles['H2x']),make_table([['Evidence class','What it means'],['Runtime observation','The submitted application was started and a defined behavior was exercised.'],['Test execution','The submitted automated test suite was executed and its outcome recorded.'],['Static finding','Source code was inspected deterministically for a specific capability or risk pattern.'],['Measurement','A bounded timing or scaling probe was executed against submitted code.'],['Unsupported','The current execution environment cannot safely perform the requested verification.']],[38*mm,125*mm]),Spacer(1,4*mm),Paragraph('Client interpretation',styles['H2x']),Paragraph('This report is an assurance record, not a certification. Conclusions apply to the submitted project snapshot and the capabilities exercised in this run. Evidence-backed requirement statuses are the primary decision signal.',styles['Smallx']),PageBreak()]
    # Evidence and failure map
    story += [Paragraph('3. Evidence-backed verification',styles['Section']),Paragraph('Important conclusions are represented as expected behavior, observed behavior, source evidence, and resulting status.',styles['Bodyx']),Spacer(1,3*mm)]
    failed_rows=[['Criterion','Status','Expected','Observed / evidence']]
    for e in a['evidences']:
        if e.get('acceptance_criterion_id') and e.get('status') in {'FAILED','VERIFIED','INCONCLUSIVE'}:
            failed_rows.append([e['acceptance_criterion_id'],e.get('status',''),e.get('expected',''),(e.get('observed','') or '')[:180]])
    story += [make_table(failed_rows[:20],[30*mm,25*mm,55*mm,55*mm]),Spacer(1,5*mm),Image(str(chart_failure_heatmap(a)),width=165*mm,height=82*mm),PageBreak()]
    # Testing / mutation
    mut_attempted=a['mutations'].get('attempted',0); mut_score=a['mutations'].get('score'); mut_explain=(f"Mutation testing injected {mut_attempted} valid code changes; {a['mutations'].get('killed',0)} were caught and {a['mutations'].get('survived',0)} survived. A {mut_score*100:.0f}% mutation score means the tests detected that share of the injected faults." if mut_attempted and mut_score is not None else f"Mutation testing did not produce a valid mutation score in this run. {a['mutations'].get('reason','No valid mutation candidates were available.')}"); story += [Paragraph('4. Testing strength',styles['Section']),Paragraph(f"The submitted project test suite reports {a['tests']['passed']} passed and {a['tests']['failed']} failed. {mut_explain}",styles['Bodyx']),Spacer(1,4*mm),Image(str(chart_mutation(a)),width=105*mm,height=55*mm),Spacer(1,3*mm)]
    if a['mutations'].get('mutations'):
        mr=[['File','Function','Mutation','Outcome']]+[[x['file'],x['symbol'],x['operator'],x['outcome']] for x in a['mutations']['mutations']]
        story.append(make_table(mr,[50*mm,40*mm,35*mm,25*mm]))
    story += [Spacer(1,5*mm),Paragraph('Adversarial / mutation observations',styles['H2x'])]; _seen_obs=set()
    for e in a['evidences']:
        if e.get('kind') in {'adversarial','runtime_http'}:
            story.append(_rich_observation(e['title'], e.get('details',''), e.get('expected',''), e.get('observed',''), styles['Smallx']))
    story += [PageBreak()]
    # Performance + runtime
    story += [Paragraph('5. Performance and runtime verification',styles['Section']),Paragraph('Performance measurements are separated by purpose. Timing values describe observed runs, not universal guarantees.',styles['Bodyx']),Spacer(1,4*mm),Image(str(chart_perf(a)),width=100*mm,height=52*mm),Image(str(chart_scaling(a)),width=100*mm,height=52*mm)]
    if a.get('runtime'):
        r=a['runtime']; story += [Spacer(1,3*mm),Paragraph(f"Runtime verification: {'EXECUTED' if r.get('checks') else r.get('status','UNSUPPORTED')} | Target checks: {sum(1 for c in r.get('checks',[]) if c.get('status')=='VERIFIED')} verified / {sum(1 for c in r.get('checks',[]) if c.get('status')=='FAILED')} failed | Entry: {r.get('entry','-')}",styles['Bodyx'])]
        rr=[['Endpoint','Expected','Observed','Status']]+[[c['method']+' '+c['path'],f"HTTP {c['expected_code']} {c.get('expected_contains','')}",f"HTTP {c.get('observed_code')} {c.get('observed_body','')[:80]}",c['status']] for c in r.get('checks',[])]
        if len(rr)>1: story += [Spacer(1,3*mm),make_table(rr,[48*mm,42*mm,56*mm,25*mm])]
    story += [Spacer(1,5*mm),Paragraph('Performance interpretation',styles['H2x']),Paragraph('Observed timings are environment-specific. A scaling failure indicates that the measured growth pattern exceeded the bounded verification expectation; it should be reproduced under production-like load before capacity commitments are made.',styles['Smallx']),PageBreak()]
    # Security + architecture
    story += [Paragraph('6. Security and architecture',styles['Section']),Image(str(chart_security(a)),width=100*mm,height=52*mm)]
    if a['findings']:
        sr=[['Severity','Rule','File','Line','Evidence']]+[[f['severity'],f['rule'],f['file'],str(f['line']),f['evidence']] for f in a['findings']]
        story += [Spacer(1,3*mm),make_table(sr,[22*mm,32*mm,35*mm,12*mm,62*mm])]
    arch_edges = a['metrics'].get('architecture_edges',[])
    if arch_edges:
        story += [Spacer(1,4*mm),Image(str(chart_arch(a)),width=150*mm,height=75*mm),Spacer(1,3*mm)]
    else:
        story += [Spacer(1,4*mm),Paragraph('Architecture evidence',styles['H2x']),Paragraph('No project-internal import relationships were detected in the submitted source. Standard-library and external dependencies are intentionally excluded from the architecture graph so the report does not imply relationships that are not present in the project.',styles['Smallx']),Spacer(1,4*mm)]
    story += [Paragraph('Project inventory',styles['H2x'])]
    inv=[['File','Language','Lines','Symbols']]+[[f['path'],f.get('language','Other'),str(f.get('lines',0)),str(len(f.get('symbols',[])))] for f in a['files'] if f.get('language') in {'Python','JavaScript','TypeScript'}][:14]
    story += [make_table(inv,[72*mm,35*mm,22*mm,25*mm]),PageBreak()]
    # Scope & unresolved
    story += [Paragraph('7. What remains unresolved',styles['Section']),Paragraph(f"<b>{100-m['closure']:.1f}%</b> of acceptance criteria are not fully verified in this run. These are not all the same kind of gap; PLUMB separates failed behavior from insufficient evidence.",styles['Bodyx']),Spacer(1,4*mm)]
    ur=[['Requirement','Criterion','Status','Criterion / reason']]+[[x[0],x[1],x[2],x[3]] for x in unresolved]
    story += [make_table(ur,[24*mm,30*mm,28*mm,78*mm]),Spacer(1,5*mm),Paragraph('Verification capabilities',styles['H2x'])]
    cr=[['Capability','Status']]+[[k,v] for k,v in a['capability'].items()]; story += [make_table(cr,[65*mm,70*mm]),Spacer(1,4*mm),Paragraph('Current execution is local-first and subprocess-based. This is not Docker-grade isolation. Unsupported capabilities are not treated as passes.',styles['Smallx']),PageBreak()]
    # Final assessment
    mut_note = (' Test resilience is <b>WEAK</b>: none of the injected faults were detected.' if a['mutations'].get('attempted',0)>0 and a['mutations'].get('killed',0)==0 else '')
    story += [Paragraph('8. Final assessment',styles['Section']),Paragraph(f"PLUMB reached <b>{m['closure']}%</b> acceptance-criteria closure and <b>{m['depth']}%</b> implementation depth. The deterministic final verdict for this verification run is <b>{a['verdict']}</b>.{mut_note} The summary score ({a['score']}/100) is contextual; requirement-level evidence remains authoritative.",styles['Bodyx']),Spacer(1,5*mm)]
    story += [Paragraph('Interpretation',styles['H2x']),Paragraph('A VERIFIED status means the defined applicable evidence for that criterion passed. FAILED means the recorded verification contradicted the expected behavior. INCONCLUSIVE means the available evidence does not justify a definitive result. UNSUPPORTED means the current environment cannot perform the required check.',styles['Bodyx']),Spacer(1,5*mm),Paragraph('Evidence principle',styles['H2x']),Paragraph('AI completion messages are claims. PLUMB uses project inspection, actual tests, observations, measurements, and recorded evidence to determine what can be stated with confidence.',styles['Bodyx']),Spacer(1,5*mm),Paragraph('Audit trail and reproducibility',styles['H2x']),Paragraph('The verification ID, project hash, executed probes, observed outputs, findings, and capability limitations travel with this report. The summary score is a navigation aid; requirement statuses and their cited evidence remain the authoritative conclusions.',styles['Bodyx']),Spacer(1,8*mm),HRFlowable(width='100%',thickness=1,color=colors.HexColor(CYAN)),Spacer(1,3*mm),Paragraph(f"Verification ID: {a['analysis_id']} | Project hash: {a['project_hash'][:16]}... | Report generated from the same stored verification record used by the application.",styles['Smallx'])]
    doc=SimpleDocTemplate(str(p),pagesize=A4,rightMargin=14*mm,leftMargin=14*mm,topMargin=14*mm,bottomMargin=14*mm)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return p
