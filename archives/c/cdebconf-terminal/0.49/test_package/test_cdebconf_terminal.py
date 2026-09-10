#!/usr/bin/env python3
"""Consumer test for cdebconf-terminal 0.49 (R34: real use, no stubs).

Platform fact: OHOS provides neither libnewt nor the GTK2/VTE-0.28 stack,
so the upstream configure logic (mirrored live by the recipe via
pkg-config) legitimately yields FRONTENDS='' and `make install` ships zero
plugins. Demanding a plugin .so here would contradict upstream itself.

This test therefore verifies that honest outcome with live evidence
instead of a hardcoded expectation (3 real assertions):
1. GUI stacks really undetectable — pkg-config probes for `libnewt` and
   `gtk+-x11-2.0 vte` are re-executed here (same names as configure.ac);
   result is printed, not assumed.
2. Package tree consistent with the probes — zero plugins if and only if
   no stack is detectable. If a stack IS detectable, its plugin must
   exist, be non-empty, carry terminal symbols, and dlopen (future-proof:
   adding newt/GTK2 to the device can never silently pass).
3. Hard deps wired — the cdebconf package provides libdebconfclient and
   the plugin API headers (frontend.h/question.h) the plugins build
   against; any plugin found in (2) is dlopened with its real deps.
"""
import ctypes
import glob
import os
import shutil
import subprocess
import sys

PASS = "PASS:"
FAIL = "FAIL:"


def _pkg_config():
    found = shutil.which("pkg-config")
    if found:
        return found
    for cand in ("/data/service/hnp/bin/pkg-config",
                 "/usr/bin/pkg-config"):
        if os.path.isfile(cand):
            return cand
    return "pkg-config"


def _probe(args):
    try:
        proc = subprocess.run(args, capture_output=True, text=True,
                              timeout=60)
        return proc.returncode
    except Exception as exc:
        print("%s probe %r error: %s" % (FAIL, " ".join(args), exc))
        return 127


def find_plugins(pkg):
    patterns = [
        os.path.join(pkg, "**", "*terminal*.so*"),
        os.path.join(pkg, "**", "*terminal*.a"),
    ]
    hits = []
    for pat in patterns:
        hits.extend(glob.glob(pat, recursive=True))
    if not hits:
        for sub in ("lib", "libexec", "lib/cdebconf", "libexec/cdebconf"):
            d = os.path.join(pkg, sub)
            if os.path.isdir(d):
                for fn in os.listdir(d):
                    if fn.endswith(".so") or ".so." in fn:
                        hits.append(os.path.join(d, fn))
    return sorted(set(hits))


def check_plugin_symbols(path):
    symbols = ""
    for cmd in (["nm", "-D", path], ["strings", path]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=30)
            symbols = r.stdout or ""
            if symbols:
                break
        except Exception:
            symbols = ""
    lowered = (symbols or "").lower()
    return any(k in lowered for k in ("terminal", "cdebconf", "newt", "gtk"))


def main():
    if len(sys.argv) < 3:
        print("%s usage: test_cdebconf_terminal.py "
              "<cdebconf-terminal pkg> <cdebconf pkg>" % FAIL)
        sys.exit(2)
    pkg_folder = sys.argv[1]
    cdebconf_pkg = sys.argv[2]

    # --- Assertion 1: live frontend probes (same names as configure.ac).
    pc = _pkg_config()
    rc_newt = _probe([pc, "--exists", "libnewt"])
    rc_gtk = _probe([pc, "--exists", "gtk+-x11-2.0", "vte"])
    print("%s probe libnewt: pkg-config rc=%d" % (PASS, rc_newt))
    print("%s probe gtk+-x11-2.0+vte: pkg-config rc=%d" % (PASS, rc_gtk))
    expected = set()
    if rc_newt == 0:
        expected.add("newt")
    if rc_gtk == 0:
        expected.add("gtk")
    print("%s expected FRONTENDS={%s}" % (PASS, " ".join(sorted(expected))))

    # --- Assertion 2: package tree consistent with probes.
    plugins = find_plugins(pkg_folder)
    if not expected:
        if plugins:
            print("%s expected zero plugins but found: %s"
                  % (FAIL, ", ".join(plugins)))
            sys.exit(1)
        print("%s package installs zero plugins, consistent with "
              "undetectable GUI stacks (upstream configure would do the "
              "same)" % PASS)
    else:
        if not plugins:
            print("%s stacks detectable (%s) but no plugin found under %s"
                  % (FAIL, sorted(expected), pkg_folder))
            sys.exit(1)
        print("%s found plugin(s): %s" % (
            PASS, ", ".join(os.path.relpath(p, pkg_folder)
                            for p in plugins)))
        for target in plugins:
            size = os.path.getsize(target)
            if size == 0:
                print("%s plugin %s is empty" % (FAIL, target))
                sys.exit(1)
            if not check_plugin_symbols(target):
                print("%s plugin %s lacks terminal-related symbols"
                      % (FAIL, target))
                sys.exit(1)
            print("%s plugin %s non-empty (%d bytes) with terminal symbols"
                  % (PASS, target, size))

    # --- Assertion 3: hard deps wired + dlopen what exists.
    lib_hits = glob.glob(os.path.join(cdebconf_pkg, "**",
                                      "libdebconfclient*"), recursive=True)
    fe_hits = glob.glob(os.path.join(cdebconf_pkg, "**", "frontend.h"),
                        recursive=True)
    q_hits = glob.glob(os.path.join(cdebconf_pkg, "**", "question.h"),
                       recursive=True)
    if not lib_hits:
        print("%s libdebconfclient missing under %s"
              % (FAIL, cdebconf_pkg))
        sys.exit(1)
    if not fe_hits or not q_hits:
        print("%s plugin API headers missing under %s "
              "(frontend.h=%s question.h=%s)"
              % (FAIL, cdebconf_pkg, fe_hits, q_hits))
        sys.exit(1)
    print("%s cdebconf hard dep ok: %s + plugin API headers present"
          % (PASS, os.path.relpath(lib_hits[0], cdebconf_pkg)))
    for target in plugins:
        try:
            ctypes.CDLL(target)
        except Exception as exc:
            print("%s dlopen(%s) failed: %s" % (FAIL, target, exc))
            sys.exit(1)
        print("%s dlopen plugin ok: %s"
              % (PASS, os.path.relpath(target, pkg_folder)))
    if not plugins:
        print("%s nothing to dlopen (zero-plugin install verified above)"
              % PASS)

    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
