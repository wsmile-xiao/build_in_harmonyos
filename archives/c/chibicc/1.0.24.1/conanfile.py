#!/usr/bin/env python3
"""Conan recipe for chibicc 1.0.24.1.

chibicc is a small self-contained C compiler. This packaged build exposes the
compiler executable and its bundled headers; it does not provide a linkable
library to consumers.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ChibiccConan(ConanFile):
    name = "chibicc"
    version = "1.0.24.1"
    description = "Small self-contained C compiler"
    license = "MIT"
    homepage = "https://github.com/rui314/chibicc"
    url = "https://github.com/rui314/chibicc"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return compilers.get("c") or "clang"

    def _openssl_flags(self):
        openssl = self.dependencies["openssl"].cpp_info
        cflags = [f"-I{d}" for d in openssl.includedirs]
        ldflags = [f"-L{d}" for d in openssl.libdirs]
        return " ".join(cflags), " ".join(ldflags)

    def _linker_flag(self):
        if self.settings.os == "OHOS" and os.path.exists("/data/service/hnp/bin/ld.bfd"):
            return "-fuse-ld=/data/service/hnp/bin/ld.bfd"
        return ""

    def _compile_flags(self):
        openssl_cflags, openssl_ldflags = self._openssl_flags()
        cflags = " ".join(
            flag
            for flag in [
                "-std=c11",
                "-g",
                "-fno-common",
                "-Wall",
                "-Wno-switch",
                '-DPREFIX=\\"/usr/local\\"',
                '-DGCC_VERSION=\\"0\\"',
                openssl_cflags,
            ]
            if flag
        )
        ldflags = " ".join(
            flag
            for flag in [
                self._linker_flag(),
                openssl_ldflags,
                "-lcrypto",
            ]
            if flag
        )
        return cflags, ldflags

    def _sign_binary(self, binary_path):
        if self.settings.os != "OHOS" or not os.path.isfile(binary_path):
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool):
            self.output.warning("binary-sign-tool not found; skip OHOS ELF signing")
            return
        if os.path.isfile(objcopy):
            self.run(f'"{objcopy}" --remove-section .codesign "{binary_path}" 2>/dev/null || true')
        signed_path = f"{binary_path}.signed"
        self.run(
            f'"{sign_tool}" sign -inFile "{binary_path}" '
            f'-outFile "{signed_path}" -selfSign 1',
            quiet=True,
        )
        if os.path.isfile(signed_path):
            os.replace(signed_path, binary_path)
            os.chmod(binary_path, 0o755)

    def build(self):
        apply_conandata_patches(self)
        cflags, ldflags = self._compile_flags()
        self.run(
            f'"{self._cc()}" {cflags} -o chibicc *.c {ldflags}',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        license_dir = os.path.join(self.package_folder, "licenses")
        copy(self, "chibicc", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "*", src=os.path.join(self.source_folder, "include"), dst=os.path.join(bin_dir, "include"))
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include", "x86_64-linux-gnu", "chibicc"),
        )
        copy(self, "LICENSE", src=self.source_folder, dst=license_dir, keep_path=False)
        self._sign_binary(os.path.join(bin_dir, "chibicc"))

    def package_info(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", bin_dir)
