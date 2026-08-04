#!/usr/bin/env python3
"""Conan test_package - fcheck 2.7.59."""
import shlex
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run


class FcheckTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["fcheck"]
        package_folder = Path(dep.package_folder)
        launcher = package_folder / "bin" / "fcheck"
        script = package_folder / "share" / "fcheck" / "fcheck.pl"
        sample_cfg = package_folder / "share" / "fcheck" / "fcheck.cfg"

        for path in (launcher, script, sample_cfg):
            if not path.is_file():
                raise RuntimeError(f"missing packaged fcheck artifact: {path}")

        if not can_run(self):
            self.output.info("Cross-building; fcheck layout check completed")
            return

        launcher_q = shlex.quote(str(launcher))
        script_q = shlex.quote(str(Path(self.source_folder) / "test.sh"))
        work_q = shlex.quote(str(Path(self.build_folder)))
        self.run(f"sh {script_q} {launcher_q} {work_q}", env="conanrun")
