#!/usr/bin/env python3
"""Apply additive HarmonyOS host-compatibility transforms to a GCC 14.2.0 tree.

This recipe builds a *cross* compiler: build/host = aarch64-linux-ohos
(HarmonyOS PC), target = i686-elf (bare-metal).  Only host-side transforms are
needed here:

1. config.sub / configfsf.sub cannot canonicalize the ``aarch64-linux-ohos``
   build/host triplet (GCC 14.2.0 ships config.sub timestamp 2021-10-27, which
   predates OHOS support).  Inject an early-match case for the triplet.
2. The generated ``configure`` scripts (GCC top-level and the in-tree
   gmp/mpfr/mpc prerequisites) use ``umask 077`` before creating their
   temporary directories.  On the HarmonyOS HMDFS worker that masks too much
   and the temporary directory cannot be used, so rewrite to ``umask 022``.

Unlike the native ``gcc/9.5.0`` recipe, no ``gcc/config.gcc`` / ``ohos.h``
transform is needed here: the target is ``i686-elf``, not ``*-linux-ohos``.
"""

import re
import sys
from pathlib import Path


MARKER = "# HarmonyOS triplet compatibility (Conan recipe)"


def inject_ohos_triplet(script_path):
    path = Path(script_path)
    content = path.read_text(encoding="utf-8", errors="surrogateescape")
    if MARKER in content:
        return
    newline = content.find("\n")
    if newline < 0:
        return
    snippet = """

{MARKER}
case "$1" in
  aarch64-linux-ohos | aarch64-unknown-linux-ohos | none-unknown-linux-ohos)
    echo aarch64-unknown-linux-ohos
    exit 0
    ;;
esac
""".format(MARKER=MARKER)
    path.write_text(
        content[: newline + 1] + snippet + content[newline + 1 :],
        encoding="utf-8",
        errors="surrogateescape",
    )


def prepare(source):
    source = Path(source)
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

    # gmp 默认 enable_assembly=yes 会编译 mpn 汇编（arm64 的 add_n.asm 等），
    # 其编译脚本 m4-ccas 是 #!/bin/sh，在 HMDFS 上无法通过 shebang 直接 exec
    # （E087：bad interpreter: Permission denied）。禁用汇编改用 C 通用代码，
    # gmp 作为 host 侧数学库，纯 C 实现功能等价，仅损失汇编优化性能。
    gmp_configure = source / "gmp" / "configure"
    if gmp_configure.exists():
        content = gmp_configure.read_text(
            encoding="utf-8", errors="surrogateescape"
        )
        updated = content.replace(
            "  enable_assembly=yes\n", "  enable_assembly=no\n", 1
        )
        if updated == content:
            raise RuntimeError(
                "gmp configure default enable_assembly=yes not found"
            )
        gmp_configure.write_text(
            updated, encoding="utf-8", errors="surrogateescape"
        )

    # GCC 构建系统的辅助脚本（move-if-change / get_patches.sh / mkinstalldirs /
    # install-sh / ylwrap / compile / depcomp / missing / ar-lib / test-driver
    # 等）会被 make 直接 exec。HMDFS 上 chmod +x 不生效（E087），任何 shebang
    # （无论 /bin/sh 还是 /data/service/hnp/bin/bash）都无法通过 exec 走通。
    # 因此遍历源码树，删除所有脚本的 #!/bin/sh shebang 行，让 make 的
    # $(SHELL)=bash 直接用 bash 解释脚本（等价于 `bash script`，已实测可行）。
    for script in source.rglob("*"):
        if not script.is_file():
            continue
        try:
            content = script.read_text(
                encoding="utf-8", errors="surrogateescape"
            )
        except (OSError, ValueError):
            continue
        # 兼容各种 shebang 变体：#!/bin/sh、#! /bin/sh（带空格）、#!/bin/bash 等。
        # 只 strip sh/bash 类解释器，Python 等其它解释器脚本不受影响。
        if content.startswith("#!"):
            first_newline = content.find("\n")
            if first_newline >= 0 and re.search(
                r"\b(ba)?sh\b", content[:first_newline]
            ):
                script.write_text(
                    content[first_newline + 1 :],
                    encoding="utf-8",
                    errors="surrogateescape",
                )

    # CI 环境（conan-pr-check worker）里，clang 链接 conftest 失败
    # （'C compiler cannot create executables'），真机 shadow CI 已验证
    # clang 能编译。参考 libseccomp 2.5.6：把 AC_PROG_CC 检测链的
    # works/exeext/cross 链接命令改成 touch conftest（HMDFS 链接受限，
    # 旧版 autoconf 缓存变量 ac_cv_prog_cc_works 在 GCC 14 新版 configure
    # 中已不读取，只能 patch 链接命令）。
    gcc_configure = source / "configure"
    if gcc_configure.exists():
        cfg = gcc_configure.read_text(
            encoding="utf-8", errors="surrogateescape"
        )
        # works 检测：ac_link_default -> touch conftest
        cfg = cfg.replace(
            '(eval "$ac_link_default") 2>&5',
            '(eval "touch conftest") 2>&5  # [ohos] works->touch',
            1,
        )
        # exeext + cross 检测：ac_link -> touch conftest（marker 定位，
        # 避免破坏 AC_PROG_CC 之后 GCC 其它真实链接检测）
        for marker, tag in (
            ("checking for suffix of executables", "exeext"),
            ("checking whether we are cross compiling", "cross"),
        ):
            idx = cfg.find(marker)
            if idx >= 0:
                eval_idx = cfg.find('(eval "$ac_link") 2>&5', idx)
                if eval_idx >= 0:
                    cfg = (
                        cfg[:eval_idx]
                        + '(eval "touch conftest") 2>&5  # [ohos] '
                        + tag
                        + "->touch"
                        + cfg[eval_idx + len('(eval "$ac_link") 2>&5') :]
                    )
        # cross 检测的运行：./conftest -> true（touch 出的空文件不可执行）
        cross_idx = cfg.find("checking whether we are cross compiling")
        if cross_idx >= 0:
            run_idx = cfg.find('(eval "$ac_try") 2>&5', cross_idx)
            if run_idx >= 0:
                cfg = (
                    cfg[:run_idx]
                    + '(eval "true") 2>&5  # [ohos] cross-run->true'
                    + cfg[run_idx + len('(eval "$ac_try") 2>&5') :]
                )
        gcc_configure.write_text(
            cfg, encoding="utf-8", errors="surrogateescape"
        )


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare_ohos_sources.py SOURCE_FOLDER")
    prepare(sys.argv[1])


if __name__ == "__main__":
    main()
