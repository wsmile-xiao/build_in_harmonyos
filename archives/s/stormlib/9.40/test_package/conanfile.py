#!/usr/bin/env python3
"""Consumer test for stormlib/9.40.

Compiles test.c against the packaged StormLib (headers + library) and runs
a full MPQ archive round trip: create -> add -> write -> finish -> close ->
reopen -> read back -> byte-compare.
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class StormLibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["stormlib"]
        include = dep.cpp_info.includedirs[0]
        libdir = dep.cpp_info.libdirs[0]
        cc = os.environ.get("CXX", os.environ.get("CC", "c++"))

        cmd = ['"%s" test.c -o stormlib_consumer_test' % cc,
               '-I"%s"' % include]
        for lib in dep.cpp_info.libs:
            cmd.append('-L"%s" -l%s' % (libdir, lib))
        # StormLib's system-library build pulls zlib/bzip2 symbols.
        for dep_name in ("zlib", "bzip2"):
            d = self.dependencies[dep_name]
            cmd.append('-L"%s"' % d.cpp_info.libdirs[0])
            for lib in d.cpp_info.libs:
                cmd.append("-l%s" % lib)
        cmd.append("-lpthread")
        self.run(" ".join(cmd))

    def test(self):
        if can_run(self):
            tmpdir = tempfile.mkdtemp(prefix="stormlib-test-")
            try:
                self.run('./stormlib_consumer_test "%s"' % tmpdir, env="conanrun")
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
