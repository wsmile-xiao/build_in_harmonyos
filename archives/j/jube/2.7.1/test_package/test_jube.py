#!/usr/bin/env python3
"""Consumer test for jube/2.7.1 — real API + CLI checks against the installed
conan package.

Performs genuine checks (no mocks / no stubs) with the packaged jube:
  1. import jube
  2. jube.conf.JUBE_VERSION == "2.7.1"
  3. `jube --version` exits 0
  4. `jube --version` output contains the version
  5. minimal XML benchmark (packaged hello_world example) runs end-to-end and
     produces a completed-workpackage `done` file (and no `error` file)
Emits HMBS_TEST_PACKAGE_RESULT after the checks with discovered/passedCount.
"""
import os
import sys
import json
import shutil
import tempfile
import subprocess


def main(pkg, site_packages, bin_dir):
    # Ensure the package under test wins over any system/pip-global jube.
    sys.path.insert(0, site_packages)
    env = dict(os.environ)
    env["PYTHONPATH"] = site_packages + os.pathsep + env.get("PYTHONPATH", "")
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")

    results = []

    def check(name, cond, detail=""):
        results.append((name, bool(cond), detail))

    # 1. import
    try:
        import jube  # noqa: F401
        check("import jube", True)
    except Exception as e:  # noqa: BLE001
        check("import jube", False, repr(e))

    # 2. version constant
    try:
        import jube.conf
        v = getattr(jube.conf, "JUBE_VERSION", None)
        check("JUBE_VERSION == 2.7.1", v == "2.7.1", "got=%r" % (v,))
    except Exception as e:  # noqa: BLE001
        check("JUBE_VERSION == 2.7.1", False, repr(e))

    # 3. CLI --version, rc
    try:
        r = subprocess.run([os.path.join(bin_dir, "jube"), "--version"],
                           capture_output=True, text=True, timeout=90,
                           env=env)
        check("jube --version rc==0", r.returncode == 0,
              "rc=%s" % r.returncode)
        check("jube --version contains 2.7.1",
              "2.7.1" in (r.stdout + r.stderr),
              "out=%r err=%r" % (r.stdout, r.stderr))
    except Exception as e:  # noqa: BLE001
        check("jube --version", False, repr(e))

    # 4. minimal XML benchmark end-to-end (packaged hello_world example)
    try:
        examples = os.path.join(pkg, "share", "jube", "examples")
        xml = os.path.join(examples, "hello_world", "hello_world.xml")
        if not os.path.isfile(xml):
            check("hello_world example found", False, "missing " + xml)
        else:
            work = tempfile.mkdtemp(prefix="jube_consumer_")
            try:
                # By default JUBE resolves the XML's relative `outpath`
                # (hello_world.xml uses outpath="bench_run") against the *XML
                # file's directory* (jube/jubeio.py: outpath =
                # normpath(join(file_path_ref, outpath))), i.e. into the
                # packaged examples dir, NOT cwd. Pass an explicit `--outpath`
                # that is relative to the execution location (cwd=work below)
                # so the benchmark output lands deterministically under the
                # temp workspace and we can verify the produced `done`/`error`
                # files there.
                out_rel = "jube_out"
                rr = subprocess.run(
                    [os.path.join(bin_dir, "jube"), "run",
                     "--outpath", out_rel, "--hide-animation", xml],
                    cwd=work, capture_output=True, text=True, timeout=300,
                    env=env)
                rc_ok = rr.returncode == 0
                check("hello_world jube run rc==0", rc_ok,
                      "rc=%s\n%s" % (rr.returncode, rr.stdout + rr.stderr))
                done_found = False
                error_found = False
                for root, _dirs, files in os.walk(work):
                    if "done" in files:
                        done_found = True
                    if "error" in files:
                        error_found = True
                check("hello_world produced done file", done_found)
                check("hello_world no error file", not error_found)
            finally:
                shutil.rmtree(work, ignore_errors=True)
    except Exception as e:  # noqa: BLE001
        check("hello_world end-to-end", False, repr(e))

    passed = sum(1 for _, c, _ in results if c)
    total = len(results)
    marker = {
        "executed": True,
        "passed": passed == total,
        "command": "python3 test_jube.py <pkg> <site-packages> <bin>",
        "discovered": total,
        "passedCount": passed,
    }
    print("JUBE_CONSUMER=%d/%d" % (passed, total), flush=True)
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False),
          flush=True)
    for name, c, detail in results:
        print(("PASS  " if c else "FAIL  ") + name + (" : " + detail if detail else ""))
    if passed != total:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
