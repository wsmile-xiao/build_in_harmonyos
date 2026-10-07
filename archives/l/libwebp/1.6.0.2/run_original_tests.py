"""Run original registered programs and count XML, never count registration as PASS."""
import hashlib,json,os,re,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path

def run(source,build):
    output=build/'original-test-evidence';output.mkdir()
    cmake=(source/'tests/fuzzer/CMakeLists.txt').read_text(encoding='utf-8')
    names=re.findall(r'^add_webp_fuzztest\((\w+)',cmake,re.M)
    # Includes four original conditional mux targets and one info target.
    names+=re.findall(r'^  add_webp_fuzztest\((\w+)',cmake,re.M)
    if len(names)!=12 or len(set(names))!=12:raise RuntimeError('Original target inventory drift')
    records=[]
    for name in names:
        matches=[p for p in build.rglob(name) if p.is_file() and not p.is_symlink()]
        if len(matches)!=1:raise RuntimeError('Missing/ambiguous original executable '+name)
        binary=matches[0];report=output/(name+'.xml')
        env=dict(os.environ,TEST_DATA_DIRS=str(source/'tests/fuzzer/data')+'/',GTEST_OUTPUT='xml:'+str(report))
        with (output/(name+'.stdout')).open('xb') as out,(output/(name+'.stderr')).open('xb') as err:
            proc=subprocess.run([str(binary)],env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=600)
        if proc.returncode:raise RuntimeError('Original program failed '+name+':'+str(proc.returncode))
        root=ET.parse(report).getroot();cases=root.findall('.//testcase')
        if not cases or any(x.find('failure') is not None or x.find('skipped') is not None or x.get('status')=='notrun' for x in cases):
            raise RuntimeError('Original program incomplete/failed/skipped '+name)
        if int(root.get('tests','0'))!=len(cases) or int(root.get('failures','0')) or int(root.get('disabled','0')):
            raise RuntimeError('Original XML denominator mismatch '+name)
        original=(source/'tests/fuzzer'/(name+'.cc')).read_text(encoding='utf-8')
        expected=set(re.findall(r'FUZZ_TEST\(\s*(\w+)\s*,\s*(\w+)\s*\)',original))
        actual={(x.get('classname'),x.get('name')) for x in cases}
        if not expected or not expected.issubset(actual):raise RuntimeError('Source case IDs missing '+name+':'+repr((expected,actual)))
        records.append({'name':name,'rc':proc.returncode,'source_case_ids':sorted(expected),'actual_case_ids':sorted(actual),'tests':len(cases),'xml_sha256':hashlib.sha256(report.read_bytes()).hexdigest()})
    antlr=build/'_deps/antlr_cpp-build';report=output/'antlr.xml'
    # Use the real tool bound by this configured CMake build, not a bare name
    # that OHOS posix_spawn can fail to resolve despite a valid shell PATH.
    entries=re.findall(r'^CMAKE_CTEST_COMMAND:INTERNAL=(.+)$',(build/'CMakeCache.txt').read_text(encoding='utf-8'),re.M)
    if len(entries)!=1:raise RuntimeError('Missing/ambiguous configured CTest command')
    ctest=Path(entries[0].strip())
    if not ctest.is_absolute() or not ctest.is_file() or not os.access(ctest,os.X_OK):raise RuntimeError('Configured real CTest is not executable')
    with (output/'antlr.stdout').open('xb') as out,(output/'antlr.stderr').open('xb') as err:
        proc=subprocess.run([str(ctest),'--test-dir',str(antlr),'--output-on-failure','-j1','--output-junit',str(report)],stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=1200)
    if proc.returncode:raise RuntimeError('Original ANTLR tests failed '+str(proc.returncode))
    root=ET.parse(report).getroot();cases=root.findall('.//testcase')
    if not cases or any(x.find('failure') is not None or x.find('skipped') is not None or x.get('status')=='notrun' for x in cases):raise RuntimeError('Original ANTLR missing/failed/skipped')
    total=sum(r['tests'] for r in records)+len(cases)
    value={'original_libwebp':records,'original_antlr_count':len(cases),'pass':total,'total':total,'skip':0,'fail':0,'scope':'COMPLETE_ENABLED_ORIGINAL_UPSTREAM_TESTS_NOT_CI'}
    with (output/'result.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
    print('UPSTREAM_COUNT='+str(total));print('UPSTREAM '+str(total)+'/'+str(total)+' PASS')

if __name__=='__main__':run(Path(sys.argv[1]),Path(sys.argv[2]))
