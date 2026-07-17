#!/usr/bin/env python3
"""Conan test_package - OpenFst 1.8.4."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class OpenfstTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["openfst"]
        fstcompile = os.path.join(dep.package_folder, "bin", "fstcompile")
        header = os.path.join(dep.package_folder, "include", "fst", "fstlib.h")
        lib_dir = os.path.join(dep.package_folder, "lib")
        lib_candidates = [
            os.path.join(lib_dir, name)
            for name in ("libfst.so", "libfst.dylib", "libfst.a")
        ]
        libfst = next((path for path in lib_candidates if os.path.exists(path)), lib_candidates[0])

        if not can_run(self):
            for path in (fstcompile, header, libfst):
                if not os.path.exists(path):
                    raise Exception(f"Missing packaged artifact: {path}")
            self.output.info("Cross-building; file layout check completed")
            return

        bash = shutil.which("bash") or os.environ.get("CONFIG_SHELL")
        if not bash:
            raise Exception("bash not found in PATH and CONFIG_SHELL is not set; cannot run test script")
        script = os.path.join(self.source_folder, "check_openfst.sh")
        self.run(
            f"{shlex.quote(bash)} {shlex.quote(script)} {shlex.quote(fstcompile)} "
            f"{shlex.quote(header)} {shlex.quote(libfst)}",
            env="conanrun",
        )
