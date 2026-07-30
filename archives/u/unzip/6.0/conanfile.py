#!/usr/bin/env python3
"""Conan recipe for unzip 6.0 — Info-ZIP's decompression utility.

unzip uses a custom Makefile build system (unix/Makefile) with a configure
script (unix/configure) that detects platform features. No external dependencies.

On HarmonyOS (OHOS):
- /tmp is read-only, so TMPDIR must be set for configure tests (E002)
- HMDFS doesn't support hard links, so manual copy is used instead of make install
- ELF signing required for execution
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class UnzipConan(ConanFile):
    name = "unzip"
    version = "6.0"
    description = "Info-ZIP's decompression utility for ZIP format archives"
    license = "Info-ZIP"
    homepage = "https://infozip.sourceforge.net/UnZip.html"
    url = "https://infozip.sourceforge.net/UnZip.html"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        pass

    def requirements(self):
        pass  # unzip has no external dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _needs_ohos_workarounds(self):
        """Check whether OHOS-specific workarounds (TMPDIR, ELF signing) are needed.

        Returns True on both OHOS (target) and Linux (dev environment),
        since local development also requires these workarounds.
        R32: settings.os check must include both Linux and OHOS.
        """
        return self.settings.os in ("Linux", "OHOS")

    def _get_cc(self):
        # R33: Get compiler from Conan conf, not undefined shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("c") or "clang"

    def _sign_elf(self, path, src):
        """Sign ELF binary on OHOS for execution on HarmonyOS."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if Path(sign_tool).exists():
            self.run(f"{objcopy} --remove-section .codesign {path} || true", cwd=src)
            self.run(f"{sign_tool} sign -inFile {path} "
                     f"-outFile {path}.signed -selfSign 1", cwd=src)
            shutil.move(f"{path}.signed", path)
        else:
            self.output.warn(
                f"binary-sign-tool not found at {sign_tool}; "
                f"skipping ELF signing for {path}. "
                f"Binary may not be executable on OHOS target."
            )
        os.chmod(path, 0o755)

    def build(self):
        apply_conandata_patches(self)

        cc = self._get_cc()

        # E002: /tmp is read-only on OHOS, set TMPDIR for configure tests
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        # Build: make -f unix/Makefile generic CC={cc}
        # 'generic' target avoids x86 assembly, works on aarch64
        self.run(f"make -f unix/Makefile generic CC={cc} -j1", cwd=self.source_folder)

        # Sign ELF binaries on OHOS-compatible platforms
        if self._needs_ohos_workarounds():
            for binary in ["unzip", "funzip", "unzipsfx"]:
                binpath = os.path.join(self.source_folder, binary)
                if os.path.exists(binpath):
                    self._sign_elf(binpath, self.source_folder)

    def package(self):
        # Copy executables to bin/
        for binary in ["unzip", "funzip", "unzipsfx"]:
            src = os.path.join(self.source_folder, binary)
            if os.path.exists(src):
                copy(self, binary, self.source_folder, os.path.join(self.package_folder, "bin"))
                os.chmod(os.path.join(self.package_folder, "bin", binary), 0o755)

        # Copy zipgrep script from unix/
        zipgrep = os.path.join(self.source_folder, "unix", "zipgrep")
        if os.path.exists(zipgrep):
            copy(self, "zipgrep", os.path.join(self.source_folder, "unix"),
                 os.path.join(self.package_folder, "bin"))
            os.chmod(os.path.join(self.package_folder, "bin", "zipgrep"), 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
