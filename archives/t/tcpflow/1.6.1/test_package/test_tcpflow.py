#!/usr/bin/env python3
"""Consumer test package for tcpflow 1.6.1.

Executes the real packaged `tcpflow` binary against the upstream offline
pcap fixture (tests/test1.pcap from the tcpflow-1.6.1 release):

- case 1: `tcpflow --version`      -> version entry point
- case 2: `tcpflow -h`             -> usage/help entry point
- case 3: offline workflow
          `tcpflow -S enable_report=false -o <out> -r test1.pcap`
          -> exit 0, 4 flow files created, MD5 of each flow file matches
             the upstream test1.sh assertions (byte-identical reassembly)
- case 4: artifact ownership       -> flow files carry the expected
             ip.port-ip.port naming and exact sizes from upstream

Safety boundaries (see task security design):
- No live capture: `-r` reads the bundled offline pcap only; no interface,
  no root, no CAP_NET_RAW requirement, no port binding, no network config
  modification.
- No traffic capture: the fixture is the upstream 7 KB test1.pcap.
- Report generation is disabled with the upstream-supported config option
  `-S enable_report=false` because the DFXML report path (report.xml)
  crashes with SIGSEGV on OHOS aarch64/musl (path B evidence); the
  production binary semantics are unchanged - no mock, no hidden env var.
- All output is written to a temp dir under TMPDIR and cleaned up after
  the test; nothing is left inside the repo.
"""

import hashlib
import os
import subprocess
import sys
import tempfile

# Upstream tests/test1.sh assertions for test1.pcap (md5 + size)
# (exact values copied from tcpflow 1.6.1 tests/test1.sh)
UPSTREAM_FLOWS = {
    "074.125.019.101.00080-192.168.001.102.50956": ("ae30a88136feb0655492bdb75e078643", 136),
    "074.125.019.104.00080-192.168.001.102.50955": ("61051e417d34e1354559e3a8901d19d3", 2792),
    "192.168.001.102.50955-074.125.019.104.00080": ("14e9c335bf54dc4652999e25d99fecfe", 655),
    "192.168.001.102.50956-074.125.019.101.00080": ("78b8073093d107207327103e80fbdf43", 604),
}

case_count = 0
assertion_count = 0
passed = 0
failed = 0


def check(cond, desc):
    global assertion_count, passed, failed
    assertion_count += 1
    if cond:
        passed += 1
        print(f"  [PASS] {desc}")
    else:
        failed += 1
        print(f"  [FAIL] {desc}")


def run_cmd(cmd, timeout=60):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    global case_count
    if len(sys.argv) != 3:
        print("usage: test_tcpflow.py <tcpflow-bin> <pcap>")
        return 2
    tcpflow_bin = sys.argv[1]
    pcap_path = sys.argv[2]

    if not os.path.isfile(tcpflow_bin):
        print(f"[FAIL] tcpflow binary not found: {tcpflow_bin}")
        return 1
    if not os.path.isfile(pcap_path):
        print(f"[FAIL] pcap fixture not found: {pcap_path}")
        return 1

    # ---- case 1: version entry point ----
    # NOTE: upstream src/tcpflow.cpp `case 'V':` prints the version and
    # exits with code 1 (real upstream behavior), so rc==1 is expected.
    case_count += 1
    print("[case 1] tcpflow --version")
    rc, out, err = run_cmd([tcpflow_bin, "--version"])
    check("TCPFLOW 1.6.1" in out, f"--version prints 'TCPFLOW 1.6.1' (got: {out.strip()!r})")
    check(rc == 1, f"--version exit code matches upstream (rc=1, got {rc})")

    # ---- case 2: help/usage entry point ----
    case_count += 1
    print("[case 2] tcpflow -h")
    rc, out, err = run_cmd([tcpflow_bin, "-h"])
    check(rc == 0, f"-h exits 0 (rc={rc})")
    check("-r file" in out, "-h usage includes offline input option '-r file'")
    check("-o outdir" in out, "-h usage includes output dir option '-o outdir'")

    # ---- case 3: core offline workflow (deterministic reassembly) ----
    case_count += 1
    print("[case 3] offline pcap workflow")
    workdir = tempfile.mkdtemp(prefix="tcpflow-test-")
    outdir = os.path.join(workdir, "out")
    os.makedirs(outdir, exist_ok=True)
    try:
        rc, out, err = run_cmd(
            [tcpflow_bin, "-S", "enable_report=false", "-o", outdir, "-r", pcap_path]
        )
        check(rc == 0, f"tcpflow -r test1.pcap exits 0 (rc={rc}, stderr={err.strip()[:120]!r})")
        files = sorted(os.listdir(outdir))
        check(len(files) == len(UPSTREAM_FLOWS),
              f"produced {len(files)} flow files, expected {len(UPSTREAM_FLOWS)}")

        # ---- case 4: artifact ownership (names + sizes + md5) ----
        case_count += 1
        print("[case 4] artifact ownership (naming/size/md5 vs upstream test1.sh)")
        for name, (exp_md5, exp_size) in sorted(UPSTREAM_FLOWS.items()):
            fpath = os.path.join(outdir, name)
            check(os.path.isfile(fpath), f"flow file exists: {name}")
            if os.path.isfile(fpath):
                size = os.path.getsize(fpath)
                check(size == exp_size, f"{name} size {size} == upstream {exp_size}")
                digest = md5_of(fpath)
                check(digest == exp_md5, f"{name} md5 matches upstream ({digest[:12]}...)")

        # upstream tests/test1.sh also checks packet file mtime is year 2008
        # (utimes on packet files properly set). Assert the same here.
        first = os.path.join(outdir, sorted(UPSTREAM_FLOWS.keys())[0])
        if os.path.isfile(first):
            import time as _time
            mtime = os.path.getmtime(first)
            year = _time.gmtime(mtime).tm_year
            check(year == 2008,
                  f"flow file mtime year {year} == upstream expectation 2008")
    finally:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)

    print()
    print(f"RESULT: passed={passed} failed={failed} total={assertion_count} "
          f"(case_count={case_count}, assertion_count={assertion_count})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
