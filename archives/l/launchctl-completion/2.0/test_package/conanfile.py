import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class LaunchctlCompletionTestConan(ConanFile):
    # Config-free harness for a config-free data package (no settings
    # attribute — the ohos-aarch64 profile axes are irrelevant to a
    # no-compile data package).
    def layout(self):
        # Keep generated env scripts out of the (possibly read-only-checked)
        # source tree.
        basic_layout(self)

    def requirements(self):
        # Required by conan 2.29: the test_package must declare the tested
        # package explicitly via tested_reference_str.
        self.requires(self.tested_reference_str)
        # The harness needs a bash >= 5.3 binary (the completion uses
        # `compgen -V`). As a purely transitive dependency its package_folder
        # is None in the test_package graph, so declare it directly (exact
        # ref matches the recipe's own requirement, resolving to the same
        # package node). bash/5.3 ships <package_folder>/bin/bash but does
        # not expose it via cpp_info, so the PATH is injected in generate().
        self.requires("bash/5.3")

    def generate(self):
        bash_pkg = self.dependencies["bash"].package_folder
        pkg = self.dependencies["launchctl-completion"].package_folder
        bash_bin = os.path.join(bash_pkg, "bin")
        completion = os.path.join(
            pkg, "share", "bash-completion", "completions", "launchctl"
        )
        if not os.path.isfile(os.path.join(bash_bin, "bash")):
            raise ConanException(
                f"bash binary not found in dependency package: {bash_bin}"
            )
        if not os.path.isfile(completion):
            raise ConanException(
                f"completion file not found in package: {completion}"
            )
        env = Environment()
        env.prepend_path("PATH", bash_bin)
        env.vars(self).save_script("conanrun")

    def test(self):
        bash_pkg = self.dependencies["bash"].package_folder
        pkg = self.dependencies["launchctl-completion"].package_folder
        runner = os.path.join(self.source_folder, "launchctl_completion_test.sh")
        cmd = (
            f'PATH="{bash_pkg}/bin:$PATH" '
            f'BASH_BIN="{bash_pkg}/bin/bash" '
            f'PKG_ROOT="{pkg}" '
            f'TEST_SRC="{self.source_folder}" '
            f'bash "{runner}"'
        )
        self.run(cmd, env="conanrun")
