#!/usr/bin/env python3
"""Consumer verification for the packaged reflex generator (reflex/20241231).

Usage:  python3 test_reflex.py <package_folder> <cc> <cxx>

Seven real-behaviour checks (no stubs).  Each passing check prints exactly one
``SMOKE-PASS <name>`` line; any failure prints ``SMOKE-FAIL <name>: <reason>``
and the script exits non-zero.

  1. version      reflex --version reports the flex 2.5.4 lineage and this
                  patch level (20241231)
  2. cxx-version  reflex++ --version works — the C++ entry point (a symlink
                  upstream creates at install time) survived packaging
  3. header       include/reFlexLexer.h declares class yyFlexLexer
  4. library      lib/librefl.a is a non-empty archive exporting yywrap
  5. manpage      share/man/man1/reflex.1 is installed and non-empty
  6. c-scanner    reflex generates a C scanner from a .l file; it is compiled
                  and linked against librefl.a (which supplies main() and
                  yywrap()); the token stream for a fixed input is asserted
  7. cxx-scanner  reflex++ generates a C++ scanner whose first line pulls in
                  the installed reFlexLexer.h; it compiles, links and
                  tokenises the same input identically
"""

import os
import shutil
import subprocess
import sys
import tempfile

C_LEX = """%{
#include <stdio.h>
%}
%%
[0-9]+                  { printf("NUM:%s\\n", yytext); }
[A-Za-z_][A-Za-z0-9_]*  { printf("ID:%s\\n", yytext); }
[ \\t\\n]+               { }
.                       { printf("OTHER:%s\\n", yytext); }
%%
"""

CXX_LEX = """%option C++ noyywrap
%{
#include <iostream>
%}
%%
[0-9]+                  { std::cout << "NUM:" << YYText() << "\\n"; }
[A-Za-z_][A-Za-z0-9_]*  { std::cout << "ID:" << YYText() << "\\n"; }
[ \\t\\n]+               { }
.                       { std::cout << "OTHER:" << YYText() << "\\n"; }
%%
int main() {
    FlexLexer* lexer = new yyFlexLexer;
    while (lexer->yylex() != 0) { }
    delete lexer;
    return 0;
}
"""

SCAN_INPUT = "42 alpha 7 _b9\n"
EXPECTED_TOKENS = ["NUM:42", "ID:alpha", "NUM:7", "ID:_b9"]

# Well-known absolute locations of the OHOS build tools.  A bare command name
# is not resolvable on every OHOS host: subprocess goes through posix_spawn,
# whose fast path performs no PATH lookup, so `["sh", ...]` / `["clang", ...]`
# raise FileNotFoundError even though the tool is on PATH.
_CLANG_PATHS = ("/data/service/hnp/bin/clang", "/system/bin/clang")
_CLANGXX_PATHS = ("/data/service/hnp/bin/clang++", "/system/bin/clang++")
_NM_PATHS = ("/data/service/hnp/bin/llvm-nm", "/system/bin/llvm-nm",
             "/data/service/hnp/bin/nm", "/system/bin/nm", "/usr/bin/nm")


def _resolve_tool(explicit, names, paths):
    """Resolve a build tool without ever spawning a bare command name.

    Order: the explicit value handed down by the Conan profile (absolute in
    the OHOS profile), then well-known absolute paths, then ``shutil.which``
    (pure Python, no subprocess), and only then the bare name as a last
    resort for hosts where the plain spawn path does work.
    """
    if explicit and os.path.isabs(explicit) and os.path.exists(explicit):
        return explicit
    for path in paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    import shutil
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return explicit or names[0]


def _run(cmd, cwd=None, stdin_data=None):
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        input=stdin_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=300,
    )
    return proc.returncode, proc.stdout or ""


def _usable(candidate):
    """True if we can really work inside *candidate*.

    A writable parent is not enough: an HMDFS-backed volume can hand back a
    freshly created directory without usable owner permissions, so verify by
    writing a file into a directory we just made and reading it straight back
    (the same failure mode that breaks autoconf's config.status).
    """
    try:
        probe_dir = tempfile.mkdtemp(prefix="reflex-probe-", dir=candidate)
    except OSError:
        return False
    try:
        probe = os.path.join(probe_dir, "probe")
        with open(probe, "w", encoding="utf-8") as handle:
            handle.write("ok")
        with open(probe, encoding="utf-8") as handle:
            return handle.read() == "ok"
    except OSError:
        return False
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)


