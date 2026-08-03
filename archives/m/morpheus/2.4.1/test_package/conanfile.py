#!/usr/bin/env python3
import os

from conan import ConanFile


class MorpheusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        exe = "morpheus.exe" if self.settings.os == "Windows" else "morpheus"
        morpheus = os.path.join(self.dependencies["morpheus"].package_folder, "bin", exe)
        assert os.path.isfile(morpheus), "morpheus binary not found: {}".format(morpheus)
        smoke = os.path.join(self.source_folder, "smoke.xml")
        runner = os.path.join(self.source_folder, "run_smoke.sh")
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run('"{}" "{}" "{}" "{}"'.format(shell, runner, morpheus, smoke), env="conanrun")
        with open("morpheus-smoke.out", encoding="utf-8", errors="replace") as handle:
            output = handle.read()
        if "Simulation finished" not in output:
            raise Exception("Morpheus smoke test did not finish successfully")
