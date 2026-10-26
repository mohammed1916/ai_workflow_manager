#!/usr/bin/env python3
"""Install the pinned official Tectonic binary into this project's private tools."""
import io, platform, tarfile, urllib.request
from pathlib import Path
if platform.system()!='Darwin': raise SystemExit('This local compiler integration currently supports macOS.')
arch='aarch64' if platform.machine()=='arm64' else 'x86_64'
url=f'https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.17.0/tectonic-0.17.0-{arch}-apple-darwin.tar.gz'
with urllib.request.urlopen(url,timeout=60) as r: data=r.read(50000000)
with tarfile.open(fileobj=io.BytesIO(data)) as archive:
    member=next(m for m in archive.getmembers() if m.isfile() and m.name.split('/')[-1]=='tectonic')
    binary=archive.extractfile(member).read()
path=Path(__file__).resolve().parents[1]/'.relay/bin/tectonic'
path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(binary);path.chmod(0o755)
print(f'Installed official Tectonic 0.17.0: {path}')
