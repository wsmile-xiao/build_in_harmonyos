#!/usr/bin/env python3
"""Conan test_package — Package::Anon (Perl XS module)

L1 test: Verify the Perl module files are properly installed.
On OHOS, loading .so on HMDFS is blocked by SELinux (E046).
This test verifies:
  1. File existence (.pm and .so)
  2. ELF integrity of .so (via self.run("file ..."))
  3. Dynamic dependencies check (via self.run("readelf -d ..."))
  4. Perl module functional test (via test.sh → test.pl)
     On OHOS HMDFS, .so loading is blocked by SELinux → test.sh skips gracefully.
"""
import os

from conan import ConanFile


class PerlpackageanonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed

    def test(self):
        # Get the package folder from the dependency
        dep = self.dependencies["perl-package-anon"]
        pkg_root = dep.package_folder
        perl_lib = os.path.join(pkg_root,
                                "data", "service", "hnp", "perl.org",
                                "perl_5.42.0", "lib", "site_perl", "5.42.0", "aarch64-linux")

        # 1. Verify .pm file exists
        pm_file = os.path.join(perl_lib, "Package", "Anon.pm")
        assert os.path.exists(pm_file), f"Package/Anon.pm not found at {pm_file}"
        print(f"Found: {pm_file}")

        # 2. Verify .so file exists
        so_file = os.path.join(perl_lib, "auto", "Package", "Anon", "Anon.so")
        assert os.path.exists(so_file), f"Anon.so not found at {so_file}"
        print(f"Found: {so_file}")

        # 3. Verify .so is a valid ELF file
        self.run(f"file {so_file}")

        # 4. Check dynamic dependencies
        self.run(f"readelf -d {so_file}")

        # 5. Perl module functional test via test.sh (runs test.pl)
        # test.sh handles SELinux HMDFS restriction gracefully (exit 0)
        # Unexpected failures (ABI mismatch, missing symbols) cause exit 1
        self.run(f'export PERL5LIB="{perl_lib}" && bash test.sh', cwd=self.source_folder)

        print("test perl-package-anon 0.05-r16: OK (file existence + ELF + deps + functional test)")
