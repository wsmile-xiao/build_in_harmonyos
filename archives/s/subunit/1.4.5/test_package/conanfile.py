#!/usr/bin/env python3
"""Consumer-side test for subunit: build a tiny client against libsubunit
and verify the emitted subunit v1 protocol stream."""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class SubunitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SUBUNIT_SHARED"] = bool(self.dependencies["subunit"].options.shared)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-build: skipping native run (smoke binary built OK)")
            return
        smoke = os.path.abspath(os.path.join(self.cpp.build.bindir, "subunit_smoke"))
        if str(self.settings.os) != "OHOS":
            self.run('"' + smoke + '"', env="conanrun")
            return
        signer = shutil.which("binary-sign-tool")
        if not signer:
            raise RuntimeError("Native binary-sign-tool required")
        private = os.path.join(self.build_folder, "harmony-private")
        os.makedirs(private, exist_ok=False)
        if self.dependencies["subunit"].options.shared:
            package_lib = os.path.realpath(os.path.join(self.dependencies["subunit"].package_folder, "lib"))
            original = os.path.realpath(os.path.join(package_lib, "libsubunit.so"))
            if os.path.commonpath([original, package_lib]) != package_lib:
                raise RuntimeError("Shared library escaped the resolved package directory")
            library = os.path.join(private, "libsubunit.so.1.4.5")
            subprocess.run([signer, "sign", "-inFile", original, "-outFile", library, "-selfSign", "1"], check=True)
            os.chmod(library, 0o700)
            for name in ("libsubunit.so", "libsubunit.so.0"):
                shutil.copyfile(library, os.path.join(private, name))
                os.chmod(os.path.join(private, name), 0o700)
        for name in ("subunit_smoke", "subunit_harmony"):
            binary = os.path.abspath(os.path.join(self.cpp.build.bindir, name))
            subprocess.run([signer, "sign", "-inFile", binary, "-outFile", binary + ".signed", "-selfSign", "1"], check=True)
            os.chmod(binary + ".signed", 0o700)
        env = dict(os.environ, LD_LIBRARY_PATH=private)
        subprocess.run([smoke + ".signed"], env=env, check=True, timeout=30)
        harmony = os.path.abspath(os.path.join(self.cpp.build.bindir, "subunit_harmony.signed"))
        subprocess.run([harmony, private, private], env=env, check=True, timeout=30)
