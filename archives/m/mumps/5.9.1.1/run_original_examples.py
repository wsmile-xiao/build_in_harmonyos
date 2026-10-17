"""Execute the original eleven IDs, checking numbers as well as return codes."""
import json,math,os,re,subprocess
from pathlib import Path
from native_driver import C,sign
ROOT=Path(__file__).resolve().parent
cases=[p+'simpletest'+suffix for p in ('s','d','c','z') for suffix in ('','_save_restore')]+['c_example','c_example_save_restore','multiple_arithmetics_example']
assert len(cases)==11
temporary=ROOT/'original-test-temporary';temporary.mkdir()
env=dict(os.environ,HYDRA_LAUNCHER='fork',HYDRA_BINDING='none',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    MUMPS_OOC_TMPDIR=str(temporary),MUMPS_SAVE_DIR=str(temporary),TMPDIR=str(temporary))
env['LD_LIBRARY_PATH']=os.pathsep.join([str(ROOT/'lib'),C['mpi']+'/lib',C['blas']+'/lib',C['scalapack']+'/lib',C['flang']+'/lib',C['llvm_lib']])
number=r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?'
for case in cases:
    binary=ROOT/'examples'/case;sign(binary)
    data=None
    if 'simpletest' in case:data=(ROOT/'examples'/('input_simpletest_cmplx' if case[0] in 'cz' else 'input_simpletest_real')).read_bytes()
    p=subprocess.run([C['mpi']+'/bin/mpiexec','-n','2' if 'simpletest' in case else '3',str(binary)],
        input=data,cwd=ROOT/'examples',env=env,capture_output=True,timeout=180)
    print(p.stdout.decode(),end='',flush=True);print(p.stderr.decode(),end='',flush=True)
    assert p.returncode==0,(case,p.returncode)
    output=p.stdout.decode();assert 'ERROR RETURN' not in output,case
    if case=='multiple_arithmetics_example':assert 'Creation of all instances went well' in output
    else:
        assert 'Solution is' in output,case
        tail=output.rsplit('Solution is',1)[1]
        if case.startswith(('csimple','zsimple')):
            pairs=re.findall(r'\(\s*('+number+r')\s*,\s*('+number+r')\s*\)',tail)
            assert len(pairs)>=5;values=[complex(float(a.replace('D','E')),float(b.replace('D','E'))) for a,b in pairs[:5]]
        else:
            size=2 if case.startswith('c_example') else 5;tokens=re.findall(number,tail)
            assert len(tokens)>=size;values=[complex(float(t.replace('D','E')),0) for t in tokens[:size]]
        tolerance=2e-5 if case.startswith(('ssimple','csimple')) else 2e-12
        assert all(math.isfinite(v.real) and math.isfinite(v.imag) and abs(v-(i+1))<tolerance for i,v in enumerate(values)),(case,values)
    print('UPSTREAM_CASE_PASS='+case,flush=True)
print('UPSTREAM_TEST_PASS=11/11',flush=True)
