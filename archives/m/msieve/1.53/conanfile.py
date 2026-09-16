#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# conanfile.py — msieve 1.53 (OpenHarmony PC / aarch64)
#
# 上游为纯 Makefile 工程（仅 all/clean/help 目标），无 CMake/Autotools/configure。
# AArch64 移植要点（全部通过命令行变量覆盖，不改上游源码）：
#   1. Makefile:23 OPT_FLAGS 无条件含 -march=native（x86 专用）。AArch64 上
#      clang 报 "unknown target feature / unsupported option"，必须整体覆盖
#      OPT_FLAGS 为通用优化标志。
#   2. Makefile:295/300 给两个 generic sieve_core 变体无条件传 -DHAS_SSE2，
#      但源码中所有 SSE2 内联汇编使用点均有 GCC_ASM32X/GCC_ASM64X/MSC_ASM*
#      宏守卫，在 AArch64 上全部回退上游可移植 C 实现，该宏无实际影响
#      （详见 notes.md）。不伪造 CPU 特性、不删除任何算法校验。
#   3. Makefile:45/89 LIBS 固定 -ldl -lz -lgmp -lm -lpthread；OHOS musl 将
#      libdl/libpthread 并入 libc，sysroot 仍保留 stub 链接库，沿用上游
#      链接行即可（不修改源码/Makefile）。
#   4. 上游无 'make test'；官方测试方式为用已知合数实际运行分解，
#      由 test_package 承担（见 test_package/MANIFEST.yml）。
#   5. OHOS 打包的二进制须用 binary-sign-tool 注入 .codesign 段（先例
#      abx/0.1）。

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class MsieveConan(ConanFile):
    name = "msieve"
    version = "1.53"
    description = (
        "Msieve is a C library implementing factorization of large integers, "
        "with a complete suite of capabilities for the quadratic sieve (QS) "
        "and number field sieve (NFS) algorithms"
    )
    license = "Public Domain"  # 上游 Makefile:1-10: "placed in the public domain by its author, Jason Papadopoulos"
    homepage = "https://sourceforge.net/projects/msieve/"
    url = "https://atomgit.com/atomgit-ohos/third_party_msieve"
    topics = ("factorization", "integer", "QS", "NFS", "number-theory")

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 上游 Makefile:81/89 无条件链接 -lz -lgmp（zlib 仅 NO_ZLIB=1 时关闭，
        # GMP 无开关），故声明为硬依赖：
        #   gmp  — 大整数运算（gnfs 后台、ECM/squfof 小因子、APRCL 素性检验）
        #   zlib — NFS 后处理保存关系数据时的压缩读写
        self.requires("gmp/6.3.0.1")
        self.requires("zlib/1.3.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
        from conan.tools.gnu import GnuToolchain  # noqa: F401  (documented alternative)

        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        # 上游 Makefile 变量（Makefile:21-34, 273-278）：
        #   CC = gcc                          → 命令行覆盖为 OHOS clang
        #   OPT_FLAGS = -O3 ... -march=native → 整体覆盖（见文件头注释 1）
        #   MACHINE_FLAGS                     → 上游未定义，留作注入位
        #   CFLAGS/LIBS 为递归展开，命令行传入的 CFLAGS 会整体替换
        # all 目标产物：libmsieve.a + msieve（demo.c 链接静态库）
        cc = shutil.which("clang") or "clang"
        ar = shutil.which("llvm-ar") or "ar"
        ranlib = shutil.which("llvm-ranlib") or "ranlib"

        # GMP/zlib 头文件与库路径（conan 依赖注入）
        cflags = []
        ldflags = []
        for dep in ("gmp", "zlib"):
            info = self.dependencies[dep].cpp_info.aggregated_components()
            cflags += [f"-I{d}" for d in info.includedirs]
            ldflags += [f"-L{d}" for d in info.libdirs]
        # 上游 LIBS（-ldl -lz -lgmp -lm -lpthread）由 Makefile 自身追加，
        # 这里只注入依赖路径；无需重复 -lz/-lgmp。

        opt_flags = (
            "-O3 -fomit-frame-pointer -D_FILE_OFFSET_BITS=64 -DNDEBUG "
            "-D_LARGEFILE64_SOURCE"
        )
        # MSIEVE_SVN_VERSION 由上游 Makefile:32-33 自行展开为
        # -DMSIEVE_SVN_VERSION="\"$(SVN_VERSION)\""，嵌套引号由 make 处理，
        # 避免跨 shell（zsh/bash）引号语义差异 —— 只传纯单词 SVN_VERSION。
        cflags_full = (
            f"{opt_flags} -Wall -W"
            " -I. -Iaprcl -Iinclude -Ignfs -Ignfs/poly -Ignfs/poly/stage1"
            + "".join(f" {f}" for f in cflags)
        )
        ldflags_full = " ".join(ldflags)

        # 变量值含空格，必须经 shell 引用，否则 make 将其拆成多个目标。
        self.run(
            f'make all CC="{cc}" AR="{ar}" RANLIB="{ranlib}" '
            f'OPT_FLAGS="{opt_flags}" MACHINE_FLAGS="" SVN_VERSION=unknown '
            f'CFLAGS="{cflags_full}" LDFLAGS="{ldflags_full}"',
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "libmsieve.a",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "msieve",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        # 公共 API 头：include/（msieve.h、util.h、gmp_xface.h 等）
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        # 许可证文件：上游声明位于 Makefile 头部注释（源码包无独立 COPYING）
        copy(
            self,
            "Makefile",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if self.settings.os == "OHOS":
            self._sign_ohos_elf(os.path.join(self.package_folder, "bin", "msieve"))

    def package_info(self):
        self.cpp_info.libs = ["msieve"]
        # 公共头文件位于 include/（含 msieve.h），默认 includedirs=["include"] 即可
        self.cpp_info.includedirs = ["include"]
        # 消费者链接 msieve 需要同时链接 gmp/zlib/线程（上游 demo 链接行）
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.requires = ["gmp::gmp", "zlib::zlib"]

    def _sign_ohos_elf(self, path):
        # 先例：archives/a/abx/0.1/conanfile.py::_sign_ohos_elf。
        # 签名工具/readelf 的所在目录因 worker 而异，统一由 profile 的
        # [buildenv] PATH 提供；在 conanbuild 环境下解析出绝对路径后
        # 直接 subprocess 调用，不依赖进程 PATH 布局。
        from conan.tools.env import VirtualBuildEnv

        if not os.path.isfile(path):
            raise ConanException(f"Missing packaged executable: {path}")

        # PR #9387 根因：远端 worker 的 /bin 不在 PATH，裸 "sh" 无法启动。
        # 先解析任务局部 shell：CONFIG_SHELL > SHELL > shutil.which("sh")
        # （同一变量 conanbuild 环境优先于进程环境）。候选必须是存在且
        # 可执行的文件；全部不可用则 fail-closed，绝不跳过签名
        # （E443 闭包原则）。
        build_env = VirtualBuildEnv(self).vars()
        shell = None
        for cand in (
            build_env.get("CONFIG_SHELL"),
            os.environ.get("CONFIG_SHELL"),
            build_env.get("SHELL"),
            os.environ.get("SHELL"),
            shutil.which("sh"),
        ):
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                shell = cand
                break
        if shell is None:
            raise ConanException(
                "No usable shell (CONFIG_SHELL/SHELL/PATH) to resolve "
                "binary-sign-tool for OHOS signing"
            )

        # 在 conanbuild 环境下让 shell 解析工具绝对路径
        # （conan Environment.vars() 返回 EnvVars，其 vars 属性即 dict）。
        # PATH 前置 conanbuild 值（profile 已前置工具目录），进程 PATH 兜底。
        resolve = r'command -v binary-sign-tool; command -v llvm-readelf || command -v readelf'
        resolve_env = dict(os.environ)
        build_path = build_env.get("PATH")
        if build_path:
            resolve_env["PATH"] = (
                build_path + os.pathsep + resolve_env["PATH"]
                if resolve_env.get("PATH") else build_path
            )
        proc = subprocess.run(
            [shell, "-c", resolve],
            capture_output=True, text=True, timeout=30,
            env=resolve_env,
        )
        out = proc.stdout.split()
        if len(out) < 2:
            raise ConanException(
                f"binary-sign-tool/readelf not resolvable via {shell} "
                f"(rc={proc.returncode}, stderr={proc.stderr.strip()[:120]}); "
                "cannot sign OHOS ELF"
            )
        signer, readelf = out[0], out[1]

        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed packaged executable has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)
