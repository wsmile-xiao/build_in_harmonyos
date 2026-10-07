"""Sign real native link outputs before original CTest post-build discovery."""
import json,os,shutil,struct,subprocess,sys
from pathlib import Path

def sign(path,cfg,allowed):
    path=Path(path).resolve()
    if not path.is_relative_to(Path(allowed).resolve()) or not path.is_file():
        raise RuntimeError("Signing path outside the exact build/package root")
    with path.open('rb') as stream:header=stream.read(20)
    if header[:4]!=b'\x7fELF' or header[5]!=1 or struct.unpack_from('<H',header,16)[0] not in (2,3):
        return
    if not cfg['ohos']:return
    env=dict(os.environ);env.pop('LD_LIBRARY_PATH',None)
    temporary=Path(str(path)+'.sign-input');signed=Path(str(path)+'.signed')
    if temporary.exists() or signed.exists():raise RuntimeError('Stale signing transaction')
    shutil.copyfile(path,temporary)
    before=subprocess.run([cfg['readelf'],'-S',str(temporary)],capture_output=True,check=True,env=env)
    if b'.codesign' in before.stdout:
        subprocess.run([cfg['objcopy'],'--remove-section','.codesign',str(temporary)],check=True,env=env)
    subprocess.run([cfg['signer'],'sign','-inFile',str(temporary),'-outFile',str(signed),'-selfSign','1'],check=True,env=env,stdout=sys.stderr)
    after=subprocess.run([cfg['readelf'],'-S',str(signed)],capture_output=True,check=True,env=env)
    if b'.codesign' not in after.stdout:raise RuntimeError('Signing returned no codesign section')
    os.replace(signed,path);temporary.unlink();path.chmod(0o755)

if __name__=='__main__':
    cfg=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    if sys.argv[2]=='--sign-package':
        sign(Path(sys.argv[4]),cfg,sys.argv[3])
    else:
        compiler=sys.argv[2];args=sys.argv[3:]
        rc=subprocess.run([compiler,*args]).returncode
        if rc:sys.exit(rc)
        output=Path(args[args.index('-o')+1]) if '-o' in args else Path('a.out')
        if output.is_file():sign(output,cfg,cfg['root'])
