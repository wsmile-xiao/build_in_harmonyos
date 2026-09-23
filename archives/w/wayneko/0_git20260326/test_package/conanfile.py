#!/usr/bin/env python3
"""Conan test_package for wayneko — executes the INSTALLED binary and asserts
on real, observable behaviour (R34: the test genuinely exercises the package),
plus an OHOS-specific consumer test (test_wayneko_ohos.c) that asserts platform
properties of the shipped artifact (鸿蒙特有测试 / rule-12 要求).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException


class WaynekoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        # R33: compiler from the Conan toolchain conf, never a bare ${CC}.
        exes = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict)
        cc = exes.get("c")
        if not cc:
            cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        return cc

    def build(self):
        # OHOS-specific consumer test: only built for the OHOS target.
        if str(self.settings.os) != "OHOS":
            return
        cc = self._cc()
        src = os.path.join(self.source_folder, "test_wayneko_ohos.c")
        out = os.path.join(self.build_folder, "test_wayneko_ohos")
        self.run(f'"{cc}" -O2 -std=c11 -o "{out}" "{src}"', env="conanbuild")
        self.output.info("wayneko: built OHOS-specific consumer test")
        self._sign_ohos_elf(out)

    @staticmethod
    def _sign_ohos_elf(path):
        """Self-sign the freshly built OHOS test binary (cubature precedent).

        OHOS may refuse to execve an unsigned ELF. Freshly compiled binaries in
        the build folder usually execute fine, but signing removes the doubt on
        stricter workers; if the signing tools are absent we run unsigned.
        """
        if not os.path.isfile(path):
            raise ConanException(f"Missing OHOS consumer executable: {path}")
        signer = shutil.which("binary-sign-tool") or \
            "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or \
            "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            self.output.warning(
                "wayneko: OHOS signing tools not found — running test unsigned")
            return
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       check=True, timeout=30)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                        "-selfSign", "1"], check=True, timeout=60)
        os.chmod(path, (os.stat(path).st_mode & 0o777) | 0o055)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test.sh")
        # Runs wayneko from the installed package bin/ (conanrun env) and
        # asserts real exit codes / error strings — not a stub.
        self.run(f'{bash} "{script}"', env="conanrun")

        if str(self.settings.os) == "OHOS":
            exe = os.path.join(self.build_folder, "test_wayneko_ohos")
            pkg = self.dependencies["wayneko"].package_folder
            binary = os.path.join(pkg, "bin", "wayneko")
            if not os.path.isfile(exe):
                raise ConanException(f"Missing OHOS consumer test binary: {exe}")
            if not os.path.isfile(binary):
                raise ConanException(f"Missing installed wayneko binary: {binary}")
            self.run(f'"{exe}" "{binary}"', env="conanrun")
