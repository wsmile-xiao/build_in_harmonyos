#!/usr/bin/env python3
"""Consumer test for slicot/5.9.1.

The assertions live in test_slicot.py (a real Fortran program is compiled and
run against the packaged archive) so the package ships a test source file
recognised by CI L0c; conanfile.py alone does not count.
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run


class SlicotTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("blas/3.12.1")
        self.requires("lapack/3.12.1")

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def test(self):
        if not can_run(self):
            return
        slicot = self.dependencies["slicot"].package_folder
        blas = self.dependencies["blas"].package_folder
        lapack = self.dependencies["lapack"].package_folder
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        sdk = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm"))[-1]

        env = {
            "SLICOT_FLANG_BIN": os.path.join(flang_pkg, "bin", "flang"),
            "SLICOT_FLANG_LIB": os.path.join(flang_pkg, "lib"),
            "SLICOT_SDK_LIB": os.path.join(sdk, "lib", "aarch64-linux-ohos"),
            "SLICOT_SYSROOT": os.path.join(sdk, "..", "sysroot"),
            "SLICOT_RESOURCE_DIR": os.path.join(sdk, "lib", "clang", "15.0.4"),
            "LD_LIBRARY_PATH": ":".join([
                os.path.join(sdk, "lib"),
                os.path.join(flang_pkg, "lib"),
                "/system/lib64",
            ]),
            "PATH": os.environ.get("PATH", ""),
        }
        script = os.path.join(self.source_folder, "test_slicot.py")
        exports = []
        for k, v in env.items():
            exports.append('export %s="%s"' % (k, v))
        cmd = ("%s && %s -E \"%s\" \"%s\" \"%s\" \"%s\""
               % (";".join(exports), self._python(), script,
                  os.path.join(slicot, "lib", "libslicot.a"),
                  os.path.join(blas, "lib", "libblas.a"),
                  os.path.join(lapack, "lib", "liblapack.a")))
        self.run(cmd)

    @staticmethod
    def _python():
        import sys
        import shutil
        return shutil.which("python3") or sys.executable
