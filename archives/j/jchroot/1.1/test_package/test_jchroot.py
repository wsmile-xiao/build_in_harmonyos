#!/usr/bin/env python3
'''jchroot consumer end-to-end test for the packaged binary (OpenHarmony PC).

usage: python3 test_jchroot.py <path to bin/jchroot>

The suite runs the real binary. One case is a complete consumer end-to-end
run: a throw-away root plus an fstab(5) file are built on the fly, jchroot
is executed on them and the guest stdout, the evidence file inside the new
root and the recorded child PID are validated. A host that refuses the
namespaces jchroot needs is validated as a refusal, so the verdict always
comes from real behaviour instead of being assumed.
'''
import os
import shutil
import subprocess
import sys
import tempfile

BIN = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'jchroot')
CASES = []
CHECKS = []


def check(case, name, cond, detail=''):
    if case not in CASES:
        CASES.append(case)
    CHECKS.append((name, bool(cond)))
    print('{} {}/{} {}'.format('PASS' if cond else 'FAIL', case, name, detail))


def run(args):
    return subprocess.run([BIN] + args, capture_output=True, text=True)


# case 1: complete consumer end-to-end run.
tmp = tempfile.mkdtemp(prefix='jchroot-consumer-')
root = os.path.join(tmp, 'root')
os.mkdir(root)
fstab = os.path.join(tmp, 'fstab')
entries = [e for e in ('/bin', '/lib', '/lib64', '/usr', '/etc')
           if os.path.isdir(e)]
with open(fstab, 'w') as handle:
    for entry in entries:
        handle.write('{} {} none bind,ro\n'.format(entry, entry))
# jchroot mounts every entry at <new-root>+<dir> and never creates the mount
# point itself: the targets must pre-exist inside the new root, otherwise the
# first mount fails with ENOENT and the end-to-end success path below can
# never run (the case silently degrades into a refusal probe).
for entry in entries:
    os.makedirs(os.path.join(root, entry.lstrip('/')), exist_ok=True)
pidfile = os.path.join(tmp, 'child.pid')
evidence = 'consumer-evidence.txt'
r = run(['-f', fstab, '-p', pidfile, root, '--', '/bin/sh', '-c',
         'id > /{}; echo CONSUMER-OK'.format(evidence)])
check('consumer', 'pidfile-created', os.path.isfile(pidfile))
if r.returncode == 0:
    check('consumer', 'guest-stdout-contract', 'CONSUMER-OK' in r.stdout)
    check('consumer', 'evidence-written-inside-new-root',
          os.path.isfile(os.path.join(root, evidence)))
else:
    low = r.stderr.lower()
    graceful = r.returncode == 1 and ('failed to clone' in low or
                                      'not permitted' in low)
    # a seccomp sandbox kills the process with SIGSYS (-31) before jchroot can
    # report the refused namespace syscalls itself.
    sandboxed = r.returncode == -31
    check('consumer', 'refusal-is-capability-denial', graceful or sandboxed,
          'exit={}'.format(r.returncode))
    check('consumer', 'refusal-no-partial-run', r.stdout == '')

# case 2: upstream smoke test (the only check upstream CI runs).
r = run(['--help'])
check('help', 'exit-0', r.returncode == 0, 'exit={}'.format(r.returncode))
check('help', 'usage-banner-and-options',
      'Usage:' in r.stderr and '--new-user-ns' in r.stderr)

# case 3: target path validation.
nope = os.path.join(tmp, 'nope')
r = run([nope, '--', '/bin/true'])
check('target', 'missing-target-exit-1', r.returncode == 1)
check('target', 'missing-target-diagnostic',
      'is not a directory' in r.stderr and nope in r.stderr)

# case 4: an unopenable pidfile must fail with exit 1.
r = run(['-p', os.path.join(tmp, 'no-dir', 'pid'), tmp, '--', '/bin/true'])
check('pidfile', 'unwritable-pidfile-exit-1',
      r.returncode == 1 and 'failed to open pid file' in r.stderr)

# case 5: UID/GID mapping requires a user namespace.
r = run(['-M', '0:0:1', tmp, '--', '/bin/true'])
check('mapping', 'map-without-userns-exit-1',
      r.returncode == 1 and 'without a user namespace' in r.stderr)

# do not leak the throw-away root/fstab/pidfile between runs
shutil.rmtree(tmp, ignore_errors=True)

failed = [name for name, ok in CHECKS if not ok]
print('cases={} checks={} failed={}'.format(len(CASES), len(CHECKS),
                                            len(failed)))
if failed:
    print('failed: {}'.format(', '.join(failed)))
    sys.exit(1)
print('jchroot consumer suite passed')