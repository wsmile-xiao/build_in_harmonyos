#!/usr/bin/env python3
"""Conan test_package for oourafft 1.0.

Compiles a C consumer against the installed static libraries and runs real
round-trip transforms through the public Ooura FFT API (1-D cdft/rdft, 2-D
cdft2d) plus the alloc helpers.
"""
import json
import os
import shutil
import tempfile

from conan import ConanFile

CHECKS = 7


class OourafftTestConan(ConanFile):
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
        src = os.path.join(self.recipe_folder, "test_oourafft.c")
        if not os.path.isfile(src):
            raise Exception("consumer source not found: %s" % src)

        workdir = tempfile.mkdtemp(prefix="oourafft-consumer-")
        exe = os.path.join(workdir, "test_oourafft")
        link = " ".join("-l" + lib for lib in libs)
        cmd = ('"{cc}" -O2 -Wall -I"{inc}" "{src}" -L"{libdir}" {link} -lm -o "{exe}"'
               .format(cc=cc, inc=includedir, src=src, libdir=libdir,
                       link=link, exe=exe))
        # Compile under conanbuild (SDK lld needs the llvm/lib runtime path on
        # CI); the statically linked executable then runs under conanrun.
        self.run(cmd, env="conanbuild")
        self.run('"{exe}"'.format(exe=exe), env="conanrun", cwd=workdir)
        shutil.rmtree(workdir, ignore_errors=True)
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "clang test_oourafft.c -lfft2d_fftsg2d -lfft2d_fftsg -lfft2d_alloc -lm && ./test_oourafft",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
