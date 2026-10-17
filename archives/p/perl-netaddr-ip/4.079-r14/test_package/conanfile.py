#!/usr/bin/env python3
"""Conan test_package for perl-netaddr-ip 4.079-r14.

Tests that the Perl XS module NetAddr::IP can be loaded and used.
This is the L1 test in the five-level test system.
"""
import os
import shutil

from conan import ConanFile


class PerlNetAddrIPTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for Perl module test

    def test(self):
        # Get the Perl lib directory from the dependency package
        dep = self.dependencies["perl-netaddr-ip"]
        pkg_dir = dep.package_folder
        perl_lib_dir = os.path.join(pkg_dir, "lib", "aarch64-linux")

        # --- L1: Binary integrity check (same as 4.079) ---
        so_found = False
        for root, dirs, files in os.walk(pkg_dir):
            for f in files:
                if f.endswith(".so"):
                    so_path = os.path.join(root, f)
                    self.output.info(f"Found .so: {so_path}")
                    so_found = True
                    with open(so_path, "rb") as fh:
                        magic = fh.read(4)
                        assert magic == b'\x7fELF', f"{f} is not a valid ELF file"
                        self.output.info(f"ELF check passed for {f}")
        assert so_found, "No .so file found in package"

        # --- L2: Functional test (load + use) ---
        # The system-installed Socket6 module is broken (missing gethostbyname2/
        # getipnodebyname exports). Remove site_perl from @INC so Util.pm
        # gracefully falls back to standard gethostbyname (its designed behavior).
        # Copy static test source to build folder and run it.
        test_src = os.path.join(self.recipe_folder, "test_netaddr_ip.pl")
        test_file = os.path.join(self.build_folder, "test_netaddr_ip.pl")
        try:
            shutil.copy2(test_src, test_file)
        except shutil.SameFileError:
            pass  # build_folder == recipe_folder, file already in place

        # Set PERL5LIB to the package's Perl lib directory only
        os.environ["PERL5LIB"] = perl_lib_dir

        self.run(f"perl {test_file}")
