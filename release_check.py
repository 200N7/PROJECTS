from __future__ import annotations
import hashlib, os, signal, socket, subprocess, sys, tempfile, time, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIX = ROOT/'fixtures'/'flagship_project'


def run(cmd, cwd=ROOT, timeout=25):
    try:
        p=subprocess.run(cmd,cwd=str(cwd),capture_output=True,text=True,timeout=timeout,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1'})
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f'TIMEOUT ({timeout}s): {cmd!r}') from e
    if p.returncode != 0:
        raise RuntimeError(f'FAILED ({p.returncode}): {cmd!r}\nSTDOUT:\n{p.stdout[-2500:]}\nSTDERR:\n{p.stderr[-2500:]}')
    return p


def sha_tree(base: Path):
    h=hashlib.sha256()
    for p in sorted(base.rglob('*')):
        if not p.is_file() or any(x in {'.git','__pycache__','.pytest_cache'} for x in p.parts):
            continue
        h.update(p.relative_to(base).as_posix().encode()); h.update(b'\0'); h.update(p.read_bytes()); h.update(b'\0')
    return h.hexdigest()


def stop_tree(proc):
    if proc.poll() is not None: return
    if os.name == 'nt':
        subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
    else:
        try: os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception: proc.terminate()
    try: proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        if os.name == 'nt': subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
        else:
            try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception: proc.kill()
        proc.wait(timeout=3)


def wait_port(port, timeout=5):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        with socket.socket() as s:
            s.settimeout(.25)
            try: s.connect(('127.0.0.1',port)); return True
            except OSError: time.sleep(.05)
    return False


def main():
    print('=== PLUMB RELEASE CHECK (bounded, deterministic) ===')
    before=sha_tree(FIX)

    # Canonical flagship run. verify.py itself analyzes a disposable copy.
    p=run([sys.executable,'verify.py'],timeout=90)
    print(p.stdout)
    after=sha_tree(FIX)
    assert before==after, 'flagship fixture changed during verification'
    print('PASS: fixture immutable')

    # Deterministic content assertions from the real verified run.
    out=p.stdout
    required=[
        'verdict: FAILED',
        'criteria closure:',
        'tests: 4 passed, 0 failed',
        'security findings: 3',
        "('/health', 'VERIFIED')",
        "('/items/count', 'FAILED')",
        'scaling:',
        'report:',
    ]
    for item in required:
        assert item in out, f'missing verified output: {item}'
    print('PASS: flagship assertions')

    # Python source compilation for the product.
    run([sys.executable,'-m','compileall','-q','plumb','verify.py','run.py','release_check.py'],timeout=12)
    print('PASS: project compilation')

    # Live server smoke. Use a new process group so termination is guaranteed.
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0
    preexec_fn = None if os.name=='nt' else os.setsid
    proc=subprocess.Popen([sys.executable,'run.py'],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=creationflags,preexec_fn=preexec_fn,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    try:
        assert wait_port(8000,6), 'server did not start'
        run([sys.executable,'-c','import urllib.request; r=urllib.request.urlopen("http://127.0.0.1:8000/healthz",timeout=3); assert r.status==200'],timeout=6)
        print('PASS: live health API')
    finally:
        stop_tree(proc)
    assert not wait_port(8000,1), 'server still listening after termination'
    print('PASS: server termination')

    # Normalize final PDF location and clean generated variants.
    generated=sorted((ROOT/'reports'/'generated').glob('PLUMB-*.pdf'))
    assert generated, 'verification did not produce a PDF'
    final=ROOT/'reports'/'PLUMB-final-report.pdf'
    shutil.copy2(generated[-1],final)
    for pth in generated:
        if pth != final: pth.unlink(missing_ok=True)
    print('PASS: canonical final PDF:', final.name)

    # No build junk in the submission tree.
    for pth in list(ROOT.rglob('*')):
        if not pth.is_file(): continue
        rel=pth.relative_to(ROOT)
        if any(x in {'.git','__pycache__','.pytest_cache'} for x in rel.parts) or pth.suffix=='.pyc':
            pth.unlink()
    print('PASS: release tree cleaned')
    print('=== RELEASE CHECK PASSED ===')

if __name__=='__main__': main()
