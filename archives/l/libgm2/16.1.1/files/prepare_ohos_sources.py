#!/usr/bin/env python3
"""Apply additive HarmonyOS compatibility transforms to a GCC 16 source tree.

Adapted from the GCC 14.2.0 recipe (archives/g/gcc-14/14.2.0) for the
GCC 16 snapshot.  The transforms are additive: non-HarmonyOS targets keep
their exact upstream behaviour.

In addition to the shared GCC OHOS transforms (triplet / umask / config.gcc
/ ohos.h) this script applies the Modula-2 frontend and runtime library
fixes required by the HarmonyOS port:

1. gcc/m2/Make-lang.in: inject --build/--host into the three nested
   configure/config-host invocations.  config.guess cannot identify
   HarmonyOS (`uname -s` = HarmonyOS) so the frontend sub-configures would
   fail with "cannot guess build type" otherwise.
2. gcc/m2/gm2-libs/config-host: Autoconf `umask 077` -> `umask 022`
   (HMDFS user-mapping quirk: 0700 temp directories become unwritable).
3. m2/mc bootstrap translator: hard-coded /tmp paths
   (/tmp/frag-*.frag, /tmp/mctemp.) -> current directory, because the
   HarmonyOS /tmp is read-only.  Both the .mod sources and the generated
   mc-boot C++ mirrors are patched so the translator can rebuild itself.
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


def apply_modula2_transforms(source):
    """Apply the Modula-2 frontend / runtime source transforms."""

    # 1. gcc/m2/Make-lang.in: pin the nested configure / config-host calls
    # to the OHOS build and host triplet.  Insert --build/--host directly
    # before the --target argument of each of the three invocations.
    make_lang = source / "gcc" / "m2" / "Make-lang.in"
    content = make_lang.read_text(encoding="utf-8", errors="surrogateescape")
    targets = (
        "               --target=$(target) \\\n",
        "                --target=$(target) --program-suffix=$(exeext) \\\n",
        "                --target=$(target) --program-suffix=$(exeext)' ; \\\n",
    )
    for target in targets:
        occurrences = content.count(target)
        if occurrences != 1:
            raise RuntimeError(
                "GCC 16 m2 Make-lang.in expects exactly one {!r} "
                "(found {})".format(target, occurrences)
            )
        indent = target.split("--target")[0]
        content = content.replace(
            target,
            indent + "--build=aarch64-linux-ohos --host=aarch64-linux-ohos \\\n" + target,
            1,
        )
    make_lang.write_text(content, encoding="utf-8", errors="surrogateescape")

    # 2. gcc/m2/gm2-libs/config-host: umask 077 -> 022 (HMDFS).
    config_host = source / "gcc" / "m2" / "gm2-libs" / "config-host"
    host_content = config_host.read_text(
        encoding="utf-8", errors="surrogateescape"
    )
    updated = host_content.replace("umask 077", "umask 022")
    if updated == host_content or "umask 022" not in updated:
        raise RuntimeError(
            "GCC 16 gm2-libs config-host umask transform no longer matches"
        )
    config_host.write_text(
        updated, encoding="utf-8", errors="surrogateescape"
    )

    # 3. mc bootstrap translator /tmp paths (see module docstring).
    mc_fixes = (
        (
            source / "gcc" / "m2" / "mc" / "mcStream.mod",
            "InitString ('/tmp/frag-%d-%d.frag')",
            "InitString ('frag-%d-%d.frag')",
        ),
        (
            source / "gcc" / "m2" / "mc-boot" / "GmcStream.cc",
            '"/tmp/frag-%d-%d.frag", 20',
            '"frag-%d-%d.frag", 15',
        ),
        (
            source / "gcc" / "m2" / "mc" / "mcPreprocess.mod",
            "InitString ('/tmp/mctemp.')",
            "InitString ('mctemp.')",
        ),
        (
            source / "gcc" / "m2" / "mc-boot" / "GmcPreprocess.cc",
            '"/tmp/mctemp.", 12',
            '"mctemp.", 7',
        ),
    )
    for path, old, new in mc_fixes:
        text = path.read_text(encoding="utf-8", errors="surrogateescape")
        if old not in text:
            raise RuntimeError(
                "GCC 16 mc path fix no longer matches {!r} in {}".format(
                    old, path
                )
            )
        path.write_text(
            text.replace(old, new, 1),
            encoding="utf-8",
            errors="surrogateescape",
        )

    # 4. gcc/m2/Make-lang.in: the cc1gm2 rule copies the freshly linked
    # stage-1 compiler over gcc/cc1gm2 with `cp -p`.  On HMDFS the target
    # becomes a code-signed executable and later overwrites in the same
    # `make all-gcc` fail with EPERM ("cp: cc1gm2: Operation not
    # permitted").  Remove the destination first so every re-copy creates a
    # brand-new file (same workaround proven in the interactive build).
    cc1gm2_rule = (
        "cc1gm2$(exeext): m2/stage1/cc1gm2$(exeext) $(m2.prev)\n"
        "\tcp -p $< $@\n"
    )
    cc1gm2_fixed = (
        "cc1gm2$(exeext): m2/stage1/cc1gm2$(exeext) $(m2.prev)\n"
        "\trm -f $@\n"
        "\tcp -p $< $@\n"
    )
    if cc1gm2_rule not in content:
        raise RuntimeError(
            "GCC 16 m2 Make-lang.in cc1gm2 rule no longer matches"
        )
    content = content.replace(cc1gm2_rule, cc1gm2_fixed, 1)
    make_lang.write_text(content, encoding="utf-8", errors="surrogateescape")


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

    config_gcc = source / "gcc" / "config.gcc"
    config_content = config_gcc.read_text(encoding="utf-8")
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
    for old, new in replacements:
        if old not in config_content:
            raise RuntimeError(
                "GCC 16 OHOS source transform no longer matches config.gcc"
            )
        config_content = config_content.replace(old, new, 1)
    config_gcc.write_text(config_content, encoding="utf-8")

    shutil.copy2(ohos_header, source / "gcc" / "config" / "ohos.h")

    apply_modula2_transforms(source)
    apply_libgcc_thread_fixes(source)


def apply_libgcc_thread_fixes(source):
    """Make libgcc gthr-posix.h usable on OHOS musl.

    libgcc chooses its default threading header via thread_header; on OHOS
    this recipe pins it to gthr-posix.h so the gm2 runtime (RTco.cc) can use
    __gthread_cond_t.  Two upstream assumptions about glibc/bionic break on
    OHOS musl:

    1. ``__gthrw(pthread_cancel)`` needs a ``pthread_cancel`` declaration,
       which OHOS musl does not provide (only glibc exposes it); guard the
       weak symbol declaration away on __OHOS__ like __BIONIC__ already is.
    2. GTHR_ACTIVE_PROXY defaults to pthread_cancel on non-glibc systems;
       fall back to pthread_create on OHOS exactly as bionic does.
    """
    gthr_posix = source / "libgcc" / "gthr-posix.h"
    gthr_text = gthr_posix.read_text(encoding="utf-8", errors="surrogateescape")

    decl_old = (
        "__gthrw(pthread_detach)\n"
        "#ifndef __BIONIC__\n"
        "__gthrw(pthread_cancel)\n"
        "#endif\n"
        "__gthrw(sched_yield)\n"
    )
    decl_new = (
        "__gthrw(pthread_detach)\n"
        "#if !defined(__BIONIC__) && !defined(__OHOS__)\n"
        "__gthrw(pthread_cancel)\n"
        "#endif\n"
        "__gthrw(sched_yield)\n"
    )
    if decl_old not in gthr_text:
        raise RuntimeError(
            "GCC 16 gthr-posix.h pthread_cancel declaration no longer matches"
        )
    gthr_text = gthr_text.replace(decl_old, decl_new, 1)

    proxy_old = (
        "#elif defined (__BIONIC__)\n"
        "# define GTHR_ACTIVE_PROXY\t__gthrw_(pthread_create)\n"
        "#else\n"
        "# define GTHR_ACTIVE_PROXY\t__gthrw_(pthread_cancel)\n"
    )
    proxy_new = (
        "#elif defined (__BIONIC__) || defined (__OHOS__)\n"
        "# define GTHR_ACTIVE_PROXY\t__gthrw_(pthread_create)\n"
        "#else\n"
        "# define GTHR_ACTIVE_PROXY\t__gthrw_(pthread_cancel)\n"
    )
    if proxy_old not in gthr_text:
        raise RuntimeError(
            "GCC 16 gthr-posix.h GTHR_ACTIVE_PROXY no longer matches"
        )
    gthr_text = gthr_text.replace(proxy_old, proxy_new, 1)
    gthr_posix.write_text(gthr_text, encoding="utf-8", errors="surrogateescape")


def main():
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: prepare_ohos_sources.py SOURCE_FOLDER OHOS_HEADER"
        )
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
