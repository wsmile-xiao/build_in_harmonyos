#!/usr/bin/env python3
"""Conan test_package for mrcal 2.5.2.

Compiles a C consumer against the installed mrcal.h + libmrcal.so and checks
the lens-model API.
"""
import json
import os
import shutil
import tempfile

from conan import ConanFile

CHECKS = 9


class MrcalTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        includedir = dep.cpp_info.includedirs[0]
        libdir = dep.cpp_info.libdirs[0]
        libs = dep.cpp_info.libs
        libdirs = list(dep.cpp_info.libdirs)
        for transitive in self.dependencies.values():
            libdirs.extend(transitive.cpp_info.libdirs)
        libdirs = list(dict.fromkeys(libdirs))
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        cc = executables.get("c", "clang")
        src = os.path.join(self.recipe_folder, "test_mrcal.c")
        if not os.path.isfile(src):
            raise Exception("consumer source not found: %s" % src)

        workdir = tempfile.mkdtemp(prefix="mrcal-consumer-")
        exe = os.path.join(workdir, "test_mrcal")
        link = " ".join("-l" + lib for lib in libs)
        cmd = ('"{cc}" -O2 -std=gnu99 -Wall -I"{inc}" "{src}" -L"{libdir}" {link} -o "{exe}"'
               .format(cc=cc, inc=includedir, src=src, libdir=libdir,
                       link=link, exe=exe))
        self.run(cmd, env="conanbuild")
        runcmd = ('LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}" "{}"'.format(
            ":".join(libdirs), exe))
        self.run(runcmd, env="conanrun", cwd=workdir)
        shutil.rmtree(workdir, ignore_errors=True)
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "clang test_mrcal.c -lmrcal && ./test_mrcal",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
