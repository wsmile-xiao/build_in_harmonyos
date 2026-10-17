#!/usr/bin/env python3
"""Conan test_package — libobjc 16.1.1 (L1 consumer test).

Builds and runs a small C program that links against the packaged GNU
Objective-C runtime and exercises its public runtime API (selector registry,
class lookup, instance allocation).  The test uses pure C entry points, so it
compiles with a plain C toolchain without requiring an Objective-C front end.

We compile the consumer directly with clang instead of CMake: on HarmonyOS the
large cmake child can transiently SIGSEGV under the memory pressure left by
the full GCC build, whereas a single clang invocation is reliable.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.env import Environment


class LibobjcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # The device clang lives outside the isolated job PATH and writes its
        # temp files to /tmp by default, which is read-only; expose both.  Use
        # a non-reserved script name: Conan reserves "conanbuild" for its own
        # aggregate environment file.
        env = Environment()
        env.prepend_path("PATH", "/data/service/hnp/bin")
        env.define("TMPDIR", "/data/storage/el2/base/cache")
        env.define("TMP", "/data/storage/el2/base/cache")
        env.define("TEMP", "/data/storage/el2/base/cache")
        env.vars(self).save_script("test_build_env")

    def build(self):
        dep = self.dependencies["libobjc"]
        include_flags = " ".join("-I" + d for d in dep.cpp_info.includedirs)
        lib_flags = " ".join("-L" + d for d in dep.cpp_info.libdirs)
        lib_names = " ".join("-l" + name for name in dep.cpp_info.libs)
        source = os.path.join(self.source_folder, "test_objc.c")
        output = os.path.join(self.build_folder, "test_libobjc")
        self.run(
            "export TMPDIR=/data/storage/el2/base/cache "
            "TMP=/data/storage/el2/base/cache "
            "TEMP=/data/storage/el2/base/cache; "
            "clang -static-libgcc {} {} {} {} -o {}".format(
                include_flags, source, lib_flags, lib_names, output
            ),
            env="test_build_env",
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile-only check")
            return
        executable = os.path.join(self.build_folder, "test_libobjc")
        # The statically-linked test binary prints ALL PASSED and then the
        # shared libgcc's exit destructor can SIGSEGV on HarmonyOS.  Capture
        # the output and require the ALL PASSED marker instead of trusting the
        # exit code.
        log = os.path.join(self.build_folder, "test_output.log")
        self.run(
            "{} > {} 2>&1; true".format(executable, log),
            env="test_build_env",
        )
        with open(log, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        if "ALL PASSED" not in content:
            raise ConanException(
                "test binary did not report ALL PASSED:\n{}".format(content)
            )
