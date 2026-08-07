#!/usr/bin/env python3
"""Conan recipe — cc65 2.19 (6502 C compiler suite).

cc65 is a C compiler suite for the 6502 microprocessor family, including
a C compiler (cc65), macro assembler (ca65), linker (ld65), library
archiver (ar65), and a compile-and-link driver (cl65). The tools run on
the HarmonyOS PC (aarch64) host and generate 6502 target code; they do
not execute 6502 code on the host.

Adaptation notes:
  - Build system: plain Makefile (no configure step).
  - The Makefile uses CC = $(CROSS_COMPILE)gcc; override with the
    Conan-provided compiler via make CC={cc} (R33).
  - Only the src/ directory (compiler tools) is built. libsrc/ (6502
    target libraries) requires running the just-built cc65 tools and
    is skipped in cross-compilation.
  - No external dependencies; self-contained build.
  - R32: settings.os supports both Linux and OHOS.
  - R33: compiler comes from Conan conf, no bare shell env vars.
  - R38: produces executables -> commands.json declared, cpp_info.bindirs set.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class Cc65Conan(ConanFile):
    name = "cc65"
    version = "2.19"
    description = "6502 C compiler suite — cross-development tools for 6502 microprocessors"
    license = "Zlib"
    homepage = "https://cc65.github.io/cc65/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: recipe must accept both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        # OHOS 适配版 Conan 不支持 tools.build:compiler_executables:c 形式的子键查询，
        # 需先用 dict 形式获取整个 compiler_executables，再 .get() 取单个编译器路径。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "ar")

        # Only build the compiler tools (src/). libsrc/ requires running
        # the just-built cc65 to compile 6502 target libraries, which is
        # not possible in cross-compilation. doc/ needs texinfo; samples/
        # needs running cc65. All skipped.
        # R9: Use -j1 (never -j$(nproc)).
        _src = f'"{self.source_folder}/src"'
        self.run(f"make -C {_src} bin CC={cc} AR={ar} -j1")

    def package(self):
        # Install built binaries from src/ to package bin/.
        # The src/Makefile install target copies ../bin/* to $(PREFIX)/bin/.
        _src = f'"{self.source_folder}/src"'
        self.run(f"make -C {_src} install PREFIX={self.package_folder}")

        # R7: Self-sign ELF binaries on OHOS for local execution.
        # OHOS requires ELF signatures; unsigned binaries get "Permission denied".
        if self.settings.os == "OHOS":
            bin_dir = os.path.join(self.package_folder, "bin")
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isdir(bin_dir) and os.path.isfile(sign_tool):
                for name in os.listdir(bin_dir):
                    bin_path = os.path.join(bin_dir, name)
                    if not os.path.isfile(bin_path):
                        continue
                    signed_path = f"{bin_path}.signed"
                    self.run(
                        f'{sign_tool} sign -inFile "{bin_path}"'
                        f' -outFile "{signed_path}"'
                        f' -selfSign 1 -signAlg SHA256withECDSA',
                        quiet=True
                    )
                    if os.path.isfile(signed_path):
                        os.replace(signed_path, bin_path)
                        os.chmod(bin_path, 0o755)

    def package_info(self):
        # cc65 produces executables (cc65, ca65, cl65, ld65, ar65, etc.)
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
