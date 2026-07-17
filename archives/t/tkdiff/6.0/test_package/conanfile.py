#!/usr/bin/env python3
"""Conan test_package for tkdiff 6.0."""
import os
import shutil

from conan import ConanFile


class TkdiffTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["tkdiff"]
        script = os.path.join(dep.package_folder, "bin", "tkdiff")
        assert os.path.isfile(script), f"missing tkdiff script: {script}"

        with open(script, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        assert content.startswith("#!/usr/bin/env sh"), "tkdiff shebang was not adapted for HarmonyOS"
        assert "package require Tk" in content, "tkdiff Tcl/Tk entry point missing"
        assert "^--help" in content and "^-h" in content, "tkdiff help switch handling missing"

        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            wish = shutil.which("wish")
            if wish:
                self.run(f'"{wish}" "{script}" --help', env="conanrun")
        else:
            self.output.info("No display server detected; static package validation completed")
