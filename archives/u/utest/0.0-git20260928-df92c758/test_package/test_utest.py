"""Compile installed-header consumers and the real OHOS libc timer test."""
import argparse,os
from pathlib import Path
import re,shutil,subprocess,sys,tempfile

SMOKE_C=r'''
#include <utest.h>
#include <stdlib.h>
#include <string.h>
UTEST(consumer, allocated_state) {
    int *state=(int *)calloc(3,sizeof(int));
    ASSERT_TRUE(state!=NULL);
    state[0]=7;state[1]=11;state[2]=state[0]+state[1];
    EXPECT_EQ(18,state[2]);
    free(state);
}
UTEST(consumer, string_comparison) {
    char buffer[16];
    memcpy(buffer,"utest-consumer",15);
    EXPECT_STREQ("utest-consumer",buffer);
    EXPECT_EQ(14,strlen(buffer));
}
UTEST_MAIN()
'''

def check_counts(text,n):
    if not re.search(r'\[\s*PASSED\s*\]\s*'+str(n)+r' tests\.',text):
        raise RuntimeError('Exact test denominator missing')
    if re.search(r'\[\s*(?:FAILED|SKIPPED)\s*\]',text):raise RuntimeError('Failed/skipped case')

def main():
    p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('--compiler')
    p.add_argument('--signer');p.add_argument('--work-root')
    p.add_argument('--only',choices=('all','consumer','harmony'),default='all')
    a=p.parse_args();inc=Path(a.package)/'include'
    if not (inc/'utest.h').is_file():raise RuntimeError('Installed utest.h missing')
    cc=a.compiler or shutil.which('clang') or shutil.which('gcc')
    if not cc:raise RuntimeError('No compiler')
    ohos=hasattr(os,'uname') and os.uname().sysname=='HarmonyOS'
    signer=a.signer or (shutil.which('binary-sign-tool') if ohos else None)
    if ohos and not signer:raise RuntimeError('OHOS native signer required')
    if a.only=='harmony' and not ohos:raise RuntimeError('Harmony test requires the real target')
    work_root=Path(a.work_root or os.environ.get('TMPDIR') or os.getcwd()).resolve()
    if not work_root.is_dir():raise RuntimeError('Existing task work directory required')
    with tempfile.TemporaryDirectory(prefix='utest-consumer-',dir=str(work_root)) as directory:
        child_env=dict(os.environ,TMPDIR=directory,TMPPREFIX=str(Path(directory)/'tmp'))
        work=Path(directory);source=work/'consumer.c';source.write_text(SMOKE_C,encoding='utf-8')
        inputs=[]
        if a.only in ('all','consumer'):inputs.append(('consumer',source,2))
        if ohos and a.only in ('all','harmony'):inputs.append(('harmony',Path(__file__).parent/'harmony_tests/timer_backend.c',1))
        for label,src,n in inputs:
            output=work/label
            subprocess.run([cc,str(src),'-I'+str(inc),'-std=gnu11','-o',str(output)],
                           check=True,timeout=60,env=child_env)
            if signer:
                signed=work/(label+'.signed')
                subprocess.run([signer,'sign','-selfSign','1','-inFile',str(output),
                                '-outFile',str(signed)],check=True,timeout=30,env=child_env)
                signed.chmod(0o700);output=signed
            run=subprocess.run([str(output)],capture_output=True,text=True,timeout=15,check=True,env=child_env)
            check_counts(run.stdout,n);print(run.stdout)
            print(label.upper()+'_TEST_PASS=%d/%d PASS'%(n,n))
    return 0

if __name__=='__main__':sys.exit(main())
