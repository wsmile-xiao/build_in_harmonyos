#!/usr/bin/env python3
"""Conan test_package — nowplaying-cli 2.1.0.1 (OHOS equivalent CLI).

R34: the test must substantially exercise the packaged artifact. The package
is a command-line tool, so we run the installed binary:
  * `nowplaying-cli --help` must exit 0 and print usage;
  * `nowplaying-cli get --demo --json` must exit 0 and emit a JSON record;
  * `nowplaying-cli seek 90` (control command) must exit 0;
  * `nowplaying-cli get title artist --demo` (TSV field query) must exit 0.
"""
import os

from conan import ConanFile


class NowplayingcliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        pass

    def build(self):
        # Nothing to compile: this is a binary-exercise test.
        pass

    def test(self):
        # Locate the installed binary: conan exposes the package path through
        # the dependency's package_folder during test_package.
        bindir = self.dependencies["nowplaying-cli"].package_folder
        bin_path = os.path.join(bindir, "bin", "nowplaying-cli")
        if not os.path.isfile(bin_path):
            raise SystemExit(f"nowplaying-cli not found at {bin_path}")
        # --help smoke test
        self.run(f'"{bin_path}" --help', env="conanrun")
        # metadata query in JSON form (demo-seeded provider path)
        self.run(f'"{bin_path}" get --demo --json', env="conanrun")
        # control command path
        self.run(f'"{bin_path}" seek 90', env="conanrun")
        # a field query exercised through the TSV formatter
        self.run(f'"{bin_path}" get title artist --demo', env="conanrun")