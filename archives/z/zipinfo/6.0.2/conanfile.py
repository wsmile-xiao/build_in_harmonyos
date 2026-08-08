#!/usr/bin/env python3
"""Conan recipe for zipinfo 6.0.2 — Info-ZIP's ZIP archive listing utility.

zipinfo is part of the Info-ZIP unzip source tree (unzip60.tar.gz). It uses
the custom unix/Makefile build system; on Unix zipinfo is built from the same
objects as unzip (the Makefile's `zipinfo` target links unzip → zipinfo).

On HarmonyOS (OHOS):
- /tmp is read-only, so TMPDIR must be set for configure tests (E002)
- HMDFS doesn't support hard links, so a copy is used instead of `ln`
- ELF signing required for execution
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class ZipinfoConan(ConanFile):
    name = "zipinfo"
    version = "6.0.2"
    description = "Info-ZIP's ZIP archive listing utility"
    license = "Info-ZIP"
    homepage = "https://infozip.sourceforge.net/UnZip.html"
    url = "https://infozip.sourceforge.net/UnZip.html"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        pass

    def requirements(self):
        pass  # zipinfo has no external dependencies

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

        # zipinfo: the Makefile's zipinfo target uses `ln unzip zipinfo`,
        # but HMDFS doesn't support hard links → copy instead (R5).
        unzip_bin = os.path.join(self.source_folder, "unzip")
        zipinfo_bin = os.path.join(self.source_folder, "zipinfo")
        if os.path.exists(unzip_bin) and not os.path.exists(zipinfo_bin):
            shutil.copy2(unzip_bin, zipinfo_bin)

        # Sign ELF binary on OHOS-compatible platforms
        if self._needs_ohos_workarounds():
            self._sign_elf(zipinfo_bin, self.source_folder)

    def package(self):
        # Copy zipinfo executable to bin/
        src = os.path.join(self.source_folder, "zipinfo")
        if os.path.exists(src):
            copy(self, "zipinfo", self.source_folder, os.path.join(self.package_folder, "bin"))
            os.chmod(os.path.join(self.package_folder, "bin", "zipinfo"), 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
