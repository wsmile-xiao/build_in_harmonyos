"""Real OHOS non-setuid product rejection, NOT authentication success."""
import hashlib,json,os,shutil,stat,subprocess
from pathlib import Path

def expected_rejection(rc,stdout,stderr,named):
    expected=b'doas: not installed setuid\n' if named else b'doas: no passwd entry for self\n'
    return rc==1 and stdout==b'' and stderr==expected

def main():
    import pwd
    assert os.uname().sysname=='HarmonyOS','Not the actual Harmony runtime'
    uid,euid=os.getuid(),os.geteuid()
    assert uid==euid and uid!=0,'Requires actual nonprivileged deployment'
    binary=shutil.which('doas');assert binary,'Installed doas missing'
    exe=Path(binary).resolve(strict=True)
    assert stat.S_IMODE(exe.stat().st_mode)==0o755,'Expected actual non-setuid package'
    try:
        name=pwd.getpwuid(uid).pw_name
    except KeyError:
        name=None
    # This absolute nonexistent command has no side effects even if the guard
    # regresses. No custom policy, password, shadow file or account is supplied.
    command=str(Path(os.environ.get('TMPDIR',os.getcwd())).resolve()/'doas-must-not-execute-security-check')
    assert not Path(command).exists()
    args=[str(exe),'-n',command]
    r=subprocess.run(args,stdin=subprocess.DEVNULL,capture_output=True,timeout=30)
    ok=expected_rejection(r.returncode,r.stdout,r.stderr,bool(name))
    print(json.dumps(dict(case='ohos-real-nonprivileged-execution-rejection',actual_os=os.uname().sysname,uid=uid,euid=euid,named_account=name,actual_binary=str(exe),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),mode='0755',argv=args,rc=r.returncode,stdout=r.stdout.decode(errors='replace'),stderr=r.stderr.decode(errors='replace'),passed=ok,authentication_success_proven=False,privilege_transition_proven=False)))
    print('HARMONY_TEST_COUNT=1')
    print('HARMONY_TEST_PASS='+('1/1 PASS' if ok else '0/1 FAIL')+'; REAL_AUTH_PRIVILEGE_NOT_PROVEN')
    raise SystemExit(0 if ok else 1)

if __name__=='__main__':main()
