#!/usr/bin/env python3
"""Conan test_package — srecord 1.65.0

Runs smoke_test.sh on native aarch64. On x86_64 SDK hosts targeting OHOS
aarch64, verifies the three CLI tools exist and are aarch64 ELF.

On native OHOS, re-signs package binaries before smoke if binary-sign-tool
is available (E077/E082), so Operation not permitted does not fail the test.
"""
import glob
import os
import platform
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class SrecordTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _foreign_aarch64(self):
        target = str(self.settings.arch)
        if target not in ("armv8", "armv8.3", "armv8.7", "arm64"):
            return False
        return platform.machine() not in ("aarch64", "arm64")

    def _sign_elf(self, path):
        """E077: resign ELF so OHOS kernel allows execution."""
        if not path or not os.path.isfile(path) or os.path.islink(path):
            return
        try:
            with open(path, "rb") as fh:
                if fh.read(4) != b"\x7fELF":
                    return
        except OSError:
            return

        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool) or not os.path.isfile(objcopy):
            return

        tmp_signed = path + ".signed"
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=False,
            capture_output=True,
        )
        r = subprocess.run(
            [
                sign_tool,
                "sign",
                "-inFile",
                path,
                "-outFile",
                tmp_signed,
                "-selfSign",
                "1",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not os.path.isfile(tmp_signed):
            self.output.warning(
                f"ELF sign failed for {os.path.basename(path)}: {r.stderr or r.stdout}"
            )
            return
        os.replace(tmp_signed, path)
        os.chmod(path, 0o755)
        self.output.info(f"ELF signed for smoke: {os.path.basename(path)}")

    def _ensure_signed(self, bindir, tools):
        for path in tools.values():
            self._sign_elf(path)
        for so in sorted(glob.glob(os.path.join(bindir, "lib*.so*"))):
            self._sign_elf(so)

    def test(self):
        pkg = self.dependencies["srecord"].package_folder
        bindir = os.path.join(pkg, "bin")
        tools = {
            "srec_cat": os.path.join(bindir, "srec_cat"),
            "srec_cmp": os.path.join(bindir, "srec_cmp"),
            "srec_info": os.path.join(bindir, "srec_info"),
        }
        for path in tools.values():
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(f"missing tool: {path}")

        if self._foreign_aarch64():
            for path in tools.values():
                out = subprocess.check_output(["file", path], text=True)
                if "ARM aarch64" not in out and "aarch64" not in out:
                    raise ConanInvalidConfiguration(f"not aarch64 ELF: {out.strip()}")
            self.output.info(
                "foreign aarch64 host: verified srec_* aarch64 ELF; "
                "skipped smoke_test.sh execution"
            )
            return

        # Native host (Linux or OHOS aarch64): ensure binaries are signed when
        # the OHOS signer is present, then run consumer smoke.
        self._ensure_signed(bindir, tools)

        # OHOS conanrun often omits LD_LIBRARY_PATH for transitive deps.
        lib_dirs = []
        for name in ("libgcrypt", "libgpg-error"):
            if name in self.dependencies:
                for libdir in self.dependencies[name].cpp_info.libdirs:
                    if libdir not in lib_dirs:
                        lib_dirs.append(libdir)
        # Staged copies next to bin/ (from package()) also cover loader lookup.
        lib_dirs.insert(0, bindir)
        ld = os.pathsep.join(lib_dirs)
        script = os.path.join(self.recipe_folder, "smoke_test.sh")
        # E002: prefer package-local writable temp (OHOS /tmp is read-only).
        smoke_tmp = os.path.join(pkg, "_smoke_tmp")
        os.makedirs(smoke_tmp, exist_ok=True)
        self.run(
            f'TMPDIR="{smoke_tmp}" SRECORD_SMOKE_TMP="{smoke_tmp}" '
            f'LD_LIBRARY_PATH="{ld}:${{LD_LIBRARY_PATH:-}}" '
            f'bash "{script}" "{tools["srec_cat"]}" "{tools["srec_cmp"]}" "{tools["srec_info"]}"',
            env="conanrun",
        )
