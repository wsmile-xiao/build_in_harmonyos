#!/usr/bin/env python3
"""Conan recipe for klibc-run-init 2.0.14 — klibc 的 run-init 子工具，HarmonyOS PC aarch64。

run-init 位于上游 usr/kinit/run-init/，是 initramfs 早期用户空间的收尾工具：
删除 initramfs 内容、把真实根文件系统 MS_MOVE 挂回 /、chroot 并 exec 指定的 init。
Usage: exec run-init [-d caps] [-c consoledev] [-n] [-p] /real-root /sbin/init [args]
适配要点：
- 与父配方 archives/k/klibc/2.0.14 完全同源（相同 tarball URL+SHA256）；
  patch 0001/0002/0003 原样复用，0004 为父配方变体（all 目标保留 usr/kinit）。
- kernel-style kbuild 交叉编译（KLIBCARCH/CC/AR/LD 等命令行变量，同父配方）；
  构建目标扩到 usr/kinit（连带 kinit/ipconfig/nfsmount/fstype/resume 闭包，纯 C）。
- 只打包静态链接的 bin/run-init（usr/kinit/run-init/static/run-init，链接 ../lib.a，
  自包含，不依赖 klibc 共享库）与 LICENSE；OHOS 内核要求 .codesign 签名段（E077）。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class KlibcRunInitConan(ConanFile):
    name = "klibc-run-init"
    version = "2.0.14"
    description = "run-init — klibc initramfs switch_root utility (delete initramfs, overmount real root, exec init)"
    license = "MIT AND BSD-3-Clause AND GPL-2.0-only"
    homepage = "https://www.kernel.org/pub/linux/libs/klibc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # conan arch -> klibc KLIBCARCH
    _ARCH_MAP = {
        "armv8": "arm64",
        "armv7": "arm",
        "armv6": "arm",
        "x86_64": "x86_64",
        "x86": "i386",
        "ppc64le": "ppc64",
        "ppc64": "ppc64",
        "riscv64": "riscv64",
    }

    # KLIBCARCH -> OHOS asm 头目录名（相对 sysroot/usr/include）
    _ASM_DIR_MAP = {
        "arm64": "aarch64-linux-ohos/asm",
        "arm": "arm-linux-ohos/asm",
        "x86_64": "x86_64-linux-ohos/asm",
        "i386": "i686-linux-ohos/asm",
    }

    def _klibc_arch(self):
        return self._ARCH_MAP.get(str(self.settings.arch), str(self.settings.arch))

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # run-init 只依赖 klibc 源码树自身（libc + UAPI 头），无外部 Conan 依赖。
        pass

    def layout(self):
        basic_layout(self)
        # klibc 在源码树内构建（kernel-style kbuild 产物输出到源码树）。
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---- 工具链与 sysroot 探测（与父配方 archives/k/klibc/2.0.14 相同） ----

    def _compilers(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return {
            "cc": compilers.get("c", "clang"),
            "cxx": compilers.get("cpp", "clang++"),
        }

    def _tool(self, cc, name):
        """从 CC 同目录推导 llvm-* 工具完整路径（编译环境 PATH 可能不含 hnp/bin）。"""
        cc_dir = os.path.dirname(cc)
        if cc_dir:
            return os.path.join(cc_dir, name)
        return name

    def _find_sysroot(self, cc):
        """探测 OHOS sysroot（clang --print-resource-dir 向上 4 级再取 sysroot）。"""
        try:
            rd = subprocess.check_output(
                [cc, "--print-resource-dir"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if rd:
                d = os.path.normpath(rd)
                for _ in range(4):
                    d = os.path.dirname(d)
                sr = os.path.join(d, "sysroot")
                if os.path.isdir(os.path.join(sr, "usr", "include")):
                    return sr
        except Exception:
            pass
        try:
            out = subprocess.check_output(
                [cc, "--print-sysroot"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if out and os.path.isdir(os.path.join(out, "usr", "include")):
                return out
        except Exception:
            pass
        cc_dir = os.path.dirname(os.path.abspath(cc))
        for rel in (("..", "sysroot"), ("..", "..", "sysroot")):
            c = os.path.normpath(os.path.join(cc_dir, *rel))
            if os.path.isdir(os.path.join(c, "usr", "include")):
                return c
        return None

    def _find_asm_dir(self, sysroot, arch):
        """探测 asm 头目录（相对 sysroot/usr/include）。"""
        inc = os.path.join(sysroot, "usr", "include")
        preferred = self._ASM_DIR_MAP.get(arch)
        if preferred and os.path.isdir(os.path.join(inc, preferred)):
            return preferred
        for name in ("aarch64-linux-ohos/asm", "asm-arm64", "asm"):
            if os.path.isdir(os.path.join(inc, name)):
                return name
        return None

    def build(self):
        apply_conandata_patches(self)
        arch = self._klibc_arch()
        cc = self._compilers()["cc"]
        tools = {
            "ar": self._tool(cc, "llvm-ar"),
            "ranlib": self._tool(cc, "llvm-ranlib"),
            "strip": self._tool(cc, "llvm-strip"),
            "nm": self._tool(cc, "llvm-nm"),
            "objcopy": self._tool(cc, "llvm-objcopy"),
            "objdump": self._tool(cc, "llvm-objdump"),
            "ld": self._tool(cc, "ld.lld"),
            "perl": self._tool(cc, "perl"),
        }
        sysroot = self._find_sysroot(cc)
        if not sysroot:
            raise ConanInvalidConfiguration(
                "OHOS sysroot not found; cannot satisfy klibc KLIBCKERNELSRC "
                "(Linux UAPI headers) dependency"
            )
        asmdir = self._find_asm_dir(sysroot, arch)
        if not asmdir:
            raise ConanInvalidConfiguration(
                f"OHOS asm UAPI headers not found under {sysroot}/usr/include"
            )

        # 干净的 UAPI 头目录：只含 linux/asm/asm-generic，排除 OHOS musl 头
        # （同父配方；直接 -I sysroot/include 会经 #include_next 误吸入 musl 头导致污染）。
        kh = os.path.join(self.build_folder, "kernel-headers")
        kh_inc = os.path.join(kh, "include")
        os.makedirs(kh_inc, exist_ok=True)
        inc_root = os.path.join(sysroot, "usr", "include")
        shutil.copytree(os.path.join(inc_root, "linux"), os.path.join(kh_inc, "linux"))
        shutil.copytree(os.path.join(inc_root, "asm-generic"),
                        os.path.join(kh_inc, "asm-generic"))
        shutil.copytree(os.path.join(inc_root, asmdir), os.path.join(kh_inc, "asm"))
        # 物化到源码树 usr/include（顶层 make 不触发 usr/include 的 always 目标，
        # 而 klibc 头会 #include <asm/*.h> 与 <linux/*.h>；同父配方做法）。
        for name in ("asm", "asm-generic", "linux"):
            dst = os.path.join(self.source_folder, "usr", "include", name)
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(os.path.join(kh_inc, name), dst)

        kernelsrc = kh

        # arm64 交叉链接：clang 编译需显式 target；ld.lld 直接链接需 emulation。
        # （kbuild 已探测 LD_IS_LLD 自动切换 --image-base/-Ttext-segment。）
        extra_cflags = ""
        extra_ldflags = ""
        if arch == "arm64":
            extra_cflags = "--target=aarch64-linux-ohos"
            extra_ldflags = "-m aarch64linux"
        elif arch == "x86_64":
            extra_cflags = "--target=x86_64-linux-ohos"
            extra_ldflags = "-m elf_x86_64"
        elif arch == "i386":
            extra_cflags = "--target=i686-linux-ohos"
            extra_ldflags = "-m elf_i386"

        make_vars = (
            f"KLIBCARCH={arch} "
            f"KLIBCKERNELSRC='{kernelsrc}' "
            f"KLIBCASMDIR='{asmdir}' "
            f"CC='{cc}' HOSTCC='{cc}' "
            f"AR='{tools['ar']}' RANLIB='{tools['ranlib']}' "
            f"STRIP='{tools['strip']}' NM='{tools['nm']}' "
            f"OBJCOPY='{tools['objcopy']}' OBJDUMP='{tools['objdump']}' "
            f"LD='{tools['ld']}' PERL='{tools['perl']}' "
            f"EXTRA_KLIBCCFLAGS='{extra_cflags}' "
            f"EXTRA_KLIBCLDFLAGS='{extra_ldflags}' "
        )
        # R9/E074：make -j1（kbuild jobserver/FIFO 多核偶发问题）。默认目标 all
        # （klcc + klibc）经 patch 0004 递归 scripts/basic + usr/klibc + usr/kinit，
        # usr/kinit 闭包含 run-init（static + shared 两版）。
        self.run(f"make {make_vars} -j1", env="conanbuild")
        # 上游无 run-init 专属测试（usr/klibc/tests 属父配方职责），不执行 make test。
        run_init = os.path.join(
            self.source_folder, "usr", "kinit", "run-init", "static", "run-init"
        )
        if not os.path.isfile(run_init):
            raise ConanInvalidConfiguration(
                f"run-init static binary was not produced by the kbuild: {run_init}"
            )

    def _sign_elf(self, prog, objcopy, signtool):
        """给 ELF 加 OHOS 代码签名（.codesign 段），否则内核拒绝 exec（E077）。

        binary-sign-tool 签名后会把权限重置为 660，需恢复执行权限。
        """
        self.run(
            f'{objcopy} --remove-section .codesign {prog} 2>/dev/null || true',
            env="conanbuild", ignore_errors=True,
        )
        r = self.run(
            f'{signtool} sign -inFile {prog} -outFile {prog} -selfSign 1',
            env="conanbuild", ignore_errors=True,
        )
        self.run(f"chmod +x {prog}", env="conanbuild", ignore_errors=True)
        return r == 0

    def package(self):
        src = self.source_folder
        bin_dst = os.path.join(self.package_folder, "bin")
        lic_dst = os.path.join(self.package_folder, "licenses")
        # 只装静态链接的 run-init（自包含，不依赖 klibc 共享库）。
        copy(self, "run-init", os.path.join(src, "usr", "kinit", "run-init", "static"), bin_dst)
        prog = os.path.join(bin_dst, "run-init")
        os.chmod(prog, 0o755)
        # 许可证：klibc 本体 LICENSE（BSD/MIT + Linux 派生 GPL-2.0；run-init 源码为 MIT）。
        copy(self, "LICENSE", os.path.join(src, "usr", "klibc"), lic_dst)
        cc = self._compilers()["cc"]
        self._sign_elf(prog, self._tool(cc, "llvm-objcopy"), self._tool(cc, "binary-sign-tool"))

    def package_info(self):
        # application 包：只声明 bin/，无头文件与库。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
