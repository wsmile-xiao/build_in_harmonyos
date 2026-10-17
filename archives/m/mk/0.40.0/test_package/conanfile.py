#!/usr/bin/env python3
"""conan test_package — mk (mk-configure) 0.40.0 (make/bmake build system).

Drives the real consumer scenario through test.sh: the installed mkcmake
wrapper builds a C project with the installed include library, the produced
program is executed and the packaged mkc_check_version helper is called.
"""
import os

from conan import ConanFile


class MkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        mk_pkg = self.dependencies["mk"].package_folder
        script = os.path.join(self.recipe_folder, "test.sh")
        self.output.info(f"mk package folder: {mk_pkg}")
        self.run(f'MK_PKG="{mk_pkg}" sh "{script}"', env="conanrun")
