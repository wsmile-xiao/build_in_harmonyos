#!/usr/bin/env python3
"""Conan recipe for ired 0.6 — a minimalistic commandline hex editor.

ired is a raw Makefile C project (no configure, no CMake) that builds two
executables (`ired` and `bdiff`) plus the `vired` shell wrapper. It is a CLI
tool package, so this recipe follows the raw-Makefile CLI pattern:
  - package_type = application, binaries installed to bin/
  - make invoked with the Conan-provided clang (R33: no bare ${CC})
  - OHOS package binaries self-signed (llvm-objcopy + binary-sign-tool)
  - software-level commands.json provided for R38/L0k
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class IredConan(ConanFile):
    name = "ired"
    version = "0.6"
    description = "Minimalistic commandline hexadecimal editor similar to radare"
    license = "MIT"
    homepage = "https://github.com/radare/ired"
    url = "https://github.com/radare/ired"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    _source_url = (
        "https://github.com/radare/ired/archive/refs/tags/0.6.tar.gz"
    )
    _source_sha256 = (
        "c15d37b96b1a25c44435d824bd7ef1f9aea9dc191be14c78b689d3156312d58a"
    )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ired requires a POSIX target (Linux or OHOS)"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        # Official GitHub tag archive; verified SHA256.
        get(
            self,
            url=self._source_url,
            sha256=self._source_sha256,
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc = compilers.get("c", "clang")
        # R9: -j1; R33: CC comes from Conan conf, never bare ${CC}.
        self.run(
            f"make CC={cc} -j1",
            cwd=self.source_folder,
        )

    def package(self):
        # Mirror the upstream `make install` binary layout but only the real
        # CLI tools: ired (hex editor) and bdiff (binary diff). The upstream
        # `vired` shell wrapper is excluded: it requires an interactive raw
        # terminal (stty raw + /dev/tty reads) and would hang the CI L2 smoke
        # test forever in headless OHOS CI workers.
        for name in ("ired", "bdiff"):
            copy(
                self,
                name,
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "bin"),
                keep_path=False,
            )
        copy(
            self,
            "*.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )

        for name in ("ired", "bdiff"):
            path = os.path.join(self.package_folder, "bin", name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
                self._sign_ohos_binary(path)

    def _sign_ohos_binary(self, path):
        """HarmonyOS rejects unsigned ELF binaries (PermissionError) at
        execution time; add a .codesign section during packaging."""
        if str(self.settings.os) != "OHOS":
            return

        signer = self.conf.get(
            "user.ohos:sign_tool",
            default="",
            check_type=str,
        )
        signer = (
            signer
            or os.environ.get("OHOS_SIGN_TOOL", "")
            or shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool is unavailable; skipping OHOS ELF signing"
            )
            return

        objcopy = self.conf.get(
            "user.ohos:objcopy",
            default="",
            check_type=str,
        )
        objcopy = (
            objcopy
            or os.environ.get("OHOS_OBJCOPY", "")
            or shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        if os.path.isfile(objcopy):
            self.run(
                f'"{objcopy}" --remove-section .codesign "{path}"',
                ignore_errors=True,
            )

        signed = f"{path}.signed"
        self.run(
            f'"{signer}" sign -inFile "{path}" '
            f'-outFile "{signed}" -selfSign 1'
        )
        if not os.path.isfile(signed):
            raise ConanException(f"binary-sign-tool produced no output for {path}")
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )