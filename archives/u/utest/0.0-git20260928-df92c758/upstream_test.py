"""Build and execute the official CMake/CTest test inventory, never a replacement."""
import argparse,hashlib,json,os
from pathlib import Path
import shutil,subprocess,sys
import xml.etree.ElementTree as ET

def call(argv,root,label,env,timeout):
    with (root/(label+'.stdout')).open('xb') as out,(root/(label+'.stderr')).open('xb') as err:
        subprocess.run(argv,stdout=out,stderr=err,env=env,check=True,timeout=timeout)

def main():
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('build')
    p.add_argument('--compiler',required=True);p.add_argument('--cxx',required=True)
    p.add_argument('--native-ohos',action='store_true');a=p.parse_args()
    source=Path(a.source).resolve();build=Path(a.build).resolve();build.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ)
    cmake=shutil.which('cmake');ctest=shutil.which('ctest')
    make=shutil.which('make')
    if not cmake or not ctest or not make:raise RuntimeError('CMake/CTest/make closure missing')
    cc,cxx=a.compiler,a.cxx
    if a.native_ohos:
        if os.uname().sysname!='HarmonyOS' or os.uname().machine!='aarch64':
            raise RuntimeError('Native HarmonyOS/aarch64 execution required')
        signer=shutil.which('binary-sign-tool')
        if not signer:raise RuntimeError('Native signer missing')
        env.update(UTEST_REAL_CC=cc,UTEST_REAL_CXX=cxx,UTEST_NATIVE_SIGNER=signer)
        driver=(source/'native_compiler.py').read_text(encoding='utf-8')
        for role in ('cc','cxx'):
            wrapper=build/('utest-'+role)
            wrapper.write_text('#!'+sys.executable+'\n'+driver,encoding='utf-8')
            wrapper.chmod(0o700)
        cc,cxx=str(build/'utest-cc'),str(build/'utest-cxx')
    # _GNU_SOURCE enables the vendored subprocess.h's musl POSIX extensions.
    # No warning or test is disabled; per-TU upstream standards remain intact.
    cflags='-D_GNU_SOURCE';cxxflags=''
    if a.native_ohos:
        # Native SDK clang injects a linker-only --code-sign option even for -c.
        # Suppress that driver-only diagnostic, not upstream source warnings.
        cflags+=' -Wno-unused-command-line-argument -DSUBPROCESS_SPAWN_VIA_FORK=1'
        cxxflags='-Wno-unused-command-line-argument'
        # Keep upstream tests and all assertions intact. Only replace their
        # temporary stdio stream backend; the installed public header is not
        # changed. Every stream is created in this fresh, task-private directory.
        private_tmp=build/'test-tmp'
        private_tmp.mkdir()
        env['TMPDIR']=str(private_tmp)
        compatibility=source/'ohos_test_tmpfile.h'
        if not compatibility.is_file():raise RuntimeError('OHOS test stdio backend missing')
        include=' -include "'+str(compatibility)+'"'
        cflags+=include;cxxflags+=include
        # Vendored subprocess.h assumes musl has addchdir_np. OHOS lacks it;
        # use its existing fork/chdir/exec error-pipe implementation, not a stub.
        # GNU make 4.4's default FIFO jobserver cannot create HMDFS FIFOs.
        # Pipe jobserver keeps the same two-job resource bound without a FIFO.
        version=subprocess.run([make,'--version'],capture_output=True,text=True,check=True,timeout=15)
        if 'GNU Make 4.4' in version.stdout:
            env['MAKEFLAGS']='--jobserver-style=pipe'
    configure=[cmake,'-S',str(source/'test'),'-B',str(build/'cmake'),
               '-DCMAKE_C_COMPILER='+cc,'-DCMAKE_CXX_COMPILER='+cxx,
               '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_C_FLAGS='+cflags,
               '-DCMAKE_CXX_FLAGS='+cxxflags,
               '-DCMAKE_MAKE_PROGRAM='+make,'-G','Unix Makefiles']
    call(configure,build,'configure',env,180)
    call([cmake,'--build',str(build/'cmake'),'--parallel','2'],build,'build',env,1200)
    env['PATH']=str(build/'cmake')+os.pathsep+env['PATH']
    listing=subprocess.run([ctest,'--test-dir',str(build/'cmake'),'--show-only=json-v1'],
                           capture_output=True,env=env,check=True,timeout=30)
    inventory=json.loads(listing.stdout);names=[t['name'] for t in inventory['tests']]
    if len(names)<4 or len(names)!=len(set(names)):raise RuntimeError('Official inventory incomplete')
    (build/'inventory.json').write_bytes(listing.stdout)
    call([ctest,'--test-dir',str(build/'cmake'),'--output-on-failure',
          '--timeout','90','--parallel','1','--output-junit',str(build/'results.xml')],
         build,'ctest',env,900)
    cases=ET.parse(build/'results.xml').getroot().findall('.//testcase')
    if sorted(c.attrib['name'] for c in cases)!=sorted(names):raise RuntimeError('CTest identity mismatch')
    if any(c.find('failure') is not None or c.find('skipped') is not None for c in cases):
        raise RuntimeError('CTest failed or skipped')
    n=len(names)
    print('INVENTORY_COUNT='+str(n));print('UPSTREAM_TEST_PASS=%d/%d PASS'%(n,n))
    print('UPSTREAM_CASES='+json.dumps(names))
    print('RESULT_XML_SHA256='+hashlib.sha256((build/'results.xml').read_bytes()).hexdigest())

if __name__=='__main__':main()
