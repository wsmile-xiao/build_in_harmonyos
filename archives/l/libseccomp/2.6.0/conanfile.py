#!/usr/bin/env python3
"""Conan recipe — libseccomp 2.6.0 (enhanced seccomp library).

Build system: autotools
Source: https://github.com/seccomp/libseccomp/releases/download/v2.6.0/libseccomp-2.6.0.tar.gz

Rules compliance:
  R1:  Minimal configure args (--prefix handled by AutotoolsToolchain)
  R26: System same-name lib (libseccomp.z.so exists in /system/lib64 on OHOS)
       -> build static via --disable-shared
  R27: No external dependencies (requirements() is empty)
  R32: settings.os validated with in ("Linux", "OHOS")
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibseccompConan(ConanFile):
    name = "libseccomp"
    version = "2.6.0"
    description = "Enhanced seccomp (mode 2) helper library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/seccomp/libseccomp"
    url = ""  # CI fills this

    # R26: libseccomp is a system same-name library on OHOS (/system/lib64/
    # has libseccomp.z.so) — build static to avoid polluting /lib, /lib64
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: No external dependencies — requirements() is empty
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os must be checked with in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libseccomp 2.6.0 only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System same-name library must be static
        tc.configure_args.append("--disable-shared")
        # Python bindings need cython — not available on OHOS
        tc.configure_args.append("--disable-python")
        # OHOS: config.guess can't detect HarmonyOS (uname -s=HarmonyOS
        # not in its table) AND its temp-file probe is blocked by the
        # security framework (Permission denied on $HOME/.cache/tmp) —
        # pass explicit --build/--host to skip config.guess entirely
        # (same as audit precedent; config.sub patched to accept ohos)
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # R8: Define __OHOS__ so #ifdef __OHOS__ guards in patches are active
        tc.extra_defines.append("__OHOS__")
        tc.generate()
        # gperf is REQUIRED to generate syscall tables (AC_CHECK_TOOL).
        # It is not in the default PATH on OHOS — prepend its dir so
        # configure can find it (same pattern as libsoup llvm/bin injection).
        for _cand in ("/data/service/hnp/bin/gperf",
                      "/storage/Users/currentUser/.local/bin/gperf"):
            if os.path.isfile(_cand):
                _gperf_dir = os.path.dirname(_cand)
                if _gperf_dir not in os.environ.get("PATH", ""):
                    self.buildenv_info.prepend("PATH", _gperf_dir)
                break
        # configure 编译器测试 = clang 调 SDK lld 链接测试程序，而 SDK
        # lld 的 DT_NEEDED 含 libxml2.so.16（在 llvm/lib/）——CI worker
        # 上若 LLVM lib 不在 loader 默认搜索路径，lld 运行即失败 →
        # "C compiler cannot create executables"（picotool 先例）。
        # 用 Python os.path.realpath（不依赖外部 realpath 命令，CI worker
        # 原始 PATH 无其所在目录——libsoup/atlas 同款教训）推导 SDK llvm
        # lib 并注入 LD_LIBRARY_PATH。
        _llvm_lib = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.realpath("/data/service/hnp/bin/clang"))),
            "lib")
        if os.path.isdir(_llvm_lib):
            self.buildenv_info.prepend("LD_LIBRARY_PATH", _llvm_lib)

    def build(self):
        # OHOS: umask 000 needed for config.status temp dir creation
        # (security framework blocks 077-created dirs in $HOME)
        os.umask(0)
        apply_conandata_patches(self)
        # OHOS: Patch configure to use umask 000 for config.status temp dirs
        # (Autoconf generates "umask 077" which fails on OHOS)
        self.run("sed -i 's/umask 077/umask 000/g' configure",
                 cwd=self.source_folder)
        # Autotools.configure() sources Conan environment files
        # (CFLAGS with -D__OHOS__, PATH with gperf dir, etc.)
        autotools = Autotools(self)
        autotools.configure()
        # OHOS: make -j1 (mkfifo/jobserver not supported on OHOS)
        self.run("make -j1")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # tools/ binaries (scmp_sys_resolver etc.) are not part of the
        # library package — drop them, keep lib + headers only
        self.run(f"rm -rf {os.path.join(self.package_folder, 'bin')}")

    def package_info(self):
        self.cpp_info.libs = ["seccomp"]
        self.cpp_info.includedirs = ["include"]
