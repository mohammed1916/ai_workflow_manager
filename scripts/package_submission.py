"""Build a clean, reproducible source ZIP without local credentials or private state."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
INCLUDE=['relay','web','data','eval','tests','scripts']
TOP=['README.md','LICENSE','.env.example','.gitignore','render.yaml']

def build(destination=None):
    output=Path(destination or ROOT/'tmp/submission/relay-research.zip');output.parent.mkdir(parents=True,exist_ok=True)
    files=[ROOT/p for p in TOP if (ROOT/p).is_file()]
    for name in INCLUDE:
        files.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and not p.is_symlink() and not any(x.startswith('.') or x=='__pycache__' for x in p.relative_to(ROOT).parts) and p.suffix not in ('.pyc',))
    manifest={}
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(set(files)):
            rel=str(p.relative_to(ROOT));body=p.read_bytes();manifest[rel]=hashlib.sha256(body).hexdigest();archive.writestr(rel,body)
        archive.writestr('manifest.json',json.dumps(manifest,indent=2))
    return output,len(manifest)

if __name__=='__main__':
    path,count=build();print(f'{path}\n{count} files; local secrets, downloaded source cache, and private state excluded.')
