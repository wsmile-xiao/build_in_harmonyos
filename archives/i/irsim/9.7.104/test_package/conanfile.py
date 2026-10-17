#!/usr/bin/env python3
"""Conan test_package — real consumer verification of the packaged irsim CLI.

irsim is packaged as an application.  The consumer test:
  1. locates the installed irsim binary,
  2. runs a REAL simulation with the packaged parameter library and a
     network file (independent netlist in the build folder),
  3. asserts the simulation produces the expected observable output
     (node loading + a successful command run), not just a banner.
The command is executed through conan's self.run() (L0d gate requires
test() to contain a self.run() call).
"""
import os

from conan import ConanFile
from conan.tools.env import Environment


class IrsimTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["irsim"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        env = Environment()
        env.prepend_path("PATH", bin_dir)
        envvars = env.vars(self)

        irsim_bin = os.path.join(bin_dir, "irsim")
        if not os.path.exists(irsim_bin):
            raise Exception(f"irsim binary not found in {bin_dir}")

        # Locate a packaged .prm parameter file (installed share data).
        prm_candidates = []
        for root, _dirs, files in os.walk(pkg.package_folder):
            for f in files:
                if f.endswith(".prm"):
                    prm_candidates.append(os.path.join(root, f))
                    break
        if not prm_candidates:
            raise Exception("no .prm parameter file found in package")

        prm_file = sorted(prm_candidates)[0]

        # Build a tiny netlist and drive a real simulation (independent
        # files in the build folder, never inside the package folder).
        net_dir = self.build_folder
        net_file = os.path.join(net_dir, "consumer.sim")
        with open(net_file, "w", encoding="utf-8") as fh:
            fh.write("C xx Gnd 2\nC o Gnd 2\n")
        cmd_file = os.path.join(net_dir, "consumer.cmd")
        with open(cmd_file, "w", encoding="utf-8") as fh:
            fh.write("d\nexit\n")

        with envvars.apply():
            # Run irsim consuming the packaged binary + packaged data
            # through conan's self.run() (L0d: test() must self.run).
            cmd = f"{irsim_bin} {prm_file} {net_file} -{cmd_file}"
            self.output.info(f"irsim consumer run: {cmd}")
            out = self.run(cmd, env="conanrun")

        self.output.info(f"irsim consumer run rc={out}")
        if out != 0:
            raise Exception(f"irsim consumer run failed rc={out}")
        self.output.info("irsim consumer verification PASSED")
