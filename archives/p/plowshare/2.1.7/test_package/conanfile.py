#!/usr/bin/env python3
"""Conan test_package — plowshare 2.1.7.

Consumer test: bash is a system tool on HarmonyOS (available through PATH,
e.g. /data/service/hnp/bin/bash), so it is deliberately NOT declared as a
Conan dependency. We verify the packaged CLI suite exists, is executable and
answers --version/--help through the installed bin/, then run the deeper
test.sh smoke assertions.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building

CLI_TOOLS = (
    "plowdown", "plowup", "plowdel",
    "plowlist", "plowprobe", "plowmod",
)


class PlowshareTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def configure(self):
        self.settings.rm_safe("os.version")

    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
        ):
            if candidate and os.path.exists(candidate):
                return f'"{candidate}"'
        return "bash"

    def test(self):
        if cross_building(self):
            return

        dep = self.dependencies["plowshare"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        for tool in CLI_TOOLS:
            path = os.path.join(bin_dir, tool)
            if not os.path.exists(path):
                raise RuntimeError(f"missing packaged CLI: {path}")
            if not os.access(path, os.X_OK):
                raise RuntimeError(f"packaged CLI not executable: {path}")

        bash = self._bash()

        self.run(f"{bash} --version")

        env_path = f"PATH={bin_dir}:$PATH"
        for tool in CLI_TOOLS:
            self.run(f"{env_path} {bash} -c 'command -v {tool}'")

        self.run(f"{env_path} {bash} -c '{bin_dir}/plowdown --help'")

        self.run(f'{env_path} {bash} "{self.source_folder}/test.sh"')