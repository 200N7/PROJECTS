from pathlib import Path
import shutil, tempfile
from plumb.app.analyzer import analyze
from plumb.app.report import generate_pdf

ROOT=Path(__file__).resolve().parent
FIX=ROOT/'fixtures'/'flagship_project'

def main():
    spec=(FIX/'task_spec.txt').read_text(encoding='utf-8')
    claim=(FIX/'ai_claim.txt').read_text(encoding='utf-8')
    # Analyze a disposable copy so mutation/probe execution can never alter the shipped fixture.
    with tempfile.TemporaryDirectory(prefix='plumb_verify_') as td:
        target=Path(td)/'flagship_project'
        shutil.copytree(FIX,target,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','*.pyc'))
        a=analyze(target,'PLUMB Flagship Demo',spec,claim)
        p=generate_pdf(a)
    print('PLUMB verification complete')
    print('verdict:',a['verdict'])
    print('score:',a['score'])
    print('criteria closure:',f"{a['metrics']['verified']}/{a['metrics']['total_criteria']} ({a['metrics']['closure']}%)")
    print('implementation depth:',f"{a['metrics']['depth']}%")
    print('tests:',a['tests']['passed'],'passed,',a['tests']['failed'],'failed')
    print('security findings:',len(a['findings']))
    if a.get('runtime'): print('runtime:',a['runtime']['status'],[(c['path'],c['status']) for c in a['runtime'].get('checks',[])])
    if a.get('performance',{}).get('SCALING'): print('scaling:',a['performance']['SCALING']['growth_ratio'],'x observed growth')
    print('report:',p)

if __name__=='__main__': main()
