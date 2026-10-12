"""Run the complete configured native suite; separate harnesses/cases/assertions."""
import argparse, hashlib, json, os, re, shutil, socket, subprocess
from pathlib import Path

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--build',required=True);p.add_argument('--output',required=True);p.add_argument('--ctest',default='ctest')
    a=p.parse_args();source=Path(a.source).resolve();build=Path(a.build).resolve();output=Path(a.output).resolve()
    assert not output.exists();output.mkdir()
    env=dict(os.environ,CTEST_LOG='1')
    # Tests execute the freshly built shared library, not an installed provider.
    # OHOS does not reliably honor CMake's build RUNPATH on this layout.
    # Bind only this candidate's library directory for these child processes.
    native_library=build/'src/onion/libonion.so'
    if native_library.is_file():
        library_root=native_library.parent.resolve()
        assert library_root.is_relative_to(build)
        env['LD_LIBRARY_PATH']=str(library_root)+(os.pathsep+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    # The target Python posix_spawn path does not search PATH for bare names.
    # Resolve using the inherited Conan buildenv before launching, fail closed.
    ctest=shutil.which(a.ctest,path=env.get('PATH'))
    if ctest is None: raise FileNotFoundError('CTest not found in the active build environment: '+a.ctest)
    # Frozen discovery is not a PASS. It never substitutes for unfiltered runs.
    inventory=subprocess.run([ctest,'--test-dir',str(build),'--show-only=json-v1'],capture_output=True,check=True,timeout=30,env=env)
    (output/'ctest-inventory.json').write_bytes(inventory.stdout)
    tests=json.loads(inventory.stdout)['tests']
    expected={'internal-hash','internal-request','internal-response','internal-handler','internal-server','internal-codecs','internal-post','internal-block','internal-mime','internal-sessions','internal-cloexec','internal-otemplates','internal-websockets','internal-post-no-type','internal-url','internal-permissions','listen_stop','random','version'}
    assert {t['name'] for t in tests}==expected,'Configured suite registration mismatch'
    all_cases=[];records=[];assertions=0
    def invoke(command,label,cwd,environment=env):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=str(sock.getsockname()[1])
        actual_env=dict(environment,ONION_TEST_PORT=port,ONION_BIG_FILE=str(source/'AGPL.txt'))
        executable=shutil.which(command[0],path=actual_env.get('PATH'))
        if executable is None: raise FileNotFoundError('Upstream command not found: '+command[0])
        command=[executable,*command[1:]]
        out=output/(label+'.stdout');err=output/(label+'.stderr')
        try:
            r=subprocess.run(command,cwd=cwd,env=actual_env,capture_output=True,timeout=60)
        except subprocess.TimeoutExpired as exc:
            out.write_bytes(exc.stdout or b'');err.write_bytes(exc.stderr or b'')
            (output/(label+'.timeout.json')).write_text(json.dumps({'command':command,'cwd':str(cwd),'rc':None,'timed_out':True,'timeout_seconds':60,'stdout_sha256':digest(out),'stderr_sha256':digest(err)})+'\n',encoding='utf-8')
            raise
        out.write_bytes(r.stdout);err.write_bytes(r.stderr)
        rec={'command':command,'cwd':str(cwd),'rc':r.returncode,'stdout_sha256':digest(out),'stderr_sha256':digest(err),'port':port}
        records.append(rec)
        assert r.returncode==0,f'Upstream failed: {label}; RC={r.returncode}'
        return r.stdout.decode('utf-8',errors='replace')+'\n'+r.stderr.decode('utf-8',errors='replace')
    for t in tests:
        command=t['command'];binary=Path(command[0]).resolve()
        assert binary.is_relative_to(build) and binary.is_file()
        cwd=binary.parent
        discovered=invoke(command+['--list'],t['name']+'-discovery',cwd)
        names=re.findall(r'INFO \* (\w+)',discovered)
        # Upstream INFO emits a space before '*'. Avoid depending on source line numbers.
        if not names: names=re.findall(r'INFO\s+\*\s+(\w+)',discovered)
        assert names and len(names)==len(set(names)),t['name']+': invalid runtime discovery'
        text=invoke(command,t['name']+'-execution',cwd)
        started=re.findall(r'INFO Test (\w+)',text)
        ends=re.findall(r'INFO (\w+) ends: (\d+) succeses / (\d+) failures',text)
        assert sorted(started)==sorted(names) and sorted(x[0] for x in ends)==sorted(names),'Runtime case identity drift: '+t['name']
        assert all(int(x[2])==0 for x in ends)
        totals=re.findall(r'INFO TOTAL: (\d+) succeses / (\d+) failures',text)
        assert len(totals)==1 and int(totals[0][1])==0 and int(totals[0][0])>0
        assertions+=int(totals[0][0]);all_cases.extend(t['name']+'/'+x for x in names)
    prerecorded=build/'tests/04-prerecorded/prerecorded'
    # Both original fixtures in both newline modes, as documented upstream.
    for fixture in sorted((source/'tests/04-prerecorded').glob('*.tst')):
        for crlf in [False,True]:
            cmd=[str(prerecorded)]+(['-r'] if crlf else [])+[str(fixture)]
            name=fixture.stem+('-crlf' if crlf else '-lf')
            text=invoke(cmd,'prerecorded-'+name,prerecorded.parent)
            totals=re.findall(r'INFO TOTAL: (\d+) succeses / (\d+) failures',text)
            assert len(totals)==1 and int(totals[0][0])>0 and int(totals[0][1])==0,'Fixture did not execute'
            assertions+=int(totals[0][0]);all_cases.append('prerecorded/'+name)
    tools=build/'tests/07-tools'
    assets_env=dict(env,OPACK=str(build/'tools/opack/opack'),OTEMPLATE=str(build/'tools/otemplate/otemplate'),ORIG_DIR=str(source/'tests/07-tools'),DEST_DIR=str(tools))
    text=invoke(['sh',str(source/'tests/07-tools/test-assets.sh')],'tools-assets',tools,assets_env)
    assert re.search(r'^OK$',text,re.MULTILINE)
    all_cases.append('tools/assets')
    assert len(all_cases)==len(set(all_cases))
    result={'status':'PASS','total':len(all_cases),'passed':len(all_cases),'failed':0,'skipped':0,'registered_harnesses':len(tests),'fixture_modes':4,'tool_scenarios':1,'assertions':assertions,'cases':all_cases,'records':records,'excluded_feature_contract':{'ssl':False,'sqlite3':False,'xml2':False,'cpp_bindings':False,'examples':False},'interactive_demo_targets':['tests/03-methods/01-methods','tests/05-sessions/sessions','tests/07-tools/01-otemplate'],'interactive_demo_note':'Unregistered indefinite demonstration servers, not unattended assertion suites; native compilation required.'}
    (output/'inventory.txt').write_text('UPSTREAM_TEST_COUNT='+str(len(all_cases))+'\n'+'\n'.join(all_cases)+'\n',encoding='utf-8')
    (output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'UPSTREAM_TEST_PASS={len(all_cases)}/{len(all_cases)}; REGISTERED_HARNESSES={len(tests)}; ASSERTIONS={assertions}; NO_SKIPS')
if __name__=='__main__':main()
