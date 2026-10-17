"""Actual installed CLI and production parser; no input-device creation/capture."""
import hashlib,json,os,platform,stat,subprocess,sys,uuid
from pathlib import Path

def invoke(args, expected_rc, marker):
    result=subprocess.run(args,capture_output=True,timeout=15,check=False)
    output=result.stdout+result.stderr
    if result.returncode!=expected_rc or marker not in output:
        raise RuntimeError('Real product execution failed: '+json.dumps({'argv':args,'rc':result.returncode,'stdout':result.stdout.decode('utf-8','replace'),'stderr':result.stderr.decode('utf-8','replace')}))
    return result

def config_case(probe,parent,harmony):
    parent=Path(parent).resolve(strict=True)
    if harmony:
        if platform.system()!='HarmonyOS' or platform.machine()!='aarch64':
            raise RuntimeError('Not native HarmonyOS/aarch64')
        if not parent.is_relative_to(Path('/storage/Users/currentUser')):
            raise RuntimeError('Not the declared private HMDFS domain')
    root=parent/('配置 空格-'+uuid.uuid4().hex if harmony else 'interception-config-'+uuid.uuid4().hex)
    root.mkdir(mode=0o775)
    source=root/'设备 配置.yaml'; name='鸿蒙 中文设备配置' if harmony else 'ordinary-parser-consumer'
    content=('NAME: "'+name+'"\nID: private-config-proof\nVENDOR: 22136\nPRODUCT: 4660\nBUSTYPE: BUS_USB\nVERSION: 69\nEVENTS:\n  EV_KEY: [KEY_A, KEY_ESC]\n  EV_REL: [REL_X, REL_Y]\n  EV_ABS:\n    ABS_X: {VALUE: 11, MIN: 0, MAX: 65535, RES: 15}\n').encode('utf-8')
    try:
        with source.open('xb') as f:f.write(content)
        original=hashlib.sha256(content).hexdigest()
        st=source.lstat(); owner=root.lstat().st_uid
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=owner:
            raise RuntimeError('File ownership differs from actual parent projection')
        invoke([str(probe),str(source),name],0,b'CONFIG_PARSER_PASS=1/1')
        if hashlib.sha256(source.read_bytes()).hexdigest()!=original:
            raise RuntimeError('Product/test changed its input')
        details={'platform':platform.uname()._asdict(),'source_sha256':original,'source_bytes':len(content),'process_uid':os.getuid(),'parent_uid':owner,'source_uid':st.st_uid,'actual_production_source':'uinput.cpp, immutable official packaged bytes','input_device_side_effects':False}
    finally:
        if source.exists():source.unlink()
        root.rmdir()
    if root.exists():raise RuntimeError('Private scenario root not cleaned')
    print('INTERCEPTION_TEST_DETAIL='+json.dumps(details,ensure_ascii=True),flush=True)

def main():
    mode,probe,package,parent=sys.argv[1:]
    probe=Path(probe).resolve(strict=True); package=Path(package).resolve(strict=True)
    if mode=='consumer':
        for tool in ('udevmon','intercept','uinput'):
            binary=(package/'bin'/tool).resolve(strict=True)
            if not binary.is_relative_to(package):raise RuntimeError('Foreign product executable')
            invoke([str(binary),'-h'],0,b'usage:')
            invoke([str(binary),'--definitely-invalid-option'],1,b'usage:')
        config_case(probe,parent,False)
        print('CONSUMER_TEST_PASS=7/7',flush=True)
    elif mode=='harmony':
        config_case(probe,parent,True)
        print('HARMONY_TEST_PASS=1/1',flush=True)
    else:raise RuntimeError('Unknown exact scenario')
if __name__=='__main__':main()
