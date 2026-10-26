"""macOS filesystem isolation for the TeX compiler."""
import json, os, subprocess, sys
from pathlib import Path
from .core import RelayError


def compile_tex(executable,folder,timeout=120):
    if sys.platform!='darwin' or not Path('/usr/bin/sandbox-exec').exists():
        raise RelayError('SANDBOX_REQUIRED','Local compilation currently requires the macOS sandbox. Export the ZIP to compile on another system.')
    folder=Path(folder).resolve(); binary=Path(executable).resolve()
    cache=Path.home()/'Library/Caches/TectonicProject.Tectonic'; cache.mkdir(parents=True,exist_ok=True)
    sub=lambda p:'(subpath '+json.dumps(str(p))+')'
    literal=lambda p:'(literal '+json.dumps(str(p))+')'
    profile='\n'.join([
        '(version 1)','(allow default)',
        '(deny file-read-data (require-all (require-any '+ ' '.join(sub(p) for p in ['/Users','/Volumes','/private/tmp','/private/var/folders','/System/Volumes/Data/Users','/System/Volumes/Data/Volumes','/System/Volumes/Data/private/tmp','/System/Volumes/Data/private/var/folders']) +') '+ ' '.join('(require-not '+sub(p)+')' for p in [folder,cache])+' (require-not '+literal(binary)+')))',
        '(deny file-write* (require-all (require-not '+sub(folder)+') (require-not '+sub(cache)+') (require-not '+literal('/dev/null')+')))',
    ])
    env={k:os.environ[k] for k in ('HOME','PATH','LANG','LC_ALL') if k in os.environ}
    env.update(TECTONIC_UNTRUSTED_MODE='1',TMPDIR=str(folder))
    return subprocess.run(['/usr/bin/sandbox-exec','-p',profile,str(binary),'--untrusted','--keep-logs','main.tex'],cwd=folder,env=env,capture_output=True,text=True,timeout=timeout)
