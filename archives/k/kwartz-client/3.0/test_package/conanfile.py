import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class KwartzClientTestConan(ConanFile):
    # Config-free harness for a zero-compilation package: the profile axes
    # are irrelevant to the smoke assertions (launchctl-completion precedent).
    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Conan 2.29 requires the tested package to be declared explicitly.
        self.requires(self.tested_reference_str)
        # The harness needs a real POSIX-capable shell to run `bash -n`
        # syntax gates against the packaged scripts. bash/5.3 is published
        # for this repository's OHOS workers (launchctl-completion precedent).
        # Exact ref keeps it resolving to the same package node.
        self.requires("bash/5.3")

    def generate(self):
        bash_pkg = self.dependencies["bash"].package_folder
        pkg = self.dependencies["kwartz-client"].package_folder
        bash_bin = os.path.join(bash_pkg, "bin")
        script = os.path.join(pkg, "bin", "kwartz-cloud")
        if not os.path.isfile(os.path.join(bash_bin, "bash")):
            raise ConanException(
                f"bash binary not found in dependency package: {bash_bin}"
            )
        if not os.path.isfile(script):
            raise ConanException(
                f"kwartz-cloud script not found in package: {script}"
            )
        env = Environment()
        env.prepend_path("PATH", bash_bin)
        env.vars(self).save_script("conanrun")

    def test(self):
        bash_pkg = self.dependencies["bash"].package_folder
        pkg = self.dependencies["kwartz-client"].package_folder
        runner = os.path.join(self.source_folder, "kwartz_client_test.sh")
        cmd = (
            f'PATH="{bash_pkg}/bin:$PATH" '
            f'BASH_BIN="{bash_pkg}/bin/bash" '
            f'PKG_ROOT="{pkg}" '
            f'bash "{runner}"'
        )
        self.run(cmd, env="conanrun")
