#!/usr/bin/env python3
"""Consumer test for inn2/2.7.4.

Compiles test.c against the packaged libinn and runs it, verifying that the
installed headers, the three static libraries and the runtime behaviour all
work from a consumer's point of view.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class InnTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["inn2"]
        include = dep.cpp_info.includedirs[0]
        libdir = dep.cpp_info.libdirs[0]
        cc = os.environ.get("CC", "cc")

        cmd = ['%s test.c -o inn_consumer_test' % cc,
               '-I"%s"' % include]
        for lib in dep.cpp_info.libs:
            cmd.append('-L"%s" -l%s' % (libdir, lib))
        # libinn's public headers pull in zlib types; libm is needed by md5.
        cmd.append("-lz -lm")
        self.run(" ".join(cmd))

    def test(self):
        if can_run(self):
            self.run("./inn_consumer_test", env="conanrun")
            # The suite also ships command line tools; prove one runs.  convdate
            # is self-contained (no inn.conf needed) and prints the current date.
            dep = self.dependencies["inn2"]
            bin_path = os.path.join(dep.cpp_info.bindirs[0], "convdate")
            self.run('"%s"' % bin_path, env="conanrun")
