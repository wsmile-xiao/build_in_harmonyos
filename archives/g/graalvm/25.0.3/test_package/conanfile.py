#!/usr/bin/env python3
"""Runtime and native-image consumer tests for GraalVM 25.0.3."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment


class GraalVMTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies["graalvm"]
        freetype = self.dependencies["freetype"]
        java_home = dependency.package_folder
        freetype_libdir = freetype.cpp_info.libdirs[0]
        tools = {
            "clang": "/data/service/hnp/bin/clang",
            "patchelf": "/data/service/hnp/bin/patchelf",
            "readelf": "/data/service/hnp/bin/llvm-readelf",
            "signer": "/data/service/hnp/bin/binary-sign-tool",
        }
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "the GraalVM binary adaptation is validated on OHOS only"
            )
        missing = [path for path in tools.values() if not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                f"OHOS ELF validation tools are missing: {missing}"
            )

        temp_root = os.environ.get("TMPDIR")
        if not temp_root or not os.path.isabs(temp_root):
            raise ConanInvalidConfiguration(
                "an external absolute TMPDIR is required for target tests"
            )
        temp_root = os.path.realpath(temp_root)
        work = os.path.join(temp_root, "graalvm-test-work")
        input_roots = {
            os.path.realpath(path)
            for path in (self.source_folder, self.build_folder)
            if path
        }
        if any(os.path.commonpath((work, root)) == root for root in input_roots):
            raise ConanInvalidConfiguration(
                "target test work must remain outside frozen Conan inputs"
            )
        environment = Environment()
        environment.define_path("JAVA_HOME", java_home)
        environment.prepend_path("PATH", os.path.join(java_home, "bin"))
        environment.unset("LD_LIBRARY_PATH")
        environment.define_path("TMPDIR", os.path.join(work, "tmp"))
        environment.define_path("TMPPREFIX", os.path.join(work, "tmp"))

        command = shlex.join(
            [
                "/system/bin/sh",
                os.path.join(self.source_folder, "test.sh"),
                java_home,
                work,
                self.source_folder,
                tools["readelf"],
                tools["patchelf"],
                freetype_libdir,
                tools["clang"],
                tools["signer"],
            ]
        )
        with environment.vars(self).apply():
            self.run(command)
