#!/usr/bin/env python3
"""Consumer test for intercal 0.30.

Runs the installed `ick` compiler end-to-end: compile the bundled `hello.i` INTERCAL
program to native and execute it, asserting the produced program prints
`hello, world`. This exercises the real product path (ick -> C -> ELF -> run),
not just `--version`.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy


class IntercalTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["intercal"]
        bindir = os.path.join(dep.package_folder, "bin")
        ick = os.path.join(bindir, "ick")
        if not os.path.isfile(ick):
            raise ConanException("installed ick binary not found at %s" % ick)

        work = os.path.join(self.build_folder, "_run")
        os.makedirs(work, exist_ok=True)
        copy(self, "hello.i", self.recipe_folder, work, keep_path=False)

        # ick shells out to a C compiler named by CC (falls back to bare "gcc",
        # which is absent on the device); point it at the Conan-resolved compiler.
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp.get("c") or "cc"

        # The three behavioural assertions live in smoke.sh, which is also the
        # `*.sh` test source CI gate L0c looks for under test_package/.  Invoked
        # via `sh` because HMDFS may not preserve the executable bit.
        smoke = os.path.join(self.recipe_folder, "smoke.sh")
        if not os.path.isfile(smoke):
            raise ConanException("consumer test script not found at %s" % smoke)
        env = (
            "export ICK='{ick}'; "
            "export CC='{cc}'; "
            "export SRC='{src}'; "
            "export WORK='{work}'; "
            "export BINDIR='{bindir}'; "
        ).format(ick=ick, cc=cc, src=os.path.join(work, "hello.i"), work=work, bindir=bindir)
        self.run(env + "sh '{smoke}'".format(smoke=smoke), cwd=work)
