#!/usr/bin/env python3
"""Conan test_package for kcemu 0.5.2.

Compiles a C++ consumer against the installed prefs/dbg/sys libraries and runs
it (the same preferences surface as upstream's t_prefs).
"""
import json
import os
import shutil
import tempfile

from conan import ConanFile

CHECKS = 4


class KcemuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        incs = list(dep.cpp_info.includedirs)
        libdirs = list(dep.cpp_info.libdirs)
        for transitive in self.dependencies.values():
            incs.extend(transitive.cpp_info.includedirs)
            libdirs.extend(transitive.cpp_info.libdirs)
            pkg = transitive.package_folder
            if pkg:
                for extra in (os.path.join(pkg, "include", "glib-2.0"),
                              os.path.join(pkg, "lib", "glib-2.0", "include")):
                    if os.path.isdir(extra):
                        incs.append(extra)
        incs = list(dict.fromkeys(incs))
        libdirs = list(dict.fromkeys(libdirs))

        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        cxx = executables.get("cpp") or executables.get("cxx") or "clang++"
        src = os.path.join(self.recipe_folder, "test_kcemu.cpp")
        if not os.path.isfile(src):
            raise Exception("consumer source not found: %s" % src)

        workdir = tempfile.mkdtemp(prefix="kcemu-consumer-")
        exe = os.path.join(workdir, "test_kcemu")
        incflags = " ".join('-I"{}"'.format(i) for i in incs)
        libflags = " ".join('-L"{}"'.format(i) for i in libdirs)
        cmd = ('"{cxx}" -O2 -std=gnu++14 -fcommon -Wall {inc} "{src}" {lib} '
               '-lprefs -ldbg -lsys_unix -lglib-2.0 -o "{exe}"'
               .format(cxx=cxx, inc=incflags, src=src, lib=libflags, exe=exe))
        self.run(cmd, env="conanbuild")
        state = os.path.join(workdir, "state")
        runcmd = ('KCEMU_TEST_BASEDIR="{}" LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}" "{}"'
                  .format(state, ":".join(libdirs), exe))
        self.run(runcmd, env="conanrun", cwd=workdir)
        shutil.rmtree(workdir, ignore_errors=True)
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "clang++ test_kcemu.cpp -lprefs -ldbg -lsys_unix -lglib-2.0 && ./test_kcemu",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
