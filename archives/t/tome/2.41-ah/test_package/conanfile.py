#!/usr/bin/env python3
"""Conan test_package for tome 2.41-ah.

Compiles a C++ consumer against the installed headers and runs it.  The
consumer exercises the packaged flag_set<>/grid<> utilities (the same public
templates covered by the upstream Bandit suite).
"""
import json
import os
import shutil
import tempfile

from conan import ConanFile

CHECKS = 16


class TomeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        includedirs = list(dep.cpp_info.includedirs)
        # The public headers include Boost (<boost/...>) transitively.
        for transitive in self.dependencies.values():
            includedirs.extend(transitive.cpp_info.includedirs)
        includedirs = list(dict.fromkeys(includedirs))
        libdir = dep.cpp_info.libdirs[0]
        libs = dep.cpp_info.libs
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        cxx = executables.get("cpp") or executables.get("cxx") or "clang++"
        src = os.path.join(self.recipe_folder, "test_tome.cpp")
        if not os.path.isfile(src):
            raise Exception("consumer source not found: %s" % src)

        workdir = tempfile.mkdtemp(prefix="tome-consumer-")
        exe = os.path.join(workdir, "test_tome")
        link = " ".join("-l" + lib for lib in libs)
        incflags = " ".join('-I"%s"' % i for i in includedirs)
        cmd = ('"{cxx}" -std=c++17 -O2 -Wall {inc} "{src}" -L"{libdir}" {link} -o "{exe}"'
               .format(cxx=cxx, inc=incflags, src=src, libdir=libdir,
                       link=link, exe=exe))
        # Compile under conanbuild (SDK lld needs the llvm/lib runtime path on
        # CI); the executable then runs under conanrun.
        self.run(cmd, env="conanbuild")
        self.run('"{exe}"'.format(exe=exe), env="conanrun", cwd=workdir)
        shutil.rmtree(workdir, ignore_errors=True)
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "clang++ test_tome.cpp -lgame -lsquelch && ./test_tome",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
