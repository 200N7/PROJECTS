from pathlib import Path
import io, zipfile
from fastapi.testclient import TestClient
from plumb.app.ingest import ingest_zip, IngestionError
from plumb.app.analyzer import analyze
from plumb.app.report import generate_pdf
from plumb.app.main import app

ROOT=Path(__file__).resolve().parents[2]
FIX=ROOT/'fixtures'/'flagship_project'

def fixture_analysis():
    return analyze(FIX,'test', (FIX/'task_spec.txt').read_text(), (FIX/'ai_claim.txt').read_text())

def test_secure_ingest_rejects_traversal():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z: z.writestr('../evil.txt','x')
    try: ingest_zip(buf.getvalue())
    except IngestionError: return
    assert False, 'traversal archive should be rejected'

def test_flagship_catches_runtime_security_and_functional_failures():
    a=fixture_analysis()
    assert a['verdict']=='FAILED'
    assert any(r['status']=='FAILED' for r in a['requirements'])
    assert len(a['findings'])>=3
    assert a['runtime']['status']=='FAILED'
    assert any(c['path']=='/items/count' and c['status']=='FAILED' for c in a['runtime']['checks'])
    assert a['tests']['passed']==4 and a['tests']['failed']==0

def test_flagship_has_percentage_metrics():
    a=fixture_analysis(); m=a['metrics']
    assert 0 <= m['closure'] <= 100
    assert 0 <= m['depth'] <= 100
    assert m['total_criteria'] >= m['verified'] + m['failed']

def test_pdf_generation_real():
    a=fixture_analysis(); p=generate_pdf(a); data=p.read_bytes(); assert data[:4]==b'%PDF'; assert len(data)>10000

def test_api_flow_history_and_pdf():
    with TestClient(app) as c:
        zip_bytes=io.BytesIO()
        with zipfile.ZipFile(zip_bytes,'w',zipfile.ZIP_DEFLATED) as z:
            for p in FIX.rglob('*'):
                if p.is_file(): z.write(p,p.relative_to(FIX).as_posix())
        r=c.post('/api/analyses',data={'project_name':'API demo','task_spec_text':(FIX/'task_spec.txt').read_text(),'ai_completion_message':(FIX/'ai_claim.txt').read_text()},files={'project_archive':('flagship.zip',zip_bytes.getvalue(),'application/zip')})
        assert r.status_code==200
        aid=r.json()['analysis_id']
        assert c.get(f'/api/analyses/{aid}').status_code==200
        assert c.get(f'/api/analyses/{aid}/analytics').status_code==200
        pdf=c.get(f'/api/analyses/{aid}/export/pdf'); assert pdf.status_code==200 and pdf.content[:4]==b'%PDF'
        h=c.get('/api/history'); assert h.status_code==200 and any(x['analysis_id']==aid for x in h.json())


def test_plain_text_spec_is_actually_parsed():
    from plumb.app.analyzer import parse_requirements
    reqs=parse_requirements("The API must expose a health endpoint. It should reject invalid input. Results must preserve insertion order.")
    assert len(reqs) == 3
    assert reqs[0][0] == 'REQ-001'

def test_dynamic_planner_filtered_aggregates_are_domain_neutral():
    from plumb.app.analyzer import _derive_oracle
    literals={'RECORDS':[
        {'zone':'west','state':'done','duration':10,'mass':2},
        {'zone':'east','state':'done','duration':99,'mass':5},
        {'zone':'west','state':'done','duration':30,'mass':3},
        {'zone':'west','state':'open','duration':0,'mass':7},
    ]}
    avg=_derive_oracle('GET /records/west/average-duration must return the correct average duration for done records in the west zone','/records/west/average-duration',literals)
    cnt=_derive_oracle('GET /records/west/done-count must return the correct number of done records in the west zone','/records/west/done-count',literals)
    total=_derive_oracle('GET /records/west/total-mass must return the correct total mass for west zone records','/records/west/total-mass',literals)
    assert avg and avg['value']==20
    assert cnt and cnt['value']==2
    assert total and total['value']==12
