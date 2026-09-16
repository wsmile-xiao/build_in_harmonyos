#!/usr/bin/env python3
"""Consumer test for sdl-image 1.2.12 on OHOS.

Builds test.c against the packaged SDL_image 1.2 headers and library, signs
the executable (OHOS will not start an unsigned binary) and runs it with the
runtime environment of the dependency graph, so the transitive codec
dependencies (libpng / libjpeg-turbo / libtiff / libwebp) and the sdl12-compat
SDL 1.2 implementation are exercised the same way a real consumer would.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"
SIGNER = "/data/service/hnp/bin/binary-sign-tool"


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # sdl12-compat keeps its headers in include/SDL, but its published
        # package_info leaves cpp_info.includedirs empty, so CMakeDeps has no
        # include directory to export to consumers.  Locate the headers
        # through the dependency's package folder instead (the SDL 1.2
        # headers are part of the SDL_image API, a real consumer needs them).
        sdl = self.dependencies["sdl12-compat"]
        inc = os.path.join(sdl.package_folder, "include")
        tc = CMakeToolchain(self)
        tc.variables["SDL1_INCLUDE_DIRS"] = "{0};{1}".format(inc, os.path.join(inc, "SDL"))
        tc.generate()

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._sign_test_binary()

    def _sign_test_binary(self):
        bindir = os.path.join(self.cpp.build.bindirs[0])
        for f in os.listdir(bindir):
            path = os.path.join(bindir, f)
            if not os.path.isfile(path) or not os.access(path, os.X_OK):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null'.format(oc=OBJCOPY, f=path), ignore_errors=True)
            tmp = path + ".signed"
            self.run('{sg} sign -inFile "{f}" -outFile "{t}" -selfSign 1'.format(sg=SIGNER, f=path, t=tmp))
            if os.path.exists(tmp):
                shutil.move(tmp, path)
            # binary-sign-tool output may lose the exec bit; restore it
            os.chmod(path, 0o755)

    def test(self):
        if not can_run(self):
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_sdl_image")
        # the dummy SDL video driver keeps the test headless; it is set inline
        # so it applies to the launched process itself
        self.run('SDL_VIDEODRIVER=dummy "{0}"'.format(test_bin), env="conanrun")
        harmony_bin = os.path.join(self.cpp.build.bindirs[0], "harmonyos_specific_test")
        self.run('SDL_VIDEODRIVER=dummy "{0}"'.format(harmony_bin), env="conanrun")
