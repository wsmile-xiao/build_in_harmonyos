#!/usr/bin/env python3
"""Consumer validation for corrected librttopo 1.1.0."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibrttopoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    @property
    def _test_binary(self):
        return os.path.join(self.cpp.build.bindir, "test_librttopo")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._sign_test_binary()

    def _sign_test_binary(self):
        if str(self.settings.os) != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires signing tools"
            )
        self.run(
            '"{}" --remove-section .codesign "{}" 2>/dev/null || true'.format(
                objcopy, self._test_binary
            )
        )
        self.run(
            '"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                signer, self._test_binary, self._test_binary
            )
        )

    def _writable_tmp_environment(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment = Environment()
        environment.define("TMPDIR", tmpdir)
        environment.define("TMPPREFIX", os.path.join(tmpdir, "zsh-tmp-"))
        return environment

    def test(self):
        if not can_run(self):
            self.output.info("Cross build: consumer compile/link passed")
            return
        with self._writable_tmp_environment().vars(self).apply():
            self.run('"{}"'.format(self._test_binary), env="conanrun")
