#!/usr/bin/env python3
"""alloy 1.17.1 consumer smoke test (R34).

On hosts that block the bpf syscall (seccomp -> SIGSYS at alloy startup,
e.g. the OHOS build worker), the binary cannot execute at all; the script
then verifies the package layout (binary present, ELF) and reports the
environment limitation explicitly. On capable hosts (bpf allowed) the
runtime assertions below run in full.
"""

import os
import subprocess
import sys
import tempfile

exe = sys.argv[1]
passed = True

# Clean failure when the packaged binary is missing (avoid a traceback
# from subprocess.run / open() on a non-existent path).
if not os.path.isfile(exe):
    print(f"FAIL: alloy executable not found: {exe}")
    sys.exit(1)


def layout_checks():
    ok = os.path.isfile(exe)
    print(("PASS" if ok else "FAIL") + f": binary exists ({exe})")
    if not ok:
        return False
    with open(exe, "rb") as f:
        elf_ok = f.read(4) == b"\x7fELF"
    print(("PASS" if elf_ok else "FAIL") + ": binary is ELF")
    return ok and elf_ok


def run(args, timeout=90):
    return subprocess.run([exe] + args, capture_output=True, text=True,
                          timeout=timeout)


# Probe: does the binary execute on this host?
probe = run(["--version"])
probe_out = (probe.stdout + probe.stderr)
# Go's runtime catches SIGSYS (seccomp on the bpf syscall), prints
# "SIGSYS: bad system call" and exits non-zero; the exit code is the
# runtime's fatal code, not the signal, so match on the message too.
bpf_blocked = probe.returncode != 0 and (
    "SIGSYS: bad system call" in probe_out
    or "bad system call" in probe_out
    or probe.returncode == -31
    or probe.returncode == 159
)
if bpf_blocked:
    print("SKIP: binary blocked by host seccomp (SIGSYS on bpf syscall at "
          "startup, cilium/ebpf memcg detection); runtime assertions "
          "require a bpf-capable target/CI. Verifying package layout only.")
    if not layout_checks():
        sys.exit(1)  # layout broken -> real failure
    # Explicit SKIP semantics (autoconf-style exit 77): the environment
    # blocks execution, so this is NOT a pass — the consumer runtime
    # assertions must be exercised on a bpf-capable host.
    sys.exit(77)
if probe.returncode != 0:
    # Unexpected failure (not the known environment limitation) -> fail
    print(probe_out[-500:])
    sys.exit(1)

# Test 1: --version 输出含 v1.17.1
r = run(["--version"])
ok = r.returncode == 0 and "1.17.1" in (r.stdout + r.stderr)
passed &= ok
print(("PASS" if ok else "FAIL") +
      f": alloy --version -> {(r.stdout + r.stderr).strip()[:60]}")

# Test 2: -version 等价（cobra 版本旗标）
r = run(["-version"])
ok = r.returncode == 0 and "1.17.1" in (r.stdout + r.stderr)
passed &= ok
print(("PASS" if ok else "FAIL") + ": alloy -version -> version string")

# Test 3: alloy fmt 解析最小配置（Alloy 配置语言解析器）
cfg = 'logging {\n\tlevel = "info"\n}\n'
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "config.alloy")
    with open(p, "w") as f:
        f.write(cfg)
    r = run(["fmt", p])
    ok = r.returncode == 0
    passed &= ok
    print(("PASS" if ok else "FAIL") +
          f": alloy fmt minimal config rc={r.returncode}")

print("RESULT:", "ALL PASS" if passed else "FAILED")
sys.exit(0 if passed else 1)
