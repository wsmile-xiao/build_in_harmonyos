#!/usr/bin/env python3
"""Conan test_package — f3d 3.5.0

R34: the test actually EXECUTES the packaged binary.
`f3d --version` is run and its exit code + version output are verified
by test_f3d.cpp. Executing the binary exercises the full runtime
contract: dynamic loading of libf3d.so and every VTK shared library
through the OHOS loader.

OHOS specifics handled here:
- the packaged f3d binary (and VTK libs) lose their .codesign sidecar
  when conan copies them into the package cache; re-sign with
  binary-sign-tool -selfSign before executing (same as the recipe's
  upstream-test step)
- runtime libc++_shared.so only lives in /system/lib64
"""
import os
import shlex
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class F3DTestPackage(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _resign(self, path):
        """Re-sign an ELF file so the OHOS loader will execute it.

        HMDFS keeps the code signature as sidecar data which plain file
        copies (conan package cache) do not preserve; binary-sign-tool
        regenerates a local self-signature.
        Returns True if the file is signed/re-signed or signing is not
        needed (non-OHOS host / tool absent -> False only when the tool
        is missing on an OHOS host).
        """
        if self.settings.os != "OHOS":
            return True
        tool = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(tool):
            return False
        try:
            r = subprocess.run(
                [tool, "sign", "-selfSign", "1",
                 "-inFile", path, "-outFile", path + ".signed"],
                capture_output=True, timeout=120)
            if r.returncode == 0 and os.path.isfile(path + ".signed"):
                os.replace(path + ".signed", path)
                # binary-sign-tool's output file loses the exec bit on
                # HMDFS (default 660) — restore it so the loader runs it
                os.chmod(path, os.stat(path).st_mode | 0o111)
                return True
        except Exception:
            pass
        return False

    def test(self):
        pkg_folder = self.dependencies["f3d"].package_folder
        f3d_bin = os.path.join(pkg_folder, "bin", "f3d")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_f3d")

        if not can_run(self):
            self.output.warning(
                "cross-building: cannot execute the test binary")
            return

        # OHOS: re-sign the packaged binary AND every dependency shared
        # library (conan's cache copies lost their .codesign sidecar, so
        # the loader would refuse to execute/dlopen them).
        sign_targets = [f3d_bin]
        for _r, d in self.dependencies.items():
            if d.package_folder and os.path.isdir(os.path.join(d.package_folder, "lib")):
                import glob as _glob
                sign_targets += [p for p in _glob.glob(
                    os.path.join(d.package_folder, "lib", "*.so*"))
                    if not os.path.islink(p)]
        missing = [t for t in sign_targets if not self._resign(t)]
        if missing:
            self.output.warning(
                "binary-sign-tool unavailable on OHOS — {} targets "
                "could not be re-signed; the execution test may fail "
                "with Permission denied".format(len(missing)))

        # f3d's NEEDED libf3d.so resolves via LD_LIBRARY_PATH: prepend
        # the package lib dir + /system/lib64 (libc++_shared.so).
        pkg_lib = os.path.join(pkg_folder, "lib")
        vtk_pkg = self.dependencies["f3d"].cpp_info.libdirs
        old_ldp = os.environ.get("LD_LIBRARY_PATH", "")
        parts = [p for p in ([pkg_lib] + list(vtk_pkg) + ["/system/lib64"]) if p]
        os.environ["LD_LIBRARY_PATH"] = ":".join(parts + ([old_ldp] if old_ldp else []))
        try:
            cmd = shlex.quote(test_bin) + " " + shlex.quote(f3d_bin)
            self.run(cmd, env="conanrun")
        finally:
            if old_ldp:
                os.environ["LD_LIBRARY_PATH"] = old_ldp
            else:
                os.environ.pop("LD_LIBRARY_PATH", None)
