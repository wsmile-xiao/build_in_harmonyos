#!/usr/bin/env python3
"""Charm++ conan test_package — HarmonyOS-specific runtime verification (R53).

Test flow (all on the HarmonyOS PC):
  1. ask the packaged bin/charmc for its version (-V is charmc's version flag);
  2. compile a real Charm++ program (mainchare + chare array) with the packaged
     bin/charmc, exactly like a user would;
  3. run it as a single PE and assert the runtime output;
  4. run it through the packaged bin/charmrun with 2 PEs (multi-process
     charmrun handshake, TCP transport) and assert the output again.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, load
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        charmpp = self.dependencies["charmpp"].package_folder
        charmc = os.path.join(charmpp, "bin", "charmc")
        charmrun = os.path.join(charmpp, "bin", "charmrun")
        assert os.path.isfile(charmc), "bin/charmc was not packaged"
        assert os.path.isfile(charmrun), "bin/charmrun was not packaged"

        work = os.path.join(self.build_folder, "work")
        copy(self, "test_hello.ci", src=self.source_folder, dst=work)
        copy(self, "test_hello.cpp", src=self.source_folder, dst=work)

        # charmc must report the Charm++ version it was built from (upstream tag
        # v8.0.2 ships project VERSION 8.0.1, hence the numeric string 80001;
        # 80002 accepted in case upstream fixes the version typo later)
        self.run(f'"{charmc}" -V > charmc-version.log 2>&1', cwd=work)
        version = load(self, os.path.join(work, "charmc-version.log"))
        assert ("Charm++ Version 80001" in version
                or "Charm++ Version 80002" in version), version

        # Build a real Charm++ program with the packaged compiler driver
        self.run(f'"{charmc}" -language charm++ -o test_hello test_hello.ci test_hello.cpp', cwd=work)
        binary = os.path.join(work, "test_hello")
        assert os.path.isfile(binary), "charmc did not produce the test program"

        # 1) single-process run on the HarmonyOS PC
        self.run(f'"{binary}" 5 > direct.log 2>&1', cwd=work)
        direct = load(self, os.path.join(work, "direct.log"))
        assert "Running Hello on 1 processors for 5 elements" in direct, direct
        assert "All done" in direct, direct

        # 2) two-process run through the packaged charmrun
        self.run(f'"{charmrun}" ++local +p2 "{binary}" 5 > charmrun.log 2>&1', cwd=work)
        multi = load(self, os.path.join(work, "charmrun.log"))
        assert "Running Hello on 2 processors for 5 elements" in multi, multi
        assert "All done" in multi, multi
        self.output.info("charmpp runs correctly on HarmonyOS (1 PE direct, 2 PEs via charmrun)")
