#!/usr/bin/env python3
"""Consumer test for GNU trueprint 5.3 (tool package).

trueprint ships no linkable public API — the trueprint binary is the
product, so the consumer test executes the packaged binary and asserts
observable formatting behaviour (R34/R51) through test_trueprint.sh.
"""
import os

from conan import ConanFile


class TrueprintTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        script = os.path.join(self.source_folder, "test_trueprint.sh")
        sample = os.path.join(self.source_folder, "sample.c")
        spool = self.build_folder
        self.run(f'sh "{script}" "{bindir}" "{sample}" "{spool}"',
                 env=["TP_OPTS=--N"])
