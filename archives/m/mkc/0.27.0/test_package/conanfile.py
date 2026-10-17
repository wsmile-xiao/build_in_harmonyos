#!/usr/bin/env python3
"""conan test_package — mkc (mk-configure) 0.27.0 (make/bmake build system).

Drives the real consumer scenario through test.sh: the installed mkcmake
wrapper builds a C project with the installed include library, the produced
program is executed and the packaged mkc_check_* helpers are exercised.
"""
import os

from conan import ConanFile


class MkcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        mkc_pkg = self.dependencies["mkc"].package_folder
        script = os.path.join(self.recipe_folder, "test.sh")
        self.output.info(f"mkc package folder: {mkc_pkg}")
        # "conanbuild" first: the test compiles and links a real program with
        # the clang from the profile build env (its ld.lld + libs are on that
        # PATH); "conanrun" adds the runtime environment of the dependencies.
        self.run(
            f'MKC_PKG="{mkc_pkg}" sh "{script}"',
            env=["conanbuild", "conanrun"],
        )
