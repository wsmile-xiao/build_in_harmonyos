#!/usr/bin/env python3
"""Apply additive HarmonyOS compatibility transforms for the lib32-gcc (arm-linux-ohos) cross-compiler.

lib32-gcc targets 32-bit ARM (arm-linux-ohos) on a HarmonyOS PC (aarch64 host).  The
OHOS PC SDK uses a musl-derived C library, so the ARM target is treated like the
existing musl targets plus an OHOS-specific os header (ohos.h).
"""

import os
import re
import shutil
import sys
from pathlib import Path


def inject_ohos_triplet(script_path):
    path = Path(script_path)
    content = path.read_text(encoding="utf-8", errors="surrogateescape")
    marker = "# HarmonyOS triplet compatibility (Conan recipe lib32-gcc)"
    if marker in content:
        return
    newline = content.find("\n")
    if newline < 0:
        return
    snippet = """
{marker}
case "$1" in
  aarch64-linux-ohos | aarch64-unknown-linux-ohos | none-unknown-linux-ohos | \\
  arm-linux-ohos | arm-unknown-linux-ohos)
    case "$1" in
      arm*) echo arm-unknown-linux-ohos ;;
      *)    echo aarch64-unknown-linux-ohos ;;
    esac
    exit 0
    ;;
esac
""".format(marker=marker)
    path.write_text(
        content[: newline + 1] + snippet + content[newline + 1 :],
        encoding="utf-8",
        errors="surrogateescape",
    )


def allow_arm_linux_ohos(config_text):
    """Whitelist arm*-*-linux-ohos* in config.gcc's "Unsupported targets list".

    Upstream GCC aborts arm targets whose triplet has no "eabi" substring:
    the pre-check around config.gcc line ~350 only whitelists
    "arm*-*-*eabi*" and blacklists legacy targets like "arm*-*-linux*".
    Our normalized triplet arm-unknown-linux-ohos (config.sub pads the
    missing vendor with "unknown") therefore hits the blacklist and dies
    with "*** Configuration ... not supported" before reaching the real
    arm*-*-linux-* case.  Insert an explicit whitelist entry right after
    the eabi one; shell case stops at the first match, so the target is
    released before the blacklist is consulted.  Idempotent: re-running
    leaves the file unchanged.
    """
    pattern = re.compile(r"( +arm\*-\*-\*eabi\*[ \t]*\\\n)[ \t]*\)")
    if "arm*-*-linux-ohos*" in config_text:
        return config_text
    updated, count = pattern.subn(
        lambda match: match.group(1) + " | arm*-*-linux-ohos*\t\t\t\\\n )",
        config_text,
        count=1,
    )
    if count == 0:
        raise RuntimeError(
            "lib32-gcc OHOS source transform no longer matches the "
            "config.gcc unsupported-targets whitelist"
        )
    return updated


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
                "lib32-gcc OHOS source transform no longer matches config.gcc"
            )
        config_content = config_content.replace(old, new, 1)

    # Release arm-unknown-linux-ohos from the upstream unsupported-targets
    # blacklist (see allow_arm_linux_ohos for the rationale).
    config_content = allow_arm_linux_ohos(config_content)

    # The ARM Linux EABI target case (GCC 16.1.0+) references arm/linux-eabi.h
    # (older layouts used arm/linux.h / arm/linux-elf.h) inside its tm_file
    # assignment.  Append our OHOS os header right after the ARM Linux OS header
    # so the 32-bit ARM target picks up __OHOS__ builtins inline within the
    # matched case.  Match on the tm_file line (not a contiguous literal) because
    # the real line is e.g. 'tm_file="$tm_file arm/bpabi.h arm/linux-eabi.h ..."'.
    arm_linux_headers = ("arm/linux-eabi.h", "arm/linux.h", "arm/linux-elf.h")
    injected = False
    config_lines = config_content.split("\n")
    for header in arm_linux_headers:
        if injected:
            break
        for index, line in enumerate(config_lines):
            if "tm_file=" in line and header in line and "ohos.h" not in line:
                config_lines[index] = line.replace(header, header + " ohos.h", 1)
                injected = True
                break
    if injected:
        config_content = "\n".join(config_lines)
    else:
        # Fallback: append a generic case that adds ohos.h for *-linux-ohos*.
        snippet = (
            '\ncase $target in\n'
            '  *-*-linux-ohos*)\n'
            '\ttm_file="${tm_file} ohos.h" ;;\n'
            'esac\n'
        )
        config_content = config_content.rstrip("\n") + "\n" + snippet

    config_gcc.write_text(config_content, encoding="utf-8")

    ohos_header_dst = source / "gcc" / "config" / "ohos.h"
    os.makedirs(os.path.dirname(ohos_header_dst), exist_ok=True)
    shutil.copy2(ohos_header, ohos_header_dst)


def main():
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: prepare_ohos_sources.py SOURCE_FOLDER OHOS_HEADER"
        )
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
