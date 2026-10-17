#!/usr/bin/env python3
"""jellyfish1 test_package.

Two proof planes, both real:
  1. compile and link mmap_probe.cc against the installed headers
     (include/jellyfish/mapped_file.hpp) and the packaged libjellyfish, then
     run it - so both include/ and lib/ are genuinely depended upon.
  2. drive the packaged jellyfish CLI over a real fasta: count, dump, query,
     stat, asserting k-mer count values read back from the tool.  query, dump
     and stat open the database through mapped_file, so this also exercises
     the mmap read path end to end.
Everything runs in a scratch directory under ~/tmp so no artifact is left in
the recipe tree.
"""
import os
import shutil
import stat
import tempfile
from conan import ConanFile
from conan.tools.build import can_run


class Jellyfish1TestConan(ConanFile):
    name = "jellyfish1_test_package"
    version = "0.1"
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _rundir(self):
        root = os.path.join(os.path.expanduser("~"), "tmp")
        if not os.path.isdir(root):
            root = tempfile.gettempdir()
        d = os.path.join(root, "jellyfish1-tp-run")
        if not os.path.isdir(d):
            os.makedirs(d)
        return d

    def build(self):
        pkg = self.dependencies["jellyfish1"].package_folder
        incs = []
        libs = []
        for dep in self.dependencies.values():
            incs += ["-I" + p for p in dep.cpp_info.includedirs]
            for p in dep.cpp_info.libdirs:
                if os.path.isdir(p):
                    libs.append("-L" + p)
                    libs.append("-Wl,-rpath," + p)
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict)
        cxx = comp.get("cpp") or "/data/service/hnp/bin/clang++"
        d = self._rundir()
        for f in ("test.fa", "run_cli_tests.sh", "mmap_probe.cc"):
            shutil.copy(os.path.join(self.recipe_folder, f), d)
        jf = os.path.join(pkg, "bin", "jellyfish")
        with open(os.path.join(d, "jf.sh"), "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\nexec \"" + jf + "\" \"$@\"\n")
        for f in ("jf.sh", "run_cli_tests.sh"):
            p = os.path.join(d, f)
            os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        cmd = "%s -o mmap_probe mmap_probe.cc %s %s -ljellyfish-1.1 -lm -lpthread" % (cxx, " ".join(incs), " ".join(libs))
        self.run("cd \"" + d + "\" && " + cmd)

    def test(self):
        if not can_run(self):
            self.output.info("cross build, skipping run")
            return
        d = self._rundir()
        self.run("cd \"" + d + "\" && ./run_cli_tests.sh", env="conanrun")
