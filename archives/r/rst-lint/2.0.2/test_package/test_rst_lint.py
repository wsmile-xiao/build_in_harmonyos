#!/usr/bin/env python3
"""rst-lint 2.0.2 consumer test — really drives the packaged product (R34).

Invoked by test_package/conanfile.py as::

    python3 test_rst_lint.py <bin/rst-lint>

Checks (any real failure aborts with a non-zero exit code):
  1. import the *installed* `restructuredtext_lint`; the CLI's version
     constant (`restructuredtext_lint.cli.VERSION`) == "2.0.2"
     (upstream has no package-level `__version__`)
  2. `lint()` parses reStructuredText through the packaged `docutils/0.23`
     (upstream fixture semantics: valid doc -> no errors; a title underline
     one character too short -> exactly one WARNING at line 2)
  3. `lint_file()` on an on-disk document
  4. `bin/rst-lint --version` prints 2.0.2 and exits 0
  5. `bin/rst-lint` on a clean file -> exit 0, no output
  6. `bin/rst-lint` on a broken file -> exit 2 with a WARNING line
  7. `bin/rst-lint` on a directory -> aggregates the *.rst files it finds
  8. [OHOS] platform case — the generated console script is a POSIX
     executable (mode +x) with a ``#!/usr/bin/env python3`` shebang, which
     is what works on OpenHarmony PC (python3 is provided on PATH by the
     OHOS runtime, not at /usr/bin/python3), and the tool operates on an
     OpenHarmony filesystem path under the OHOS-provided $TMPDIR (OHOS
     mounts /tmp read-only — SKILL §7 Gotcha E002).

Emits machine-readable markers consumed by the pipeline:
  HMBS_TEST_PACKAGE_RESULT=<json>
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

# Upstream fixture semantics (restructuredtext_lint/test/test_files/*.rst).
VALID_RST = "Hello\n=====\nWorld\n"      # title underline == title width
INVALID_RST = "Hello\n====\nWorld\n"     # underline one short -> 1 WARNING

CHECKS = []  # (name, ok, detail)


def record(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    return ok


def run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return proc.returncode, proc.stdout, proc.stderr


def main():
    cli = sys.argv[1] if len(sys.argv) > 1 else None

    # 1. installed module + version (upstream exposes it on cli, not the pkg)
    try:
        import restructuredtext_lint
        import restructuredtext_lint.cli as rst_cli
        record("import restructuredtext_lint + cli.VERSION",
               rst_cli.VERSION == "2.0.2"
               and hasattr(restructuredtext_lint, "lint")
               and hasattr(restructuredtext_lint, "lint_file"),
               "cli.VERSION={0!r}".format(rst_cli.VERSION))
    except Exception as exc:  # pragma: no cover - diagnostic path
        record("import restructuredtext_lint + cli.VERSION", False, repr(exc))

    # 2. lint() through the packaged docutils dependency
    try:
        clean = restructuredtext_lint.lint(VALID_RST, "clean.rst")
        broken = restructuredtext_lint.lint(INVALID_RST, "broken.rst")
        broken_ok = (len(broken) == 1
                     and broken[0].type == "WARNING"
                     and broken[0].line == 2
                     and broken[0].message == "Title underline too short.")
        record("lint() valid->no errors, invalid->1 WARNING (docutils)",
               clean == [] and broken_ok,
               "clean={0} broken={1}".format(len(clean), broken_ok))
    except Exception as exc:  # pragma: no cover - diagnostic path
        record("lint() valid->no errors, invalid->1 WARNING (docutils)",
               False, repr(exc))

    # 3. lint_file() on disk
    tmp_file = os.path.join(_tmpdir(), "rst-lint-consumer-valid.rst")
    try:
        with open(tmp_file, "wt") as fh:
            fh.write(VALID_RST)
        errors = restructuredtext_lint.lint_file(tmp_file)
        record("lint_file() on-disk clean doc", errors == [],
               "errors={0}".format(len(errors)))
    except Exception as exc:  # pragma: no cover - diagnostic path
        record("lint_file() on-disk clean doc", False, repr(exc))
    finally:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

    if cli:
        # 4. --version
        try:
            rc, out, err = run([cli, "--version"])
            record("bin/rst-lint --version == 2.0.2",
                   rc == 0 and "2.0.2" in (out + err),
                   "rc={0} out={1!r}".format(rc, out.strip()))
        except Exception as exc:  # pragma: no cover - diagnostic path
            record("bin/rst-lint --version == 2.0.2", False, repr(exc))

        # 5/6/7. clean file / broken file / directory input
        workdir = tempfile.mkdtemp(prefix="rst-lint-consumer-", dir=_tmpdir())
        try:
            clean_path = os.path.join(workdir, "clean.rst")
            broken_path = os.path.join(workdir, "broken.rst")
            with open(clean_path, "wt") as fh:
                fh.write(VALID_RST)
            with open(broken_path, "wt") as fh:
                fh.write(INVALID_RST)

            try:
                rc, out, err = run([cli, clean_path])
                record("bin/rst-lint clean file -> exit 0, silent",
                       rc == 0 and out.strip() == "",
                       "rc={0} out={1!r}".format(rc, out.strip()))
            except Exception as exc:  # pragma: no cover - diagnostic path
                record("bin/rst-lint clean file -> exit 0, silent", False, repr(exc))

            try:
                rc, out, err = run([cli, broken_path])
                record("bin/rst-lint broken file -> exit 2 + WARNING",
                       rc == 2 and "WARNING" in out,
                       "rc={0} out={1!r}".format(rc, out.strip()))
            except Exception as exc:  # pragma: no cover - diagnostic path
                record("bin/rst-lint broken file -> exit 2 + WARNING", False, repr(exc))

            try:
                rc, out, err = run([cli, workdir])
                record("bin/rst-lint directory input aggregates *.rst",
                       rc == 2 and out.count("WARNING") == 1,
                       "rc={0} warnings={1}".format(rc, out.count("WARNING")))
            except Exception as exc:  # pragma: no cover - diagnostic path
                record("bin/rst-lint directory input aggregates *.rst", False, repr(exc))
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        # 8. OHOS platform case.
        try:
            mode = os.stat(cli).st_mode
            executable = bool(mode & stat.S_IXUSR)
            with open(cli, "rt") as fh:
                first_line = fh.readline().strip()
            shebang_ok = first_line == "#!/usr/bin/env python3"
            # OHOS /tmp is read-only; stage under the OHOS-provided $TMPDIR.
            ohos_dir = tempfile.mkdtemp(prefix="rst-lint-ohos-", dir=_tmpdir())
            try:
                ohos_rst = os.path.join(ohos_dir, "ohos.rst")
                with open(ohos_rst, "wt") as fh:
                    fh.write(VALID_RST)
                rc, out, err = run([cli, ohos_rst])
                path_ok = rc == 0 and out.strip() == ""
            finally:
                shutil.rmtree(ohos_dir, ignore_errors=True)
            record("[OHOS] POSIX entry script (+env python3, +x) runs on "
                   "OHOS filesystem path under $TMPDIR",
                   executable and shebang_ok and path_ok,
                   "mode={0:o} shebang={1!r} tmpdir={2} path_rc_ok={3}".format(
                       stat.S_IMODE(mode), first_line, _tmpdir(), path_ok))
        except Exception as exc:  # pragma: no cover - diagnostic path
            record("[OHOS] POSIX entry script (+env python3, +x) runs on "
                   "OHOS filesystem path under $TMPDIR", False, repr(exc))
    else:
        record("bin/rst-lint present", False, "no CLI path passed")

    discovered = len(CHECKS)
    passed = sum(1 for _n, ok, _d in CHECKS if ok)
    for name, ok, detail in CHECKS:
        print("[{0}] {1} {2}".format("PASS" if ok else "FAIL", name, detail))
    print("total: {0}/{1}".format(passed, discovered))

    marker = {
        "executed": True,
        "passed": passed == discovered,
        "command": "python3 test_rst_lint.py <bin/rst-lint>",
        "discovered": discovered,
        "passedCount": passed,
        "ohos_specific_checks": 1,
    }
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
    return 0 if passed == discovered else 1


def _tmpdir():
    """OHOS mounts /tmp read-only (SKILL §7 Gotcha E002): prefer $TMPDIR."""
    for candidate in (os.environ.get("TMPDIR"), os.environ.get("TMP"),
                      os.environ.get("TEMP"), tempfile.gettempdir()):
        if candidate and os.path.isdir(candidate) and os.access(candidate, os.W_OK):
            return candidate
    return tempfile.gettempdir()


if __name__ == "__main__":
    sys.exit(main())
