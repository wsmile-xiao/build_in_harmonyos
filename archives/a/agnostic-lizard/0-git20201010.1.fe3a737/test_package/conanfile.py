#!/usr/bin/env python3
"""Consumer-side test for the agnostic-lizard source-only package.

Checks installed source integrity, then invokes real ECL/ASDF core regression
entries, a code-walking consumer and an independent HMDFS functional test.
"""

import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class AgnosticLizardTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("ecl/24.5.10")

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def generate(self):
        from conan.tools.env import VirtualRunEnv
        VirtualRunEnv(self).generate()

    def test(self):
        package_root = self.dependencies["agnostic-lizard"].package_folder
        script = os.path.join(self.source_folder, "verify_agnostic_lizard.py")
        self.run(
            f'"{sys.executable}" "{script}" '
            f'--package-root "{package_root}"',
            env="conanrun",
        )
        # The recipe exports the installed source dir for ASDF consumers.
        src_dir = os.path.join(
            package_root, "share", "common-lisp", "source", "agnostic-lizard",
        )
        assert os.path.isfile(
            os.path.join(src_dir, "agnostic-lizard.asd")
        ), f"agnostic-lizard.asd missing under {src_dir}"
        print(f"ASDF source dir OK: {src_dir}")
        import json
        from pathlib import Path
        runtime = self.dependencies["ecl"].package_folder
        libraries = [str(Path(d.package_folder) / lib)
                     for d in self.dependencies.host.values()
                     for lib in d.cpp_info.libdirs]
        script = Path(self.source_folder) / "run_lisp_tests.py"
        self.run(f'"{sys.executable}" "{script}" --source "{src_dir}" '
                 f'--runtime "{runtime}" --work "{self.build_folder}/native-tests" '
                 f'--libraries \x27{json.dumps(libraries)}\x27', env="conanrun")
