from __future__ import annotations
import hashlib, os, shutil, tempfile, zipfile
from pathlib import Path
from typing import BinaryIO

MAX_ARCHIVE_BYTES=25*1024*1024
MAX_ENTRIES=5000
MAX_EXTRACTED_BYTES=100*1024*1024
ALLOWED_TEXT={'.py','.js','.jsx','.ts','.tsx','.json','.md','.txt','.toml','.yaml','.yml','.html','.css','.sql','.sh','.bat','.ps1','.env'}

class IngestionError(Exception): pass

def _safe_name(name: str):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts or name.startswith('\\') or ':' in name.split('/')[0]:
        raise IngestionError(f'Unsafe archive path: {name}')
    return str(p.as_posix())

def ingest_zip(data: bytes):
    if len(data)>MAX_ARCHIVE_BYTES: raise IngestionError('Archive exceeds 25 MiB limit.')
    root=Path(tempfile.mkdtemp(prefix='plumb_project_'))
    try:
        with zipfile.ZipFile(__import__('io').BytesIO(data)) as z:
            infos=z.infolist()
            if not infos: raise IngestionError('Empty archive.')
            if len(infos)>MAX_ENTRIES: raise IngestionError('Archive contains too many entries.')
            total=0
            for info in infos:
                name=_safe_name(info.filename)
                if name.endswith('/'): continue
                if info.is_dir(): continue
                # reject symlink entries
                mode=(info.external_attr >> 16) & 0o170000
                if mode==0o120000: raise IngestionError(f'Symlink entry rejected: {name}')
                total += info.file_size
                if total>MAX_EXTRACTED_BYTES: raise IngestionError('Archive extracted size exceeds 100 MiB limit.')
            for info in infos:
                name=_safe_name(info.filename)
                if info.is_dir() or name.endswith('/'):
                    continue
                dest=(root/name).resolve()
                if root.resolve() not in dest.parents:
                    raise IngestionError(f'Unsafe extraction path: {name}')
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info,'r') as src, dest.open('wb') as dst:
                    remaining=info.file_size
                    while remaining:
                        chunk=src.read(min(1024*1024,remaining))
                        if not chunk: break
                        dst.write(chunk); remaining-=len(chunk)
                    if remaining:
                        raise IngestionError(f'Archive entry could not be fully extracted: {name}')
        return root, hashlib.sha256(data).hexdigest()
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise
