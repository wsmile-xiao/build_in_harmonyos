#!/usr/bin/env python3
"""Conan recipe for picolibc 1.8.11 — 嵌入式 bare-metal C 库（libc + libm），HarmonyOS PC aarch64。

picolibc 是 Keith Packard 维护、基于 newlib 重构的最小 C 库，面向嵌入式 / RTOS / 裸机
（QEMU semihosting、Zephyr 等），使用 Meson 构建（要求 >= 0.61）。适配要点：

- **bare-metal 自举**：picolibc 是 libc 本体，编译时用 ``-nostdlib``（不链接宿主 musl），
  因此不能用 Conan 标准 MesonToolchain（它会假设标准交叉编译 + 宿主 libc）。改为手写
  Meson cross file，设置 ``skip_sanity_check=true``（-nostdlib 产物无法在构建机运行）。
- **clang 无 multilib**：上游 doc 明确 clang 不支持 built-in multilib，且 ``--print-multi-lib``
  对 clang 无效，必须 ``-Dmultilib=false``。
- **运行时库**：OHOS clang 无 libgcc，用 compiler-rt builtins（``libclang_rt.builtins-*.a``），
  通过 cross file 的 ``librt`` external property 注入（picolibc meson.build 会读取）。
- **库命名冲突**：上游产物 ``libc.a``（1.8.11 起 libm 已合并进 libc，无独立 libm.a）
  与系统 musl 的 ``-lc`` 同名，package 时重命名为 ``libpicolibc.a``（同 klibc 先例）。
- **specs 不安装**：``-Dspecsdir=none`` 避免 picolibc 探测 GCC 安装目录（OHOS clang 无该目录）。

产物：静态库 libpicolibc.a（libc+libm）/ libcrt0.a / libsemihost.a、crt0*.o、
picolibc.h 头文件、picolibc.ld 链接脚本、licenses。
"""
import os
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


