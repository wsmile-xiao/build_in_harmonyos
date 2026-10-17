#!/usr/bin/env python3
"""End-to-end checks for the uctodata 0.11 Conan package.

Usage: python3 test_data.py <package_folder>

Every assertion is about a property a *consumer* depends on, not about file
counts: the pkg-config contract ucto uses to find the data directory, the
presence and non-emptiness of the exact `config_DATA` payload upstream
installs, and the absence of build-system files that `make install-data`
would never ship.
"""
import os
import shutil
import subprocess
import sys

# Mirror of config/Makefile.am's config_DATA (35 installed data files).
TOKCONFIGS = [
    "tokconfig-eng", "tokconfig-eng-twitter", "tokconfig-nld", "tokconfig-fra",
    "tokconfig-ita", "tokconfig-spa", "tokconfig-por", "tokconfig-deu",
    "tokconfig-swe", "tokconfig-nld-twitter", "tokconfig-nld-sonarchat",
    "tokconfig-tur", "tokconfig-nld-withplaceholder", "tokconfig-nld-historical",
    "tokconfig-fry", "tokconfig-rus", "tokconfig-generic",
]
ABBREVIATIONS = ["nld_afk.abr", "spa.abr", "por.abr", "tur.abr", "fry.abr",
                 "rus.abr", "eng.abr", "swe.abr", "fra.abr", "deu.abr"]
RULES = ["e-mail.rule", "smiley.rule", "url.rule"]
TABLES = ["standard-quotes.quote", "exotic-quotes.quote",
          "standard-eos.eos", "exotic-eos.eos", "ligatures.filter"]
DATA_FILES = TOKCONFIGS + ABBREVIATIONS + RULES + TABLES

FAILURES = []
CHECKS = 0


def check(condition, message):
    global CHECKS
    CHECKS += 1
    if condition:
        print(f"        [ok] {message}")
    else:
        print(f"        [FAIL] {message}")
        FAILURES.append(message)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def main(pkg):
    print(f"[test] package_folder = {pkg}")
    datadir = os.path.join(pkg, "share", "ucto")
    pcfile = os.path.join(pkg, "lib", "pkgconfig", "uctodata.pc")

    # ── 1. data directory exists at the location ucto derives from pkg-config ──
    check(os.path.isdir(datadir), "share/ucto/ exists (uctodata datadir)")

    # ── 2. the pkg-config file is present and carries a *real* prefix ──────────
    check(os.path.isfile(pcfile), "lib/pkgconfig/uctodata.pc exists")
    if os.path.isfile(pcfile):
        text = read(pcfile)
        check("@prefix@" not in text and "@VERSION@" not in text,
              "uctodata.pc has no unexpanded autotools placeholders")
        check(f"prefix={pkg}" in text,
              "uctodata.pc prefix points at the Conan package folder")
        check("Version: 0.11" in text, "uctodata.pc declares Version: 0.11")
        check("Name: uctodata" in text, "uctodata.pc declares Name: uctodata")

    # ── 3. pkg-config itself, when available, must resolve prefix == package_folder
    #       (this is the exact query ucto's configure runs)
    #
    # NOTE: the absolute path returned by shutil.which() must be used here. When
    # subprocess is given an explicit env=, CPython goes through os.posix_spawn()
    # and performs NO PATH lookup of a bare program name, so passing the literal
    # "pkg-config" raises FileNotFoundError even though which() just found it.
    # (Observed on the OHOS CI worker: `pkg-config` exists, but running the bare
    #  name with a modified env failed with ENOENT.)
    pkgconfig = shutil.which("pkg-config")
    if pkgconfig:
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = os.path.join(pkg, "lib", "pkgconfig")
        try:
            proc = subprocess.run([pkgconfig, "--variable=prefix", "uctodata"],
                                  capture_output=True, text=True, env=env, timeout=60)
        except OSError as exc:
            print(f"        [skip] pkg-config found at {pkgconfig} but not executable: {exc}")
        else:
            got = (proc.stdout or "").strip()
            check(proc.returncode == 0 and got == pkg,
                  f"pkg-config --variable=prefix uctodata == package_folder (got {got!r})")
    else:
        print("        [skip] pkg-config not installed in the test environment")

    # ── 4. the complete upstream config_DATA payload ──────────────────────────
    missing = [n for n in DATA_FILES if not os.path.isfile(os.path.join(datadir, n))]
    check(not missing,
          f"all {len(DATA_FILES)} config_DATA files installed (missing: {missing})")
    empty = [n for n in DATA_FILES
             if os.path.isfile(os.path.join(datadir, n))
             and os.path.getsize(os.path.join(datadir, n)) == 0]
    check(not empty, f"no zero-length data files (empty: {empty})")
    check(len(TOKCONFIGS) == 17 and len(ABBREVIATIONS) == 10,
          "upstream payload shape unchanged (17 tokconfigs, 10 abbreviation lists)")

    # ── 5. faithful to `make install-data`: build-system files must not ship ──
    check(not os.path.exists(os.path.join(datadir, "Makefile.am")),
          "Makefile.am not installed (matches make install-data)")

    # ── 6. content sanity: tokeniser configs must resolve their %include targets ─
    #    tokconfig-nld pulls in `nld_afk` (the .abr file), the rules and the tables.
    cfg = os.path.join(datadir, "tokconfig-nld")
    if os.path.isfile(cfg):
        body = read(cfg)
        check(len(body.splitlines()) > 20, "tokconfig-nld has real configuration lines")
        for include in ("%include nld_afk", "%include url", "%include e-mail",
                        "%include smiley", "%include ligatures",
                        "%include standard-eos", "%include standard-quotes"):
            check(include in body,
                  f"tokconfig-nld references `{include}` (data is self-consistent)")
    with_include = [n for n in TOKCONFIGS
                    if os.path.isfile(os.path.join(datadir, n))
                    and "%include" in read(os.path.join(datadir, n))]
    check(len(with_include) >= 10,
          f"at least 10 tokconfigs use %include (got {len(with_include)})")

    print(f"[test] {CHECKS - len(FAILURES)}/{CHECKS} assertions passed")
    if FAILURES:
        print(f"[test] FAILED: {FAILURES}")
        return 1
    print("[test] All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
