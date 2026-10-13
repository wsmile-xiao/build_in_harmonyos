"""Real build2 Testscript execution on HarmonyOS projected-UID user storage."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,shutil

def main():
    binary=Path(sys.argv[1]).resolve(strict=True)
    parent=Path(sys.argv[2]).resolve(strict=True)
    if os.uname().sysname!='HarmonyOS' or os.uname().machine!='aarch64':
        raise RuntimeError('HarmonyOS/aarch64 required')
    if not parent.is_relative_to(Path('/storage/Users/currentUser')):
        raise RuntimeError('HMDFS user-storage test root required')
    root=Path(tempfile.mkdtemp(prefix='build2-hmdfs-',dir=parent))
    # Keep the native driver's cwd in the same application cache namespace
    # already used by the real upstream build. The input/output remain on
    # HMDFS: this is not a claim that getcwd on HMDFS works.
    cache=Path('/data/storage/el2/base/cache').resolve(strict=True)
    if not cache.is_dir():raise RuntimeError('Application-private cache required')
    project=Path(tempfile.mkdtemp(prefix='build2-hmdfs-driver-',dir=cache))
    try:
        # build2 starts its real FIFO jobserver in TMPDIR, even with -j 1.
        # HMDFS is the data fixture, not a POSIX FIFO filesystem. Keep the
        # ordinary jobserver enabled and give it this invocation's own cache.
        private_tmp=project/'tmp'
        private_tmp.mkdir()
        (project/'build').mkdir()
        (project/'build/bootstrap.build').write_text(
            'project = hmdfs-test\namalgamation =\nsubprojects =\nusing test\n',encoding='utf-8')
        (project/'buildfile').write_text('./: testscript{hmdfs}\n',encoding='utf-8')
        source=root/'输入 数据.bin';output=root/'输出 数据.bin'
        if any(c in str(root) for c in ('"','$','\\','\n','\r')):
            raise RuntimeError('Unsafe generated HMDFS path')
        (project/'hmdfs.testscript').write_text(
            'cp --no-cleanup "'+str(source)+'" "'+str(output)+'"\n',encoding='utf-8')
        payload='HarmonyOS 投射 UID 与 UTF-8 路径\n'.encode('utf-8')+bytes(range(256))
        source.write_bytes(payload)
        projected_uid=source.stat().st_uid
        if projected_uid==os.getuid():
            raise RuntimeError('HMDFS projected-owner behavior not observed')
        result=subprocess.run([str(binary),'--no-default-options','-j','1','-v','test'],
                              cwd=project,env=dict(os.environ,PWD=str(project),
                                  TMPDIR=str(private_tmp),TMP=str(private_tmp),
                                  TEMP=str(private_tmp),TEMPDIR=str(private_tmp)),
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
        sys.stdout.buffer.write(result.stdout);sys.stdout.buffer.flush()
        if result.returncode or not output.is_file() or output.read_bytes()!=payload or source.read_bytes()!=payload:
            raise RuntimeError('Actual build2 HMDFS Testscript copy or exact-byte check failed: '+str(result.returncode))
        print(json.dumps({'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
                          'platform':list(os.uname()),'process_uid':os.getuid(),'projected_uid':projected_uid,
                          'root':str(root),'rc':result.returncode,'bytes':len(payload),
                          'driver_cwd':str(project),'cwd_boundary':'app-private cache; absolute HMDFS data paths',
                          'fifo_tmpdir':str(private_tmp),'jobserver':'upstream default FIFO; not disabled',
                          'sha256':hashlib.sha256(payload).hexdigest()},ensure_ascii=False),flush=True)
    finally:
        if project.is_symlink() or project.resolve().parent!=cache:
            raise RuntimeError('Task-owned driver cleanup identity mismatch')
        shutil.rmtree(project)
        if root.is_symlink() or root.resolve().parent!=parent:
            raise RuntimeError('Task-owned cleanup identity mismatch')
        shutil.rmtree(root)
    if root.exists():raise RuntimeError('HMDFS test cleanup incomplete')
    if project.exists():raise RuntimeError('Driver test cleanup incomplete')
    print('HARMONY_TEST_PASS=1/1',flush=True)

if __name__=='__main__':main()
