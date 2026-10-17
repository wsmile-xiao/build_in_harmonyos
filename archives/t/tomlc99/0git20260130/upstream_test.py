"""All original tomlc99 test entries with pinned official data, no Go/jq dependency.

The toml-test project permits a data-based runner. JSON comparison implements
its tagged-value contract, with the v1.6 datetime want/want typo corrected.
Timeout, signal, missing golden file and valid decoder nonzero are failures.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def datetime_value(kind, text):
    text=text.replace(' ', 'T').replace('t', 'T').replace('z', 'Z')
    match=re.search(r'\.(\d+)', text)
    ns=int((match.group(1)+'000000000')[:9]) if match else 0
    base=text[:match.start()]+text[match.end():] if match else text
    if kind=='datetime':
        val=datetime.datetime.fromisoformat(base.replace('Z','+00:00'))
        if val.tzinfo is None: raise ValueError('Missing datetime offset')
        return val.astimezone(datetime.timezone.utc),ns
    if kind=='datetime-local':
        val=datetime.datetime.fromisoformat(base)
        if val.tzinfo is not None: raise ValueError('Unexpected local datetime offset')
        return val,ns
    if kind=='date-local':return datetime.date.fromisoformat(base),ns
    if kind=='time-local':
        val=datetime.time.fromisoformat(base)
        if val.tzinfo is not None: raise ValueError('Unexpected local time offset')
        return val,ns
    raise ValueError('Unsupported datetime type')


def compare(want, have, location='$', tagged=True):
    # toml-spec-tests uses the original tagged array and local date type names;
    # toml-test uses unwrapped arrays and explicitly named local subtypes.
    if isinstance(want,dict) and set(want)=={'type','value'}:
        if want['type']=='array':want=want['value']
        elif want['type'] in ('date','time','datetime-local'):
            want=dict(want,type={'date':'date-local','time':'time-local','datetime-local':'datetime-local'}[want['type']])
        elif want['type']=='datetime' and re.search(r'(Z|[+-]\d\d:\d\d)$',want['value'],re.I) is None:
            # Legacy spec-tests called both offset and local values datetime.
            want=dict(want,type='datetime-local')
    if isinstance(want,dict):
        if not isinstance(have,dict) or set(want)!=set(have):raise ValueError('Object keys/type mismatch '+location)
        if tagged and set(want)=={'type','value'} and isinstance(want['type'],str):
            if want['type']!=have['type']:raise ValueError('Tagged type mismatch '+location)
            typ=want['type'];w,h=want['value'],have['value']
            if not isinstance(w,str) or not isinstance(h,str):raise ValueError('Atomic value not string '+location)
            if typ=='float':
                wf,hf=float(w),float(h)
                if not ((math.isnan(wf) and math.isnan(hf)) or wf==hf):raise ValueError('Float mismatch '+location)
            elif typ in ('datetime','datetime-local','date-local','time-local'):
                if datetime_value(typ,w)!=datetime_value(typ,h):raise ValueError('Datetime mismatch '+location)
            elif (w.lower() if typ=='bool' else w)!=(h.lower() if typ=='bool' else h):
                raise ValueError('Value mismatch '+location)
            return
        for k in want:compare(want[k],have[k],location+'.'+k,tagged)
    elif isinstance(want,list):
        if not isinstance(have,list) or len(want)!=len(have):raise ValueError('Array mismatch '+location)
        for i,(w,h) in enumerate(zip(want,have)):compare(w,h,location+'['+str(i)+']',tagged)
    elif type(want)!=type(have) or want!=have:raise ValueError('Scalar mismatch '+location)


def inventory(source, fixtures):
    rows=[{'id':'unittest/t1','kind':'unit'}]
    for p in sorted((source/'stdex').glob('*.toml')):
        golden=Path(str(p)+'.res')
        if not golden.is_file():raise RuntimeError('Missing stdex golden: '+str(p))
        row={'id':'stdex/'+p.name,'kind':'stdex','input':str(p),'expected':str(golden)}
        if p.name=='string8.toml':
            # The original golden records a parser bug: apostrophes are legal
            # inside a double-quoted basic string. Keep the original bytes and
            # hash, but explicitly verify the entire corrected output.
            row.update(spec_override='TOML 1.0 permits apostrophes inside basic strings',
                expected_output="{\n  apos15 = \"Here are fifteen apostrophes: '''''''''''''''\",\n}\n")
        rows.append(row)
    suite=fixtures/'toml-test/tests'
    paths=(suite/'files-toml-1.0.0').read_text(encoding='utf-8').splitlines()
    tomls=[p for p in paths if p.endswith('.toml')]
    if not tomls or len(tomls)!=len(set(tomls)):raise RuntimeError('Invalid official version list')
    for rel in tomls:
        p=suite/rel
        if not p.is_file():raise RuntimeError('Missing official test input '+rel)
        invalid=rel.startswith('invalid/')
        row={'id':'test1/'+rel,'kind':'invalid' if invalid else 'valid','input':str(p),'tagged':True}
        if not invalid:row['expected']=str(p.with_suffix('.json'))
        rows.append(row)
    suite=fixtures/'toml-spec-tests'
    for kind,sub in [('valid','values'),('invalid','errors')]:
        for p in sorted((suite/sub).glob('*.toml')):
            row={'id':'test2/'+sub+'/'+p.name,'kind':kind,'input':str(p),'tagged':False}
            if kind=='valid':row['expected']=str(p.with_suffix('.json'))
            if sub=='errors' and p.name=='array-7.toml':
                # This preserved TOML 0.x fixture became valid in TOML 1.0.
                # Execute it and compare both typed values; do not skip it or
                # force the product to reject valid mixed arrays.
                row.update(kind='valid',original_kind='invalid',
                    spec_override='TOML 1.0 permits mixed-type arrays',
                    expected_value={'arr6':[{'type':'integer','value':'1'},
                                            {'type':'float','value':'2.0'}]})
            rows.append(row)
    for r in rows:
        for k in ('input','expected'):
            if k in r:
                p=Path(r[k]);assert p.is_file(),str(p)
                r[k+'_sha256']=digest(p)
    assert len(rows)==len({r['id'] for r in rows})
    return rows


def run(source, fixtures, out, compiler=None, signer=None, binaries=None):
    sys.setrecursionlimit(12000)
    source=Path(source).resolve();fixtures=Path(fixtures).resolve();out=Path(out).resolve()
    out.mkdir(parents=True,exist_ok=False)
    rows=inventory(source,fixtures)
    (out/'inventory.json').write_text(json.dumps({'tests':rows},indent=2),encoding='utf-8')
    print('INVENTORY_COUNT='+str(len(rows)),flush=True)
    tools={}
    for name,rel in [('t1','unittest/t1.c'),('toml_cat','toml_cat.c'),('toml_json','toml_json.c')]:
        if binaries:
            tools[name]=str(Path(binaries)/name)
        else:
            exe=out/(name+'.unsigned' if signer else name)
            command=[compiler,'-std=c99','-O1','-UNDEBUG','-I'+str(source),str(source/rel),str(source/'toml.c'),'-o',str(exe)]
            p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
            (out/(name+'.build.stdout')).write_bytes(p.stdout);(out/(name+'.build.stderr')).write_bytes(p.stderr)
            if p.returncode:raise RuntimeError('Upstream executable build failure: '+name)
            if signer:
                signed=out/name
                p=subprocess.run([signer,'sign','-selfSign','1','-inFile',str(exe),'-outFile',str(signed)],capture_output=True,timeout=30)
                (out/(name+'.sign.stdout')).write_bytes(p.stdout);(out/(name+'.sign.stderr')).write_bytes(p.stderr)
                if p.returncode:raise RuntimeError('Native signing failure: '+name)
                os.chmod(signed,0o700);exe=signed
            tools[name]=str(exe)
    results=[]
    for index,row in enumerate(rows):
        case=out/('case-%04d'%index);case.mkdir();error=None
        try:
            data=Path(row['input']).read_bytes() if 'input' in row else None
            command=[tools['t1']] if row['kind']=='unit' else [tools['toml_cat'] if row['kind']=='stdex' else tools['toml_json']]
            # The original stdex tool reads argv files; the JSON decoder reads stdin.
            if row['kind']=='stdex':command.append(row['input']);data=None
            p=subprocess.run(command,input=data,capture_output=True,timeout=10)
            (case/'stdout').write_bytes(p.stdout);(case/'stderr').write_bytes(p.stderr)
            if row['kind']=='stdex':
                golden=(row['expected_output'].encode('utf-8') if 'expected_output' in row
                        else Path(row['expected']).read_bytes())
                # toml_cat returns zero after parse diagnostics; only its
                # value-decoding failure exits one. Also require exact golden.
                expected_rc=1 if b'ERROR: unable to decode value' in golden else 0
                # C libraries may print a sign for NaN; TOML NaN has no signed
                # mathematical value. Preserve every other byte of the golden.
                normalize=lambda b:re.sub(rb'( = )[+-]nan(,)',rb'\1nan\2',b)
                if p.returncode!=expected_rc or normalize(p.stdout+p.stderr)!=normalize(golden):
                    raise ValueError('stdex expected RC/output mismatch: rc='+str(p.returncode))
            elif row['kind']=='invalid':
                if p.returncode!=1 or not p.stderr:raise ValueError('Invalid input not normally rejected: rc='+str(p.returncode))
            else:
                if p.returncode!=0:raise ValueError('Valid input failed: rc='+str(p.returncode))
                if row['kind']=='valid':
                    expected=row.get('expected_value')
                    if expected is None:expected=json.loads(Path(row['expected']).read_text(encoding='utf-8'))
                    compare(expected,json.loads(p.stdout))
            result={'id':row['id'],'status':'PASS','rc':p.returncode}
        except (ValueError,RuntimeError,subprocess.TimeoutExpired,RecursionError) as exc:
            error=str(exc);result={'id':row['id'],'status':'FAIL','error':error}
            if isinstance(exc,subprocess.TimeoutExpired):
                (case/'stdout').write_bytes(exc.stdout or b'');(case/'stderr').write_bytes(exc.stderr or b'')
        results.append(result);print(result['status']+' '+row['id']+(' '+error if error else ''),flush=True)
    (out/'results.json').write_text(json.dumps({'tests':results},indent=2),encoding='utf-8')
    passed=sum(r['status']=='PASS' for r in results)
    print('UPSTREAM_TEST_'+('PASS' if passed==len(rows) else 'FAIL')+'=%d/%d %s'%(passed,len(rows),'PASS' if passed==len(rows) else 'FAIL'),flush=True)
    if passed!=len(rows):raise RuntimeError('Complete upstream suite failed')
    return len(rows)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('fixtures');p.add_argument('out')
    p.add_argument('--compiler');p.add_argument('--signer');p.add_argument('--binaries')
    a=p.parse_args();run(a.source,a.fixtures,a.out,a.compiler,a.signer,a.binaries)
