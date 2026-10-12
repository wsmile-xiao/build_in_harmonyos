"""Real OHOS non-setuid product rejection, NOT authentication success."""
import hashlib,json,os,shutil,stat,subprocess
from pathlib import Path

def expected_rejection(rc,stdout,stderr,named):
    expected=b'doas: not installed setuid\n' if named else b'doas: no passwd entry for self\n'
    return rc==1 and stdout==b'' and stderr==expected

def safe_nonprivileged_mode(file_mode):
    # HMDFS may project advisory chmod bits. Require the security properties,
    # not optional group/other read permissions. Writable or privileged files
    # remain failures; a successful chmod or signed execution is not enough.
    mode=stat.S_IMODE(file_mode)
    return (stat.S_ISREG(file_mode) and bool(mode & stat.S_IXUSR)
            and not bool(mode & (stat.S_ISUID | stat.S_ISGID | 0o022)))

def main():
    import pwd
    assert os.uname().sysname=='HarmonyOS','Not the actual Harmony runtime'
    uid,euid=os.getuid(),os.geteuid()
    assert uid==euid and uid!=0,'Requires actual nonprivileged deployment'
    binary=shutil.which('doas');assert binary,'Installed doas missing'
    exe=Path(binary).resolve(strict=True)
    metadata=exe.stat()
    observed_mode=format(stat.S_IMODE(metadata.st_mode),'04o')
    print(json.dumps(dict(case='ohos-installed-mode-readback',actual_binary=str(exe),mode=observed_mode,uid=uid,euid=euid,mode_security_properties_pass=safe_nonprivileged_mode(metadata.st_mode))),flush=True)
    assert safe_nonprivileged_mode(metadata.st_mode),'Unsafe installed package mode: '+observed_mode
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
    assert os.getuid()==uid and os.geteuid()==euid,'Calling process identity drift'
    print(json.dumps(dict(case='ohos-real-nonprivileged-execution-rejection',actual_os=os.uname().sysname,uid=uid,euid=euid,named_account=name,actual_binary=str(exe),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),mode=observed_mode,argv=args,rc=r.returncode,stdout=r.stdout.decode(errors='replace'),stderr=r.stderr.decode(errors='replace'),passed=ok,authentication_success_proven=False,privilege_transition_proven=False)))
    print('HARMONY_TEST_COUNT=1')
    print('HARMONY_TEST_PASS='+('1/1 PASS' if ok else '0/1 FAIL')+'; REAL_AUTH_PRIVILEGE_NOT_PROVEN')
    raise SystemExit(0 if ok else 1)

if __name__=='__main__':main()
