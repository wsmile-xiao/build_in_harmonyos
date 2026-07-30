#!/usr/bin/env python3
"""Conan recipe — pixiewps 1.4.2 (Makefile)

Pixiewps is an offline WPS brute-force utility that exploits low-entropy PRNGs.
Crypto libraries (libtomcrypt + tomsfastmath) are bundled in the source tree.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PixiewpsConan(ConanFile):
    name = "pixiewps"
    version = "1.4.2"
    description = "Offline WPS brute-force utility exploiting low-entropy PRNGs (pixie-dust attack)"
    license = "GPL-3.0"
    homepage = "https://github.com/wiire-a/pixiewps"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        self.run(f'make CC="{cc}" -j1')

    def package(self):
        copy(self, "pixiewps", dst=os.path.join(self.package_folder, "bin"), src=".", keep_path=False)
        copy(self, "pixiewps.1", dst=os.path.join(self.package_folder, "share", "man", "man1"), src=".", keep_path=False)

        # R38/E082: HarmonyOS requires ELF signing before a binary can execute.
        bin_path = os.path.join(self.package_folder, "bin", "pixiewps")
        if os.path.exists(bin_path) and self.settings.os in ("Linux", "OHOS"):
            self._sign_elf(bin_path)

    def _sign_elf(self, path):
        """Sign an ELF binary for HarmonyOS execution (R38/E082)."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(sign_tool) and os.path.isfile(objcopy)):
            self.output.warning("ELF signing tools not found; skipping (CI worker will sign).")
            return
        # Remove any existing .codesign section (may not exist on fresh build).
        objcopy_result = subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=False, capture_output=True, text=True, timeout=10,
        )
        if objcopy_result.returncode != 0:
            detail = (objcopy_result.stderr or objcopy_result.stdout).strip()
            self.output.warning(
                f"Failed to remove .codesign section (rc={objcopy_result.returncode}): {detail}"
            )
        tmp = path + ".signed.tmp"
        r = subprocess.run(
            [sign_tool, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0 and os.path.exists(tmp):
            os.replace(tmp, path)
            os.chmod(path, 0o755)
        else:
            detail = (r.stderr or r.stdout).strip()
            raise RuntimeError(
                f"ELF signing failed for {os.path.basename(path)} "
                f"(rc={r.returncode}): {detail}"
            )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
