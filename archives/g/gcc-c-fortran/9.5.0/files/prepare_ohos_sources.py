#!/usr/bin/env python3
"""Apply additive HarmonyOS compatibility transforms to a GCC source tree."""

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
                "GCC 9.5.0 OHOS source transform no longer matches config.gcc"
            )
        config_content = config_content.replace(old, new, 1)
    config_gcc.write_text(config_content, encoding="utf-8")

    shutil.copy2(ohos_header, source / "gcc" / "config" / "ohos.h")


def main():
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: prepare_ohos_sources.py SOURCE_FOLDER OHOS_HEADER"
        )
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
