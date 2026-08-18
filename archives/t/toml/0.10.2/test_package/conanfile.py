import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TomlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies[self.tested_reference_str]
        upstream_tests = os.path.join(dep.package_folder, "upstream_tests")

        # --- Smoke gate (R34: must exercise the real API) ---
        self.run(
            'python3 -c "import toml; '
            'assert toml.loads(\'k=1\')=={\'k\':1}; print(\'smoke ok\')"',
            env="conanrun")

        if not os.path.isdir(upstream_tests):
            self.output.warning(
                "upstream_tests/ missing in package; only smoke ran")
            return

        # Run the real upstream pytest suite (tests/test_api.py, 23 cases).
        # The upstream CI (.travis.yml) also clones the external BurntSushi/
        # toml-test repo; two cases (test_valid_tests / test_invalid_tests)
        # depend on that submodule. When the submodule is absent those two
        # cases raise FileNotFoundError and are counted as failed by pytest.
        # We run the suite and fail the gate only if any of the 21 cases that
        # do NOT depend on the external submodule fail.
        runner = os.path.join(self.source_folder, "run_upstream.py")
        self.run(f'python3 "{runner}" "{upstream_tests}"',
                 env="conanrun")
