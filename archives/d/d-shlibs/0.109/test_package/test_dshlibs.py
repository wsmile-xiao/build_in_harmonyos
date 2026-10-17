#!/usr/bin/env python3
"""d-shlibs consumer test (R34) — really executes both shipped tools.

Usage:
    test_dshlibs.py <pkg_folder> [<dpkg_folder>] [<binutils_folder>]

d-shlibs ships no library: it is a pair of bash scripts. A meaningful consumer
test therefore *runs* them instead of linking against them:

  A  installed artifacts      bin/d-shlibmove, bin/d-devlibdeps (executable),
                              share/man/man1/*.1, licenses/COPYING
  B  `bash -n`                upstream `make check' step 1 on both scripts
  C  argument handling        documented exit codes / messages of both tools
  D  d-shlibmove end-to-end   upstream autopkgtest scenario
                              (debian/tests/uppercase.d): a compiled
                              libUppercase.so -> libUppercase.so.1.0.0 chain
                              plus a debian/control, then the installed
                              d-shlibmove is run and its dry-run exit code (2)
                              and computed move plan are asserted. The script
                              internally calls d-devlibdeps, so the emitted
                              debian/libuppercase1-dev.substvars is asserted
                              too.
  E  d-devlibdeps standalone  emits `devlibs:Depends=' for a real ELF library

Groups D/E additionally need a Debian-shaped toolchain (dpkg-architecture,
$DEB_HOST_GNU_TYPE-objdump) and a C compiler. When one of those is absent the
group is reported as LIMITED with the exact technical reason instead of being
faked — Groups A/B/C remain hard assertions in every environment.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

# ── fixtures (mirror upstream debian/tests/uppercase.d) ─────────────────────

_LIBUPPERCASE_C = """\
/*
   Sample code to test 'libUppercase' handling.
 */
int test(int a)
{
  return a;
}
"""

_DEBIAN_CONTROL = """\
Source: libuppercase
Section: libs
Priority: standard
Build-Depends: debhelper (>= 5)
Maintainer: dancerj
Standards-Version: 3.7.2

Package: libuppercase1
Architecture: any
Section: libs
Priority: required
Depends: ${shlibs:Depends}
Description: test