def _workdir():
    """Writable scratch dir; ``/tmp`` and the HMDFS user volume are unreliable.

    The generated scanner, its object file and the linked consumer all live
    here, so prefer the /data cache first and only then whatever the ambient
    TMPDIR points at.
    """
    for candidate in ("/data/storage/el2/base/cache",
                      os.environ.get("TMPDIR"),
                      os.path.join(os.path.expanduser("~"), "tmp"),
                      os.getcwd()):
        if not candidate or not os.path.isdir(candidate):
            continue
        if not _usable(candidate):
            continue
        try:
            return tempfile.mkdtemp(prefix="reflex-test-", dir=candidate)
        except OSError:
            continue
    return tempfile.mkdtemp(prefix="reflex-test-")


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _tokens(output):
    return [line.strip() for line in output.splitlines() if line.strip()]


def check_version(reflex):
    rc, out = _run([reflex, "--version"])
    if rc != 0:
        return False, "exit code {0}: {1}".format(rc, out.strip()[-200:])
    if "2.5.4" not in out:
        return False, "output lacks the flex lineage version: {0!r}".format(
            out.strip()[-200:])
    if "20241231" not in out:
        return False, "output lacks the patch level 20241231: {0!r}".format(
            out.strip()[-200:])
    return True, out.strip().splitlines()[0][:120]


def check_cxx_version(reflexpp):
    if not os.path.exists(reflexpp):
        return False, "missing {0} (upstream installs it as a symlink)".format(
            reflexpp)
    rc, out = _run([reflexpp, "--version"])
    if rc != 0:
        return False, "exit code {0}: {1}".format(rc, out.strip()[-200:])
    if "2.5.4" not in out:
        return False, "output lacks the flex lineage version"
    return True, out.strip().splitlines()[0][:120]


def check_header(include_dir):
    path = os.path.join(include_dir, "reFlexLexer.h")
    if not os.path.isfile(path):
        return False, "missing {0}".format(path)
    text = open(path, encoding="utf-8", errors="replace").read()
    if "class yyFlexLexer" not in text:
        return False, "header does not declare class yyFlexLexer"
    if "class FlexLexer" not in text:
        return False, "header does not declare the FlexLexer base class"
    return True, "{0} bytes".format(len(text))


def check_library(lib_dir):
    path = os.path.join(lib_dir, "librefl.a")
    if not os.path.isfile(path):
        return False, "missing {0}".format(path)
    size = os.path.getsize(path)
    if size <= 0:
        return False, "empty archive"
    # A real ar archive: "!<arch>" magic.
    with open(path, "rb") as handle:
        if handle.read(7) != b"!<arch>":
            return False, "not an ar archive"
    nm = _resolve_tool(None, ("llvm-nm", "nm"), _NM_PATHS)
    if nm and os.path.isabs(nm):
        rc, out = _run([nm, path])
        if rc != 0 or "yywrap" not in out:
            return False, "archive does not export yywrap"
        return True, "librefl.a {0} bytes, exports yywrap".format(size)
    return True, "librefl.a {0} bytes (nm unavailable)".format(size)


def check_manpage(package_folder):
    path = os.path.join(package_folder, "share", "man", "man1", "reflex.1")
    if not os.path.isfile(path) or os.path.getsize(path) <= 0:
        return False, "missing or empty {0}".format(path)
    return True, "reflex.1 {0} bytes".format(os.path.getsize(path))


def check_c_scanner(reflex, include_dir, lib_dir, work):
    lex = os.path.join(work, "consumer_c.l")
    src = os.path.join(work, "consumer_c.c")
    exe = os.path.join(work, "consumer_c")
    _write(lex, C_LEX)

    rc, out = _run([reflex, "-o", src, lex], cwd=work)
    if rc != 0:
        return False, "reflex failed: {0}".format(out.strip()[-200:])
    if not os.path.isfile(src) or os.path.getsize(src) <= 0:
        return False, "reflex produced no scanner"

    cc = _resolve_tool(os.environ.get("_REFLEX_CC"), ("clang",),
                       _CLANG_PATHS)
    rc, out = _run([cc, "-I", include_dir, src,
                    "-L", lib_dir, "-lrefl", "-o", exe], cwd=work)
    if rc != 0:
        return False, "compile/link failed: {0}".format(out.strip()[-300:])

    rc, out = _run([exe], cwd=work, stdin_data=SCAN_INPUT)
    if rc != 0:
        return False, "scanner exit {0}: {1}".format(rc, out.strip()[-200:])
    tokens = _tokens(out)
    if tokens != EXPECTED_TOKENS:
        return False, "tokens {0!r} != {1!r}".format(tokens, EXPECTED_TOKENS)
    return True, "librefl.a main() driven scanner emitted {0}".format(
        ",".join(tokens))


