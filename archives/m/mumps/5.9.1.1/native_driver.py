"""Source compiler driver: bind native SDK/MPI/Flang; sign generated ELF, not binary-patch it."""
import json,os,shutil,subprocess,sys
from pathlib import Path
from shlex import quote
ROOT=Path(__file__).resolve().parent
C=json.loads((ROOT/'native-inputs.json').read_text(encoding='utf8'))

def shared_link_arguments(args):
    """Set each delivered shared object's own basename, not a build-tree path."""
    args=list(args)
    if '-shared' not in args or '-o' not in args or any(a in args for a in ('-c','-E','-S')):
        return args
    name=Path(args[args.index('-o')+1]).name
    libraries={'lib'+n+'.so' for n in ('smumps','dmumps','cmumps','zmumps','mumps_common','pord')}
    if name not in libraries:
        return args
    explicit=[a for a in args if a.startswith(('-Wl,-soname,','-Wl,--soname,'))]
    if explicit:
        if len(explicit)!=1 or explicit[0].split(',',2)[2]!=name:
            raise RuntimeError('Mismatched shared library SONAME: '+name)
    else:
        args.append('-Wl,-soname,'+name)
    return args

def sign(path):
    path=Path(path).resolve()
    assert path.is_relative_to(ROOT) and path.is_file()
    temporary=Path(str(path)+'.sign-input');signed=Path(str(path)+'.signed')
    assert not temporary.exists() and not signed.exists()
    env=dict(os.environ);env['LD_LIBRARY_PATH']=C['llvm_lib']
    shutil.copyfile(path,temporary)
    sections=subprocess.check_output([C['readelf'],'-S',str(temporary)],env=env)
    if b'.codesign' in sections:
        subprocess.run([C['objcopy'],'--remove-section','.codesign',str(temporary)],env=env,check=True)
    subprocess.run([C['signer'],'sign','-inFile',str(temporary),'-outFile',str(signed),'-selfSign','1'],env=env,check=True)
    assert b'.codesign' in subprocess.check_output([C['readelf'],'-S',str(signed)],env=env)
    os.replace(signed,path);temporary.unlink();path.chmod(0o755)

def main():
    mode,args=sys.argv[1],shared_link_arguments(sys.argv[2:])
    linking=not any(a in args for a in ('-c','-E','-S','-show','--show','-v','--version'))
    env=os.environ.copy()
    if mode=='fortran':
        fc=[C['flang']+'/bin/flang','--target=aarch64-linux-ohos','--sysroot='+C['sysroot'],
            '-resource-dir',C['resource'],'-B',C['llvm_bin'],'-L'+C['target_lib'],'-L'+C['flang']+'/lib']
        env['MPICH_FC']=' '.join(quote(a) for a in fc)
        argv=[C['mpi']+'/bin/mpifort',*args]
    else:
        assert mode=='c'
        argv=[C['raw_cc'],'--sysroot='+C['sysroot'],'-D__MUSL__',*args]
        if linking:argv+=['-fuse-ld=lld','-L'+C['sysroot']+'/usr/lib/aarch64-linux-ohos']
    if linking:argv+=['-Wl,--code-sign']
    rc=subprocess.run(argv,env=env).returncode
    if rc:return rc
    if '-o' in args:
        path=Path(args[args.index('-o')+1])
        if path.is_file():
            with path.open('rb') as f:h=f.read(20)
            if h[:4]==b'\x7fELF' and int.from_bytes(h[16:18],'little') in (2,3):sign(path)
    return 0
if __name__=='__main__':sys.exit(main())
