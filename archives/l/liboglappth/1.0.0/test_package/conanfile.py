#!/usr/bin/env python3
"""Consumer test for liboglappth 1.0.0 on OHOS.

Builds two C++ test programs against the packaged liboglappth headers and
library, signs the executables (OHOS will not start an unsigned binary) and
runs them. The tests exercise the real public API (camera settings copy,
vector template math) without needing a GL context — the GL/GLU symbols
liboglappth leaves undefined resolve through the gl4es dependency at link
time.
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
    generators = "CMakeDeps", "CMakeToolchain"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)
        # gl4es is a transitive dep of liboglappth, but the library's public
        # headers include <GL/gl.h>/<GL/glu.h> — the consumer needs the GL
        # include dir + libGL on its own link line too.
        self.requires("gl4es/1.1.6")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._sign_test_binaries()

    def _sign_test_binaries(self):
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
        # gl4es needs runtime wiring on OHOS (no desktop libGL; GLES lives in
        # libGLESv3.so, EGL in libEGL.so — same接线 as coin/4.0.10). The tests
        # themselves are pure-CPU: no GL context is created, but gl4es
        # initialises at library load time via the interposed symbols.
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += [os.path.join(_d.package_folder, d) for d in _d.cpp_info.libdirs]
        ld = ":".join(libdirs)
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_liboglappth")
        self.run('LD_LIBRARY_PATH={ld} LIBGL_GLES=/system/lib64/libGLESv3.so '
                 'LIBGL_EGL=/system/lib64/libEGL.so "{0}"'.format(test_bin, ld=ld),
                 env="conanrun")
        harmony_bin = os.path.join(self.cpp.build.bindirs[0], "harmonyos_specific_test")
        self.run('LD_LIBRARY_PATH={ld} LIBGL_GLES=/system/lib64/libGLESv3.so '
                 'LIBGL_EGL=/system/lib64/libEGL.so "{0}"'.format(harmony_bin, ld=ld),
                 env="conanrun")
