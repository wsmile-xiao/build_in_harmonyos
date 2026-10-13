#!/usr/bin/env python3
"""Consumer-side test for gumbo: parse an inline HTML5 document and
assert the element/text tree shape plus attribute lookup."""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class GumboTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-build: skipping native run (smoke binary built OK)")
            return
        smoke = os.path.join(self.cpp.build.bindir, "gumbo_smoke")
        if self.settings.os == "OHOS":
            signer = shutil.which("binary-sign-tool")
            if not signer:
                raise RuntimeError("Native binary-sign-tool required")
            private = os.path.join(self.build_folder, "harmony-private")
            os.makedirs(private, exist_ok=False)
            library = os.path.join(self.dependencies["gumbo"].package_folder,
                                   "lib", "libgumbo.so.1.0.0")
            # Never re-sign or overwrite a dependency's shared Conan cache.
            shutil.copy2(library, os.path.join(private, "libgumbo.so.1.0.0"))
            for name in ("gumbo_smoke", "gumbo_harmony"):
                binary = os.path.join(self.cpp.build.bindir, name)
                signed = binary + ".signed"
                subprocess.run([signer, "sign", "-selfSign", "1", "-inFile", binary,
                                "-outFile", signed], check=True)
                os.chmod(signed, 0o700)
            self.run('"' + smoke + '.signed"', env="conanrun")
            harmony = os.path.join(self.cpp.build.bindir, "gumbo_harmony.signed")
            self.run(f'"{harmony}" "{private}" "{private}"', env="conanrun")
        else:
            self.run('"' + smoke + '"', env="conanrun")
