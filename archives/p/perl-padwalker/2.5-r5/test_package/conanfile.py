#!/usr/bin/env python3
"""Conan test_package — perl-padwalker 2.5-r5 (Perl XS module)

Verifies PadWalker.so is a valid ELF with the boot_PadWalker XS entry
point symbol. Uses readelf instead of dlopen because PadWalker.so has
unresolved Perl interpreter symbols (Perl_safesysmalloc etc.) that
require the Perl runtime to resolve at load time.
"""
import os

from conan import ConanFile


class PerlPadwalkerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate PadWalker.so in the package folder
        pkg_dir = self.dependencies[self.tested_reference_str].package_folder
        so_path = None

        for root, dirs, files in os.walk(pkg_dir):
            for f in files:
                if f == "PadWalker.so":
                    so_path = os.path.join(root, f)
                    break
            if so_path:
                break

        assert so_path, "PadWalker.so not found in package"

        self.output.info(f"Testing PadWalker.so at: {so_path}")

        # Run readelf-based verification script
        test_script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f'sh "{test_script}" "{so_path}"', env="conanrun")