Package: libuppercase1-dev
Architecture: any
Section: libdevel
Priority: optional
Depends: libuppercase1 (= ${Source-Version})
Conflicts: libuppercase-dev
Provides: libuppercase-dev
Description: test
"""

_FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "fixtures")

_SEARCH_DIRS = (
    "/data/service/hnp/bin",
    "/storage/Users/currentUser/usr/local/bin",
    "/data/app/bin",
    "/system/bin",
    "/usr/bin",
    "/bin",
)

_RESULTS = []          # (group, ok, detail)
_LIMITED = []          # human-readable limitation notes


def _ok(group: str, detail: str) -> None:
    _RESULTS.append((group, True, detail))
    print("OK: [%s] %s" % (group, detail))


def _fail(group: str, detail: str) -> None:
    _RESULTS.append((group, False, detail))
    print("FAIL: [%s] %s" % (group, detail), file=sys.stderr)


def _note(msg: str) -> None:
    _LIMITED.append(msg)
    print("LIMITED: %s" % msg)


def _find(name: str, extra=()) -> str:
    """Locate an executable robustly on minimal OHOS/CI workers."""
    cands = [c for c in extra if c]
    for d in _SEARCH_DIRS:
        cands.append(os.path.join(d, name))
    try:
        w = shutil.which(name)
        if w:
            cands.append(w)
    except Exception:
        pass
    for c in cands:
        try:
            if c and os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        except OSError:
            continue
    return ""


def _is_bash(path: str) -> bool:
    if not path:
        return False
    try:
        r = subprocess.run([path, "-c", 'test -n "$BASH_VERSION" && echo yes'],
                           capture_output=True, text=True, timeout=60)
        return r.returncode == 0 and "yes" in (r.stdout or "")
    except Exception:
        return False


def _find_bash() -> str:
    cands = [os.environ.get("CONFIG_SHELL", ""), os.environ.get("SHELL", "")]
    for name in ("bash",):
        cands.append(_find(name))
    cands += ["/data/service/hnp/bin/bash", "/usr/bin/bash", "/bin/bash"]
    for c in cands:
        if c and _is_bash(c):
            return c
    return ""


def _write_exec(path: str, text: str) -> None:
    # HMFS honours open(2) mode even where chmod is ignored, so create the
    # helper wrappers with 0755 straight away.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    except Exception:
        try:
            os.close(fd)
        except Exception:
            pass
        raise
    try:
        os.chmod(path, 0o755)
    except OSError:
        pass


def _run(cmd, cwd, env, timeout=300):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True,
                          text=True, timeout=timeout)


def main() -> int:  # noqa: C901 - linear assertion checklist by design
    if len(sys.argv) < 2:
        print("FAIL: missing package folder argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    dpkg_dir = sys.argv[2] if len(sys.argv) > 2 else ""
    binutils_dir = sys.argv[3] if len(sys.argv) > 3 else ""

    bindir = os.path.join(pkg, "bin")
    dsm = os.path.join(bindir, "d-shlibmove")
    ddl = os.path.join(bindir, "d-devlibdeps")

    # ── A: installed artifacts ────────────────────────────────────────────
    for f in (dsm, ddl,
              os.path.join(pkg, "share", "man", "man1", "d-shlibmove.1"),
              os.path.join(pkg, "share", "man", "man1", "d-devlibdeps.1"),
              os.path.join(pkg, "licenses", "COPYING")):
        if os.path.isfile(f) and os.path.getsize(f) > 0:
            _ok("A", "artifact present: %s" % os.path.relpath(f, pkg))
        else:
            _fail("A", "missing/empty artifact: %s" % f)
    for f in (dsm, ddl):
        if os.path.isfile(f) and os.access(f, os.X_OK):
            _ok("A", "executable bit set: %s" % os.path.relpath(f, pkg))
        else:
            _fail("A", "not executable: %s" % f)

    bash = _find_bash()
    if not bash:
        _fail("B", "no bash interpreter found - cannot exercise the scripts")
        print("RESULT: ASSERT_PASS=%d ASSERT_FAIL=%d"
              % (sum(1 for r in _RESULTS if r[1]),
                 sum(1 for r in _RESULTS if not r[1])))
        return 1
    _ok("B", "bash interpreter: %s" % bash)

    work = tempfile.mkdtemp(prefix="dshlibs-test-")
    scratch = os.path.join(work, "scratch")
    os.makedirs(scratch, exist_ok=True)
    harness_bin = os.path.join(work, "harness-bin")
    os.makedirs(harness_bin, exist_ok=True)

    env = dict(os.environ)
    env["SHELL"] = bash
    env["CONFIG_SHELL"] = bash
    env["TMPDIR"] = work

    # ── B: upstream `make check' step 1 = `bash -n' on both scripts ───────
    for f in (dsm, ddl):
        if not os.path.isfile(f):
            continue
        r = _run([bash, "-n", f], work, env)
        if r.returncode == 0:
            _ok("B", "bash -n %s (upstream make check step 1)" % os.path.basename(f))
        else:
            _fail("B", "bash -n %s -> rc=%d %s"
                  % (os.path.basename(f), r.returncode, (r.stderr or "").strip()))

    # ── C: documented argument handling (real execution, no toolchain) ────
    r = _run([bash, dsm], work, env)
    if r.returncode == 1 and "is not a valid shared library file name" in (r.stderr or ""):
        _ok("C", "d-shlibmove <no args> -> rc=1 + 'not a valid shared library "
                 "file name'")
    else:
        _fail("C", "d-shlibmove <no args> -> rc=%d out=%r err=%r"
              % (r.returncode, (r.stdout or "")[-200:], (r.stderr or "")[-200:]))

    r = _run([bash, dsm, os.path.join(scratch, "notalib.txt")], work, env)
    if r.returncode == 1 and "is not a valid shared library file name" in (r.stderr or ""):
        _ok("C", "d-shlibmove <non-.so argument> -> rc=1 + same validation error")
    else:
        _fail("C", "d-shlibmove <non-.so> -> rc=%d err=%r"
              % (r.returncode, (r.stderr or "")[-200:]))

    r = _run([bash, ddl], work, env)
    if r.returncode == 1 and "not enough options given" in (r.stdout or ""):
        _ok("C", "d-devlibdeps <no args> -> rc=1 + 'not enough options given'")
    else:
        _fail("C", "d-devlibdeps <no args> -> rc=%d out=%r"
              % (r.returncode, (r.stdout or "")[-200:]))

    r = _run([bash, ddl, "--help"], work, env)
    if r.returncode == 64 and "Unknown option" in (r.stderr or ""):
        _ok("C", "d-devlibdeps --help -> rc=64 (EX_USAGE) + 'Unknown option'")
    else:
        _fail("C", "d-devlibdeps --help -> rc=%d err=%r"
              % (r.returncode, (r.stderr or "")[-200:]))

    # ── toolchain plumbing for groups D/E ────────────────────────────────
    dpkg_arch = os.path.join(dpkg_dir, "bin", "dpkg-architecture") if dpkg_dir else ""
    objdump = _find("objdump", [os.path.join(binutils_dir, "bin", "objdump")
                                if binutils_dir else ""])
    perl = _find("perl")
    # Prefer the native toolchain compiler over an inherited cross CC: the
    # fixture only needs a valid aarch64 shared object with a SONAME.
    cc = (_find("clang", ["/data/service/hnp/bin/clang", "/usr/bin/clang"])
          or _find("cc", ["/data/service/hnp/bin/cc", "/usr/bin/cc"])
          or _find(os.environ.get("CC", "") or "clang")
          or _find("gcc"))

    if dpkg_dir and os.path.isfile(dpkg_arch) and perl:
        # dpkg-architecture needs Dpkg.pm + its data tables, and the scripts
        # call it through PATH, so wrap it with the resolved absolute perl
        # (the shipped shebang points at the build-time interpreter).
        _write_exec(os.path.join(harness_bin, "dpkg-architecture"),
                    "#!%s\nexec \"%s\" \"%s\" \"$@\"\n" % (bash, perl, dpkg_arch))
        env["PERL5LIB"] = os.pathsep.join(
            [dpkg_dir] + ([env["PERL5LIB"]] if env.get("PERL5LIB") else []))
        env["DPKG_DATADIR"] = os.path.join(dpkg_dir, "share", "dpkg")
    else:
        _note("dpkg toolchain unavailable (dpkg_folder=%r perl=%r) - groups D/E "
              "limited to their error paths" % (dpkg_dir, perl))

    # d-shlibmove calls d-devlibdeps internally; make sure PATH resolves it
    # even though both scripts carry a `#!/bin/bash' shebang and OHOS has no
    # /bin/bash.
    _write_exec(os.path.join(harness_bin, "d-devlibdeps"),
                "#!%s\nexec \"%s\" \"%s\" \"$@\"\n" % (bash, bash, ddl))

    path_parts = [harness_bin, bindir]
    if dpkg_dir:
        path_parts.append(os.path.join(dpkg_dir, "bin"))
    if binutils_dir:
        path_parts.append(os.path.join(binutils_dir, "bin"))
    for d in _SEARCH_DIRS:
        path_parts.append(d)
    old_path = env.get("PATH", "")
    if old_path:
        path_parts.extend(old_path.split(os.pathsep))
    env["PATH"] = os.pathsep.join([p for p in path_parts if p])

    triplet = ""
    if dpkg_dir and os.path.isfile(dpkg_arch):
        r = _run([bash, "-c",
                  'eval "$(dpkg-architecture -s 2>/dev/null)"; '
                  'printf %s "$DEB_HOST_GNU_TYPE"'], work, env)
        triplet = (r.stdout or "").strip()
        if triplet:
            _ok("D", "dpkg-architecture reports DEB_HOST_GNU_TYPE=%s" % triplet)

    if triplet and objdump:
        # `$DEB_HOST_GNU_TYPE-objdump' is what both scripts invoke; the ohpcd
        # binutils package installs the unprefixed name, so bridge it. The
        # triplet is queried at runtime, never hardcoded.
        shim = os.path.join(harness_bin, "%s-objdump" % triplet)
        try:
            if os.path.islink(shim) or os.path.exists(shim):
                os.remove(shim)
            os.symlink(objdump, shim)
            _ok("D", "%s-objdump -> %s" % (triplet, objdump))
        except OSError as exc:
            _note("cannot create %s-objdump shim: %s" % (triplet, exc))

    # ── D: d-shlibmove end-to-end (upstream autopkgtest scenario) ─────────
    d_ready = bool(triplet and objdump and cc)
    if not d_ready:
        _note("group D skipped (triplet=%r objdump=%r cc=%r)" % (triplet, objdump, cc))
    else:
        # Stage the fixtures next to the working tree. The on-disk files in
        # fixtures/ are the declared source of truth (they mirror upstream
        # debian/tests/uppercase.d); the embedded copies are a safety net in
        # case a packaging step drops them.
        src_c = os.path.join(scratch, "libUppercase.c")
        fixture_c = os.path.join(_FIXTURE_DIR, "libUppercase.c")
        if os.path.isfile(fixture_c):
            shutil.copyfile(fixture_c, src_c)
        else:
            with open(src_c, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(_LIBUPPERCASE_C)

        r = _run([cc, "-shared", "-Wl,--soname=libUppercase.so.1",
                  "-o", "libUppercase.so.1.0.0", src_c],
                 scratch, env)
        if r.returncode != 0:
            _fail("D", "fixture compile failed rc=%d %s"
                  % (r.returncode, (r.stderr or "").strip()[-200:]))
        else:
            _ok("D", "fixture built with %s (cc -shared + SONAME)" % cc)
            os.symlink("libUppercase.so.1.0.0",
                       os.path.join(scratch, "libUppercase.so"))
            os.makedirs(os.path.join(scratch, "debian"), exist_ok=True)
            fixture_ctrl = os.path.join(_FIXTURE_DIR, "debian_control")
            ctrl = os.path.join(scratch, "debian", "control")
            if os.path.isfile(fixture_ctrl):
                shutil.copyfile(fixture_ctrl, ctrl)
            else:
                with open(ctrl, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(_DEBIAN_CONTROL)

            so = os.path.join(scratch, "libUppercase.so")
            r = _run([bash, dsm, so], scratch, env)
            out = r.stdout or ""
            if r.returncode == 2:
                _ok("D", "d-shlibmove <libUppercase.so> -> rc=2 dry-run "
                         "(upstream autopkgtest criterion)")
            else:
                _fail("D", "d-shlibmove <libUppercase.so> -> rc=%d (expected 2) "
                           "err=%r" % (r.returncode, (r.stderr or "")[-300:]))
            for needle, why in (
                    ("Dry-run. If you are satisfied, run with --commit",
                     "dry-run notice"),
                    ("install -d -m 755 debian/libuppercase1/usr/lib",
                     "shlib package dir plan"),
                    ("install -d -m 755 debian/libuppercase1-dev/usr/lib",
                     "dev package dir plan"),
                    ("libUppercase.so.1.0.0 debian/libuppercase1/usr/lib",
                     "real .so move target"),
                    ("PKGSHL=libuppercase1", "computed shlib package name"),
                    ("PKGDEV=libuppercase1-dev", "computed dev package name")):
                if needle in out:
                    _ok("D", "move plan contains %s" % why)
                else:
                    _fail("D", "move plan missing %s (%r)" % (why, needle))

            subst = os.path.join(scratch, "debian",
                                 "libuppercase1-dev.substvars")
            if os.path.isfile(subst):
                with open(subst, encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
                if content.startswith("devlibs:Depends="):
                    _ok("D", "d-devlibdeps ran internally -> %s = %r"
                             % (os.path.basename(subst), content.strip()))
                else:
                    _fail("D", "unexpected substvars content: %r" % content[:200])
            else:
                _fail("D", "d-devlibdeps did not emit %s" % subst)

    # ── E: d-devlibdeps standalone ───────────────────────────────────────
    if not d_ready:
        _note("group E skipped (needs dpkg toolchain + objdump)")
    else:
        out_file = os.path.join(scratch, "standalone.substvars")
        r = _run([bash, ddl, out_file,
                  os.path.join(scratch, "libUppercase.so.1.0.0")], scratch, env)
        if r.returncode != 0:
            _fail("E", "d-devlibdeps standalone -> rc=%d err=%r"
                  % (r.returncode, (r.stderr or "")[-300:]))
        elif os.path.isfile(out_file):
            with open(out_file, encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            if content.startswith("devlibs:Depends="):
                _ok("E", "d-devlibdeps standalone -> rc=0, wrote %r"
                         % content.strip())
            else:
                _fail("E", "unexpected standalone substvars: %r" % content[:200])
        else:
            _fail("E", "d-devlibdeps standalone produced no output file")

    shutil.rmtree(work, ignore_errors=True)

    passed = sum(1 for r in _RESULTS if r[1])
    failed = sum(1 for r in _RESULTS if not r[1])
    print("RESULT: ASSERT_PASS=%d ASSERT_FAIL=%d" % (passed, failed))
    if _LIMITED:
        print("LIMITED-NOTES: %d" % len(_LIMITED))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
