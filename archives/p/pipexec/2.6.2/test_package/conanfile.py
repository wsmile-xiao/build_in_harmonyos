#!/usr/bin/env python3
"""Conan test_package — pipexec 2.6.2 (Conan L1 official test).

Verifies the *installed* pipexec binary, not the build tree, by really
executing it (R34: no stub test).  Structure follows the repository
test_package contract enforced by CI L0a-L0e:

  * conanfile.py  — this file (L0b); test() calls self.run() (L0d)
  * pipehelper.c  — test source (L0c), compiled for the target by CMake
  * smoke.sh      — 11 consumer assertions driven through self.run()
  * MANIFEST.yml  — upstream test declaration (L0e)

pipexec execs its children by absolute path (execv, not execvp), so the test
supplies its own helper processes: pipehelper.c is built by CMake, and on OHOS
copied to a writable non-HMDFS directory and self-signed, because a freshly
linked ELF cannot be executed on the device without a .codesign section
(knowledge E360 family; the same staging pattern as
archives/l/libxext/1.3.7/test_package and archives/p/pipemeter/1.1.5).
"""

import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

HELPER = "pipehelper"


class PipexecTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    # CMakeToolchain is what CMake needs to configure; CMakeDeps is not needed
    # because pipexec is an application package that exports no CMake targets.
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "pipehelper.c", "smoke.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "SKIPPED: pipexec was cross built and cannot run on this host")
            return

        pipexec = os.path.join(
            self.dependencies["pipexec"].package_folder, "bin", "pipexec")
        if not os.path.isfile(pipexec):
            raise ConanException(f"pipexec binary missing from the package: {pipexec}")

        helper_built = os.path.join(self.cpp.build.bindir, HELPER)
        if not os.path.isfile(helper_built):
            raise ConanException(f"test helper missing: {helper_built}")

        runtime_dir = None
        try:
            if str(self.settings.os) == "OHOS":
                runtime_dir = tempfile.mkdtemp(
                    prefix="pipexec-test-", dir="/data/storage/el2/base/cache")
                helper = os.path.join(runtime_dir, HELPER)
                shutil.copy2(helper_built, helper)
                self._sign_ohos_elf(helper)
                workdir = os.path.join(runtime_dir, "work")
                os.makedirs(workdir, exist_ok=True)
            else:
                helper = helper_built
                workdir = tempfile.mkdtemp(prefix="pipexec-test-work-")

            shell = self._find_shell()
            smoke = os.path.join(self.source_folder, "smoke.sh")
            # All assertions live in smoke.sh and exit non-zero on failure, so
            # conan judges the test from the command exit status alone.
            self.run(
                f'"{shell}" "{smoke}" "{pipexec}" "{helper}" "{workdir}"',
                env="conanrun")
        finally:
            if runtime_dir is not None:
                shutil.rmtree(runtime_dir, ignore_errors=True)

    def _find_shell(self):
        for candidate in (os.environ.get("CONFIG_SHELL"),
                          shutil.which("bash"),
                          "/data/service/hnp/bin/bash"):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "/bin/sh"

    def _sign_ohos_elf(self, path):
        """OHOS refuses to execute an ELF without a .codesign section."""
        signer = shutil.which("binary-sign-tool") or \
            "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or \
            "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = f"{path}.signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary,
             "-selfSign", "1"],
            check=True, timeout=120)
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True, capture_output=True, text=True, timeout=60).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed helper has invalid .codesign: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)
