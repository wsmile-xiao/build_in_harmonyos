#!/usr/bin/env python3
"""Test package for logstalgia (consumer-side smoke test).

AI review PR #9643 follow-up: besides the --help smoke run, the test now
links glu_glew_shim_selftest() from the packaged libGLU.a and runs it, so
the GLU matrix maths (the highest-risk part of the shim) is verified from
the consumer side too - previously only the recipe build() probe ran it.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run, cross_building
from conan.tools.env import Environment


class TestLogstalgiaConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link verified only")
            return
        if not can_run(self):
            self.output.info("cannot run on this host: skipping run test")
            return

        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; test.c works
        # around that with execlp(). Launch the test binary through bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cc = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict).get("c", "clang")

        # GLU/GLEW shim self-test (AI review PR #9643): link the packaged
        # libGLU.a into the consumer test binary. The shim object references
        # two GL entry points (glTexImage2D from the mipmap path,
        # glMultMatrixd from gluPerspective) that the self-test never calls -
        # gl_stub.c stubs merely satisfy the static linker, same approach as
        # the build() probe in the main recipe (linking the real gl4es
        # libGL on a headless worker would crash in its loader init).
        tested = self.dependencies[self.tested_reference_str]
        shim_lib = os.path.join(tested.package_folder, "lib", "libGLU.a")
        if not os.path.isfile(shim_lib):
            self.output.error(f"packaged shim lib missing: {shim_lib}")
            raise ConanException("libGLU.a not found in tested package")

        # gl4es run-time: point the desktop-GL shim at the OHOS system
        # GLES3/EGL stacks (same pattern as the gl4es package test). Also
        # extend LD_LIBRARY_PATH with /system/lib64 so libEGL.so and its
        # libc++.so dependency resolve (gl4es own test does the same).
        env = Environment()
        env.define("LIBGL_GLES", "/system/lib64/libGLESv3.so")
        env.define("LIBGL_EGL", "/system/lib64/libEGL.so")
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")

        with env.vars(self).apply():
            # compile the smoke test + GL stubs and link the packaged shim
            # (E467 loader paths are not needed at compile time: the test
            # binary only needs libc/libc++_shared at run time, resolved via
            # the bash env below)
            self.run(f"{cc} test.c gl_stub.c {shim_lib} -o test_logstalgia "
                     f"-lm", env="conanbuild")
            # run it with conanrun env (dependency libs) + bash
            self.run(f"{bash} -c './test_logstalgia'", env="conanrun")
