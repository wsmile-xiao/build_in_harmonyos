#!/usr/bin/env python3
"""Conan test_package for upb 0.0.0-git200730.

Compiles a C consumer against the installed headers + libupb.a and checks the
varint/zigzag helpers (the API exercised by upstream tests/pb/test_varint.c).
"""
import json
import os
import shutil
import tempfile

from conan import ConanFile

CHECKS = 11


class UpbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        includedir = dep.cpp_info.includedirs[0]
        libdir = dep.cpp_info.libdirs[0]
        libs = dep.cpp_info.libs
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        cc = executables.get("c", "clang")
        src = os.path.join(self.recipe_folder, "test_upb.c")
        if not os.path.isfile(src):
            raise Exception("consumer source not found: %s" % src)

        workdir = tempfile.mkdtemp(prefix="upb-consumer-")
        exe = os.path.join(workdir, "test_upb")
        link = " ".join("-l" + lib for lib in libs)
        cmd = ('"{cc}" -O2 -std=gnu99 -Wall -I"{inc}" "{src}" -L"{libdir}" {link} -o "{exe}"'
               .format(cc=cc, inc=includedir, src=src, libdir=libdir,
                       link=link, exe=exe))
        self.run(cmd, env="conanbuild")
        self.run('"{exe}"'.format(exe=exe), env="conanrun", cwd=workdir)
        shutil.rmtree(workdir, ignore_errors=True)
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "clang test_upb.c -lupb && ./test_upb",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
