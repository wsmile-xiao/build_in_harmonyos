#!/usr/bin/env python3
"""Apply additive HarmonyOS compatibility transforms to a GCC source tree.

Reused from the in-repo ``gcc/9.5.0`` recipe and adapted for GCC 16.
The config.sub triplet injection and Autoconf umask fix are version
independent.  The ``gcc/config.gcc`` aarch64 musl rewrites are GCC-version
specific, so a non-matching pattern is reported as a warning instead of
aborting, so the build can surface the exact divergence on the device.
"""

import shutil
import sys
from pathlib import Path


def inject_ohos_triplet(script_path):
    path = Path(script_path)
    content = path.read_text(encoding="utf-8", errors="surrogateescape")
    marker = "# HarmonyOS triplet compatibility (Conan recipe)"
    if marker in content:
        return
    newline = content.find("\n")
    if newline < 0:
        return
    snippet = """
{marker}
case "$1" in
  aarch64-linux-ohos | aarch64-unknown-linux-ohos | none-unknown-linux-ohos)
    echo aarch64-unknown-linux-ohos
    exit 0
    ;;
esac
""".format(marker=marker)
    path.write_text(
        content[: newline + 1] + snippet + content[newline + 1 :],
        encoding="utf-8",
        errors="surrogateescape",
    )


def rewrite_config_gcc(source):
    """Map linux-ohos onto GCC's existing musl target configuration.

    GCC 16 keeps the aarch64 musl blocks that GCC 9 has, but the exact text
    may have drifted.  Apply each rewrite only when the anchor is present and
    warn otherwise, so a GCC 16 divergence is visible without blocking the
    configure step outright.
    """
    config_gcc = source / "gcc" / "config.gcc"
    content = config_gcc.read_text(encoding="utf-8")
    replacements = (
        (
            "    *-*-*musl*)\n",
            "    *-*-*musl* | *-*-*ohos*)\n",
        ),
        (
            '\ttmake_file="${tmake_file} aarch64/t-aarch64 aarch64/t-aarch64-linux"\n'
            '\ttm_defines="${tm_defines}  TARGET_DEFAULT_ASYNC_UNWIND_TABLES=1"\n',
            '\ttmake_file="${tmake_file} aarch64/t-aarch64 aarch64/t-aarch64-linux"\n'
            '\tcase $target in\n'
            '\t*-*-linux-ohos*) tm_file="${tm_file} ohos.h" ;;\n'
            '\tesac\n'
            '\ttm_defines="${tm_defines}  TARGET_DEFAULT_ASYNC_UNWIND_TABLES=1"\n',
        ),
        (
            "*-linux-musl*)\n\ttmake_file=\"${tmake_file} t-musl\"\n",
            "*-linux-musl* | *-linux-ohos*)\n\ttmake_file=\"${tmake_file} t-musl\"\n",
        ),
        (
            "*-*-linux*android*|*-*-linux*uclibc*|*-*-linux*musl*)\n",
            "*-*-linux*android*|*-*-linux*uclibc*|*-*-linux*musl*|*-*-linux*ohos*)\n",
        ),
    )
    applied = 0
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new, 1)
            applied += 1
        else:
            print(
                "WARNING: gcc/config.gcc rewrite anchor not found in GCC 16; "
                "the aarch64 musl/ohos mapping may need manual adjustment: "
                + repr(old[:60]),
                file=sys.stderr,
            )
    config_gcc.write_text(content, encoding="utf-8")
    print(
        "config.gcc: applied {}/{} HarmonyOS rewrites".format(
            applied, len(replacements)
        )
    )