class PicolibcConan(ConanFile):
    name = "picolibc"
    version = "1.8.11"
    description = "picolibc — a C library for small embedded systems (libc + libm)"
    license = "BSD-3-Clause"
    homepage = "https://keithp.com/picolibc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # 核心产物是静态库（libc.a，含 libc+libm + crt0）；用 static-library 避免 Conan 2.x
    # 对 library 强制要求 shared option（同 klibc 先例）。
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    # conan arch -> picolibc host_machine.cpu_family
    _CPU_FAMILY_MAP = {
        "armv8": "aarch64",
        "armv7": "arm",
        "armv6": "arm",
        "x86_64": "x86_64",
        "x86": "x86",
        "riscv64": "riscv",
    }

    def _cpu_family(self):
        return self._CPU_FAMILY_MAP.get(str(self.settings.arch), str(self.settings.arch))

    def validate(self):
        if str(self.settings.arch) not in self._CPU_FAMILY_MAP:
            raise ConanInvalidConfiguration(
                f"picolibc/{self.version} arch {self.settings.arch} 未在适配映射中 "
                f"(支持: {', '.join(sorted(self._CPU_FAMILY_MAP))})"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libc 本体，零外部 Conan 库依赖；仅构建期依赖 meson/ninja/clang + compiler-rt。
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---- 工具链探测（R33：从 conf 取编译器，不从 shell 环境变量） ----

    def _compilers(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return {
            "cc": compilers.get("c", "clang"),
            "cxx": compilers.get("cpp", "clang++"),
        }

    def _tool(self, cc, name):
        """从 CC 同目录推导 llvm-* 工具完整路径（PATH 可能不含 hnp/bin）。"""
        cc_dir = os.path.dirname(cc)
        if cc_dir:
            return os.path.join(cc_dir, name)
        return name

    def _find_runtime_lib(self, cc):
        """返回 compiler-rt builtins 完整路径（OHOS clang 无 libgcc）。

        用 ``-print-libgcc-file-name``（clang 下返回 libclang_rt.builtins-*.a 路径），
        与 klibc 先例一致。clang 默认 target 即 aarch64-unknown-linux-ohos，
        无需显式 --target（3 段 triplet 会被 clang 歧义解析为 vendor）。
        """
        try:
            out = subprocess.check_output(
                [cc, "-print-libgcc-file-name"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if out and os.path.isfile(out):
                return out
        except Exception:
            pass
        return None

    def generate(self):
        """手写 Meson cross file（bare-metal 自举，标准 MesonToolchain 不适用）。"""
        cc = self._compilers()["cc"]
        tools = {
            "ar": self._tool(cc, "llvm-ar"),
            "ranlib": self._tool(cc, "llvm-ranlib"),
            "nm": self._tool(cc, "llvm-nm"),
            "strip": self._tool(cc, "llvm-strip"),
        }
        runtime_lib = self._find_runtime_lib(cc)
        cpu_family = self._cpu_family()

        # clang 默认 target 即 aarch64-unknown-linux-ohos，无需 --target；
        # -nostdlib/-fno-common 与上游 doc/build.md 的 cross file 示例一致。
        c_args = ["-nostdlib", "-fno-common"]

        # nm 会触发 picolibc 的 scripts/duplicate-names 重复符号质量检查，但该脚本在
        # HMDFS 上无执行位（ninja 直接执行报 Permission denied exit 126），已用 patch
        # 0001 禁用 check_duplicate_names（该检查非构建/功能必需）。此处仍提供 nm，
        # 保持 cross file 完整（find_program('nm', required:false) 能找到工具）。
        lines = [
            "[binaries]",
            "c = '%s'" % cc,
            "ar = '%s'" % tools["ar"],
            "ranlib = '%s'" % tools["ranlib"],
            "nm = '%s'" % tools["nm"],
            "strip = '%s'" % tools["strip"],
            "",
            "[host_machine]",
            "system = 'unknown'",
            "cpu_family = '%s'" % cpu_family,
            "cpu = '%s'" % cpu_family,
            "endian = 'little'",
            "",
            "[built-in options]",
            "c_args = [%s]" % ", ".join("'%s'" % a for a in c_args),
            "",
            "[properties]",
            "skip_sanity_check = true",
        ]
        if runtime_lib:
            lines.append("librt = '%s'" % runtime_lib)
        cross_file = os.path.join(self.generators_folder, "picolibc-cross.ini")
        with open(cross_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        self.output.info("picolibc cross file written: %s" % cross_file)

    def build(self):
        apply_conandata_patches(self)

        cross_file = os.path.join(self.generators_folder, "picolibc-cross.ini")
        build_dir = os.path.join(self.build_folder, "build")

        opts = [
            "-Dmultilib=false",            # clang 无 built-in multilib（上游 doc 明确）
            "-Dtests=false",               # 上游测试为 bare-metal semihosting 测试，需 qemu/FVP，本轮不运行
            "-Dspecsdir=none",             # 不安装 .specs 到 GCC 目录（OHOS clang 无该目录）
            "-Dprefix=/",                  # 用 --destdir 重定向到 package_folder（同 glib）
            "-Dincludedir=include",
            "-Dlibdir=lib",
            "-Dbuildtype=release",         # 匹配 Conan build_type=Release
            # clang 的 aarch64-linux-ohos target 将 _Thread_local errno 编译为 emulated TLS
            # （__emutls_v.errno），链接时经 compiler-rt emutls 引入 pthread_* 依赖（裸机无 pthread）。
            # 用全局 errno 规避 emutls（sys/errno.h 的 __GLOBAL_ERRNO 宏）。
            "-Dnewlib-global-errno=true",
        ]
        self.run(
            'meson setup --cross-file "%s" "%s" "%s" %s'
            % (cross_file, build_dir, self.source_folder, " ".join(opts)),
            env="conanbuild",
        )
        self.run('meson compile -C "%s"' % build_dir, env="conanbuild")

    def package(self):
        build_dir = os.path.join(self.build_folder, "build")
        # meson install --destdir 把 prefix=/ 的内容装到 package_folder（include/ + lib/）。
        self.run(
            'meson install -C "%s" --destdir "%s"' % (build_dir, self.package_folder),
            env="conanbuild",
        )

        lib_dst = os.path.join(self.package_folder, "lib")
        # libc.a 与系统 musl 的 -lc 同名，重命名避免消费者误链（同 klibc）。
        # 1.8.11 起 libm 已合并进 libc.a（meson.build libnames=['cpart','mpart'] → static_library('c')），
        # 无独立 libm.a。
        src = os.path.join(lib_dst, "libc.a")
        if os.path.isfile(src):
            os.rename(src, os.path.join(lib_dst, "libpicolibc.a"))
        else:
            self.output.warning("expected library not found: libc.a")

        # 许可证（COPYING.picolibc 为 SPDX 格式的完整许可清单）。
        copy(self, "COPYING.picolibc", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # picolibc 头文件：include/（通用） + include/machine（架构相关，已由 meson install 安装）。
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # picolibc 是 libc 本体，消费方式特殊：-nostdlib + crt0.o + libpicolibc.a + compiler-rt
        # （见 test_package），故只声明库名，消费者按完整路径/start-group 链接。
        self.cpp_info.libs = ["picolibc"]
