import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class KworkflowTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        # Keep generated env scripts and build state out of the (possibly
        # read-only-checked) source tree.
        basic_layout(self)

    def requirements(self):
        # Required by conan 2.29: the test_package must declare the tested
        # package explicitly via tested_reference_str.
        self.requires(self.tested_reference_str)
        # The harness needs the bash binary location. As a purely transitive
        # dependency its package_folder is None in the test_package graph, so
        # declare it directly (exact ref matches kworkflow's own requirement,
        # resolving to the same package node).
        self.requires("bash/5.3")

    def generate(self):
        # Legal Conan 2 API: consumers read dependency package folders.
        # bash/5.3 only exposes cpp_info.libs=["bash"] and no bin PATH, and
        # kw's shebang is "#!/usr/bin/env bash" — without a PATH injection the
        # entry point is not executable at all.
        bash_pkg = self.dependencies["bash"].package_folder
        kw_pkg = self.dependencies["kworkflow"].package_folder
        bash_bin = os.path.join(bash_pkg, "bin")
        kw_bin = os.path.join(kw_pkg, "bin")
        if not os.path.isfile(os.path.join(bash_bin, "bash")):
            raise ConanException(f"bash binary not found in dependency package: {bash_bin}")
        if not os.path.isfile(os.path.join(kw_bin, "kw")):
            raise ConanException(f"kw entry not found in package: {kw_bin}")
        env = Environment()
        env.prepend_path("PATH", bash_bin)
        env.prepend_path("PATH", kw_bin)
        env.vars(self).save_script("conanrun")

    def test(self):
        bash_pkg = self.dependencies["bash"].package_folder
        kw_pkg = self.dependencies["kworkflow"].package_folder
        runner = os.path.join(self.source_folder, "kw_test_runner.sh")
        cmd = (
            f'PATH="{bash_pkg}/bin:{kw_pkg}/bin:$PATH" '
            f'KW_PKG_ROOT="{kw_pkg}" BASH_PKG_ROOT="{bash_pkg}" '
            f'TEST_SRC="{self.source_folder}" '
            f'bash "{runner}"'
        )
        self.run(cmd, env="conanrun")