def fix_gmp_shell_scripts(source):
    """Invoke build helper scripts through $(SHELL).

    On HMDFS, shebang scripts cannot be executed directly (the loader fails
    with "bad interpreter: Permission denied"), and chmod does not reliably
    stick.  gmp's mpn asm rules hand m4-ccas / cpp-ccas to libtool as the CC
    command, and GCC's libcpp / gcc rules call move-if-change directly, so
    prefix them with $(SHELL) to run them through bash explicitly.
    """
    targets = (
        "gmp/mpn/Makefile.in",
        "gmp/mpn/Makeasm.am",
    )
    replaced = 0
    for rel in targets:
        path = source / rel
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="surrogateescape")
        updated = content.replace(
            "$(top_srcdir)/mpn/m4-ccas",
            "$(SHELL) $(top_srcdir)/mpn/m4-ccas",
        )
        updated = updated.replace(
            "$(top_srcdir)/mpn/cpp-ccas",
            "$(SHELL) $(top_srcdir)/mpn/cpp-ccas",
        )
        if updated != content:
            path.write_text(updated, encoding="utf-8", errors="surrogateescape")
            replaced += 1
    print("gmp shell scripts: patched {} file(s)".format(replaced))

    # move-if-change is invoked directly by gcc/ and libcpp/ Makefiles; its
    # #!/bin/sh shebang fails on HMDFS.  Rewrite every Makefile.in /
    # Make-lang.in / Makefile.am reference to run it through $(SHELL).
    # GCC 16 already prefixes most call sites with $(SHELL); protect those so
    # we do not double-prefix them.
    mv_replaced = 0
    for rel in (
        "libcpp/Makefile.in",
        "gcc/Makefile.in",
        "gcc/c/Make-lang.in",
        "gcc/objc/Make-lang.in",
    ):
        path = source / rel
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="surrogateescape")
        protected = content.replace(
            "$(SHELL) $(srcdir)/../move-if-change",
            "\x00SHELL_MV\x00",
        )
        updated = protected.replace(
            "$(srcdir)/../move-if-change",
            "$(SHELL) $(srcdir)/../move-if-change",
        ).replace("\x00SHELL_MV\x00", "$(SHELL) $(srcdir)/../move-if-change")
        if updated != content:
            path.write_text(updated, encoding="utf-8", errors="surrogateescape")
            mv_replaced += 1
    print("move-if-change: patched {} file(s)".format(mv_replaced))

    # mpfr's get_patches.sh is invoked directly by mpfr/src/Makefile; its
    # shebang fails on HMDFS the same way.  Prefix with $(SHELL).
    # Only rewrite Makefile.in: touching Makefile.am marks the .in stale and
    # makes make re-run automake (automake-1.17 is not installed on the
    # device), which aborts the mpfr build.
    gp_replaced = 0
    for rel in ("mpfr/src/Makefile.in",):
        path = source / rel
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="surrogateescape")
        updated = content.replace(
            "$(GET_PATCHES_SH)",
            "$(SHELL) $(GET_PATCHES_SH)",
        )
        if updated != content:
            path.write_text(updated, encoding="utf-8", errors="surrogateescape")
            gp_replaced += 1
    print("get_patches.sh: patched {} file(s)".format(gp_replaced))

    # libgcc's mkheader.sh is invoked directly (mkheader.sh > tmp-libgcc_tm.h)
    # and its #!/bin/sh shebang fails on HMDFS; run it through $(SHELL).  Also
    # undo a double-shell 'sh $(SHELL)' for the unwind.h move-if-change rule.
    lg_replaced = 0
    lg_mk = source / "libgcc" / "Makefile.in"
    if lg_mk.is_file():
        content = lg_mk.read_text(encoding="utf-8", errors="surrogateescape")
        updated = content.replace(
            "\t\t$(srcdir)/mkheader.sh > tmp-libgcc_tm.h",
            "\t\t$(SHELL) $(srcdir)/mkheader.sh > tmp-libgcc_tm.h",
        )
        updated = updated.replace(
            "\tsh $(SHELL) $(srcdir)/../move-if-change $$dest "
            "$(gcc_objdir)/include/unwind.h",
            "\t$(SHELL) $(srcdir)/../move-if-change $$dest "
            "$(gcc_objdir)/include/unwind.h",
        )
        if updated != content:
            lg_mk.write_text(updated, encoding="utf-8", errors="surrogateescape")
            lg_replaced += 1
    print("libgcc mkheader.sh: patched {} file(s)".format(lg_replaced))


def prepare(source, ohos_header):
    for filename in ("config.sub", "configfsf.sub"):
        for script in source.rglob(filename):
            inject_ohos_triplet(script)

    for configure in source.rglob("configure"):
        content = configure.read_text(
            encoding="utf-8", errors="surrogateescape"
        )
        updated = content.replace("umask 077", "umask 022")
        if updated != content:
            configure.write_text(
                updated, encoding="utf-8", errors="surrogateescape"
            )

    rewrite_config_gcc(source)

    fix_gmp_shell_scripts(source)

    shutil.copy2(ohos_header, source / "gcc" / "config" / "ohos.h")


def main():
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: prepare_ohos_sources.py SOURCE_FOLDER OHOS_HEADER"
        )
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
