#!/usr/bin/env python3
"""Consumer test for the packaged lifelines 3.0.61 binaries.

Runs against the *installed* package only (PATH and TERMINFO_DIRS come from the
conan run environment), and checks: binary resolution, version banners,
database creation from a GEDCOM fixture, two consumer-written report programs,
the reports' actual genealogical content, and three negative paths.

Prints one "ok -" / "FAILED -" line per assertion and a final count.
"""
import os
import shutil
import subprocess
import sys

WORK = sys.argv[1]
DB = "ti"
GED = "ti.ged"

results = []


def check(label, condition, detail=""):
    results.append((label, bool(condition)))
    tag = "ok" if condition else "FAILED"
    print(f"{tag} - {label}{(' :: ' + detail) if detail and not condition else ''}",
          flush=True)
    return bool(condition)


def run(cmd, cwd=WORK, stdin_text=None, timeout=120):
    """Run argv *cmd* directly; a prompt can never block the suite forever.

    Anything without piped input runs with /dev/null on stdin, and every call
    is bounded: an interactive fallback would otherwise hang the whole suite.
    """
    try:
        proc = subprocess.run(cmd, cwd=cwd, input=stdin_text, capture_output=True,
                              text=True, timeout=timeout,
                              stdin=None if stdin_text is not None else subprocess.DEVNULL)
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return "TIMEOUT", out
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def write(name, text):
    path = os.path.join(WORK, name)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(WORK, exist_ok=True)

    # The GEDCOM fixture is upstream's own reports/st/ti.ged (md5 34364f35...),
    # and upstream's selftest puts it next to the new database name.
    with open(os.path.join(here, "data", GED), encoding="utf-8") as f:
        ged_text = f.read()
    write(GED, ged_text)

    llines = shutil.which("llines") or ""
    llexec = shutil.which("llexec") or ""
    check("bin/llines is on PATH", bool(llines))
    check("bin/llexec is on PATH", bool(llexec))
    if not llexec or not llines:
        return finish()

    rc, out = run([llines, "--version"])
    check("llines --version exits 0", rc == 0, f"rc={rc} out={out[:120]!r}")
    check("llines --version reports 3.0.61", "3.0.61" in out, out[:120])
    rc, out = run([llexec, "--version"])
    check("llexec --version exits 0", rc == 0, f"rc={rc} out={out[:120]!r}")
    check("llexec --version reports 3.0.61", "3.0.61" in out, out[:120])

    # Creating the database drives the curses front-end with the same keystroke
    # sequence upstream's own selftest feeds it.
    rc, out = run([llines, f"./{DB}"], stdin_text="yurti\nyyq\n")
    check("llines creates a database from GEDCOM", rc == 0, f"rc={rc} out={out[:200]!r}")
    # The database is a directory: aa/ab are the record subdirectories and
    # key/xrefs are files inside it (see upstream reports/st selftest layout).
    dbdir = os.path.join(WORK, DB)
    for member in ("aa", "ab"):
        check(f"database subdirectory {member} written",
              os.path.isdir(os.path.join(dbdir, member)))
    for member in ("key", "xrefs"):
        check(f"database file {member} written",
              os.path.isfile(os.path.join(dbdir, member)))

    # Consumer-written report program over individuals (the report language has
    # no ';' as a statement separator, so this is the upstream style).
    ind = write("consumer_indi.ll",
                "proc main() {\n"
                "  forindi(i, c) { print(d(c), \": \", key(i), nl()) }\n"
                "}\n")
    rc, out = run([llexec, "-x", ind, f"./{DB}"])
    check("llexec runs a consumer report over individuals", rc == 0,
          f"rc={rc} out={out[:300]!r}")
    check("report ends with the upstream success marker",
          "Program was run successfully." in out, out[-200:])
    for expect in ("1: I1", "2: I2", "3: I3"):
        check(f"report lists {expect}", expect in out, out[:200])
    check("report walks every individual of the fixture (10: I12)",
          "10: I12" in out, out[-200:])

    # Family records and their spouses resolve through the report language too.
    fam = write("consumer_fam.ll",
                "proc main() {\n"
                "  forfam(f, c) {\n"
                "    print(d(c), \": \", key(f), nl())\n"
                "    spouses(f, s, cs) { print(\"    \", d(cs), \": \", key(s), nl()) }\n"
                "  }\n"
                "}\n")
    rc, out = run([llexec, "-x", fam, f"./{DB}"])
    check("report navigates family records",
          rc == 0 and "1: F1" in out, f"rc={rc} out={out[:300]!r}")
    check("report resolves the first family's husband (    1: I2)",
          "    1: I2" in out, out[:300])
    check("report resolves the first family's wife (    2: I3)",
          "    2: I3" in out, out[:300])

    # Negative paths -- each must be reported, never silently green.
    rc, out = run([llexec, "-x", os.path.join(WORK, "no_such_program.ll"),
                   f"./{DB}"])
    check("a missing report program is reported as an error",
          "Program contains errors." in out and
          "Program was run successfully." not in out, f"rc={rc} out={out[:200]!r}")

    broken = write("broken.ll", "proc main() {\n  n = 0\n}\n")
    rc, out = run([llexec, "-x", broken, f"./{DB}"])
    check("a program the interpreter rejects is reported, not green",
          "Syntax Error" in out and "Program was run successfully." not in out,
          f"rc={rc} out={out[:200]!r}")

    rc, out = run([llexec, "-x", ind, "./no_such_db"], timeout=25)
    check("an absent database is refused (no success marker)",
          "no LifeLines database" in out and
          "Program was run successfully." not in out, f"rc={rc} out={out[:200]!r}")
    return finish()


def finish():
    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        if not ok:
            print(f"  pending: {label}", flush=True)
    print(f"CONSUMER-ASSERTS {passed}/{total}", flush=True)
    if passed == total:
        print("HMBS_TEST_PACKAGE_RESULT: PASS", flush=True)
        return 0
    print("HMBS_TEST_PACKAGE_RESULT: FAIL", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