def check_cxx_scanner(reflexpp, include_dir, lib_dir, work):
    lex = os.path.join(work, "consumer_cxx.l")
    src = os.path.join(work, "consumer_cxx.cc")
    exe = os.path.join(work, "consumer_cxx")
    _write(lex, CXX_LEX)

    # Upstream is used in `-t` (stdout) form on purpose: with `-o <file>` the
    # `#include <reFlexLexer.h>` prologue line is emitted before the output
    # file is opened and is lost, so only the stdout form yields a
    # self-contained scanner.
    rc, out = _run([reflexpp, "-t", lex], cwd=work)
    if rc != 0:
        return False, "reflex++ failed: {0}".format(out.strip()[-200:])
    if not out.lstrip().startswith("#include <reFlexLexer.h>"):
        return False, ("generated scanner does not start with the "
                       "reFlexLexer.h include: {0!r}".format(
                           out.strip()[:120]))
    _write(src, out)

    cxx = _resolve_tool(os.environ.get("_REFLEX_CXX"), ("clang++",),
                        _CLANGXX_PATHS)
    rc, out = _run([cxx, "-std=c++17", "-I", include_dir, src,
                    "-L", lib_dir, "-lrefl", "-o", exe], cwd=work)
    if rc != 0:
        return False, "C++ compile/link failed: {0}".format(out.strip()[-400:])

    rc, out = _run([exe], cwd=work, stdin_data=SCAN_INPUT)
    if rc != 0:
        return False, "C++ scanner exit {0}: {1}".format(rc, out.strip()[-200:])
    tokens = _tokens(out)
    if tokens != EXPECTED_TOKENS:
        return False, "tokens {0!r} != {1!r}".format(tokens, EXPECTED_TOKENS)
    return True, "C++ scanner emitted {0}".format(",".join(tokens))


def main(argv):
    if len(argv) < 2:
        print("usage: test_reflex.py <package_folder> [cc] [cxx]",
              file=sys.stderr)
        return 2
    package_folder = argv[1]
    if len(argv) > 2 and argv[2]:
        os.environ["_REFLEX_CC"] = argv[2]
    if len(argv) > 3 and argv[3]:
        os.environ["_REFLEX_CXX"] = argv[3]

    bin_dir = os.path.join(package_folder, "bin")
    include_dir = os.path.join(package_folder, "include")
    lib_dir = os.path.join(package_folder, "lib")
    reflex = os.path.join(bin_dir, "reflex")
    reflexpp = os.path.join(bin_dir, "reflex++")

    work = _workdir()
    checks = [
        ("version", lambda: check_version(reflex)),
        ("cxx-version", lambda: check_cxx_version(reflexpp)),
        ("header", lambda: check_header(include_dir)),
        ("library", lambda: check_library(lib_dir)),
        ("manpage", lambda: check_manpage(package_folder)),
        ("c-scanner", lambda: check_c_scanner(reflex, include_dir, lib_dir, work)),
        ("cxx-scanner", lambda: check_cxx_scanner(reflexpp, include_dir,
                                                 lib_dir, work)),
    ]

    failures = []
    for name, check in checks:
        try:
            ok, detail = check()
        except Exception as exc:  # noqa: BLE001 - report, do not mask
            ok, detail = False, "{0}: {1}".format(type(exc).__name__, exc)
        if ok:
            print("SMOKE-PASS {0} ({1})".format(name, detail), flush=True)
        else:
            print("SMOKE-FAIL {0}: {1}".format(name, detail), flush=True)
            failures.append(name)

    if failures:
        print("SMOKE-SUMMARY {0}/{1} checks failed: {2}".format(
            len(failures), len(checks), ", ".join(failures)), flush=True)
        return 1
    print("SMOKE-SUMMARY {0}/{0} checks passed".format(len(checks)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
