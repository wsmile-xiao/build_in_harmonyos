#!/usr/bin/env python3
"""Conan recipe — sonic 0.2.0 (speech speed-up/down library + CLI).

Sonic is a simple ANSI C library for speeding up or slowing down speech
(optimized for >2X speed-ups), used as a TTS back-end helper. Build system
is a plain Makefile (no configure/cmake): produces the `sonic` CLI (wave
speed/pitch/rate/volume tool), libsonic.so.0.2.0 (SONAME libsonic.so.0)
and libsonic.a.

No third-party dependency (pure ANSI C). OHOS adaptations:
- R33: compiler from GnuToolchain (never shell ${CC}); clang on OHOS.
- R9: make -j1.
- E077: sign the produced ELF binaries (sonic CLI + libsonic.so) so the
  OHOS kernel accepts them.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class SonicConan(ConanFile):
    name = "sonic"
    version = "0.2.0"
    description = "Sonic - simple algorithm for speeding up or slowing down speech"
    license = "Apache-2.0"
    homepage = "https://github.com/waywardgeek/sonic"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # R33: Use GnuToolchain to inject CC/CFLAGS from Conan profile
    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Makefile in the source folder; basic_layout uses a separate build dir
        # sonic 的 Makefile 硬编码 CC=gcc / AR=ar——OHOS 无 gcc，须显式覆盖
        # （R33：编译器从 Conan conf 拿，不用 shell 环境变量 ${CC}；
        # tools.build:compiler_executables 是 map，取 dict 后读 c/ar/ranlib）
        exe = self.conf.get("tools.build:compiler_executables") or {}
        cc = exe.get("c") or shutil.which("clang") or "/data/service/hnp/bin/clang"
        ar = exe.get("ar") or shutil.which("llvm-ar") or "llvm-ar"
        ranlib = exe.get("ranlib") or shutil.which("llvm-ranlib") or "llvm-ranlib"
        with chdir(self, self.source_folder):
            # R9: Always use -j1
            self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} -j1")

    def _sign_elf(self, path):
        """E077 四步签名：remove-section → (无修改) → sign → chmod a+x。"""
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            raise ConanInvalidConfiguration("需要 llvm-objcopy 与 binary-sign-tool 签名产物")
        self.run(f'"{objcopy}" --remove-section .codesign "{path}"', ignore_errors=True)
        self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        os.chmod(path, 0o755)

    def _is_elf(self, path):
        with open(path, "rb") as handle:
            return handle.read(4) == b"\x7fELF"

    def package(self):
        # CLI
        copy(self, "sonic", self.source_folder, os.path.join(self.package_folder, "bin"))
        # 头文件
        copy(self, "sonic.h", self.source_folder, os.path.join(self.package_folder, "include"))
        # 库：libsonic.so.0.2.0 + .so/.so.0 symlink + 静态库
        copy(self, "libsonic.so.0.2.0", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        for link in ("libsonic.so", "libsonic.so.0"):
            src_link = os.path.join(self.source_folder, link)
            dst_link = os.path.join(self.package_folder, "lib", link)
            if os.path.islink(src_link):
                if os.path.lexists(dst_link):
                    os.remove(dst_link)
                os.symlink("libsonic.so.0.2.0", dst_link)
        copy(self, "libsonic.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        # 签名（E077）：OHOS 内核拒绝未签名可执行文件/共享库
        for root, _, files in os.walk(self.package_folder):
            for entry in files:
                candidate = os.path.join(root, entry)
                if not (os.path.isfile(candidate) and not os.path.islink(candidate)):
                    continue
                if not self._is_elf(candidate):
                    continue
                if entry.endswith(".a"):
                    continue
                try:
                    self._sign_elf(candidate)
                except Exception as exc:
                    self.output.warning(f"sign failed for {candidate}: {exc}")

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["sonic"]
        self.cpp_info.bindirs = ["bin"]
