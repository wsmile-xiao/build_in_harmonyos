#!/usr/bin/env python3
"""Conan test_package for perl-scope-upper 0.34 (Scope::Upper).

L1 test: verify the Perl module files are present and valid.
Note: .so loading is restricted on HarmonyOS due to SELinux file context
(.so in hmdfs context cannot be dlopen'd; requires hnp_file context via
installation to system perl path). File-based verification is used instead.

Scope::Upper uses XSLoader::load() inside a BEGIN block, so `perl -c`
triggers dlopen and fails with Permission denied. We use file verification
and content checks instead of syntax checking.
"""
import os

from conan import ConanFile


class PerlScopeUpperTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["perl-scope-upper"]
        pkg = dep.package_folder

        perl_arch = "aarch64-linux" if str(self.settings.arch) in ("armv8", "aarch64") else "x86_64-linux"
        perl_ver = "5.42.0"
        lib_dir = os.path.join(pkg, "data", "service", "hnp", "perl.org",
                               f"perl_{perl_ver}", "lib", "site_perl",
                               perl_ver, perl_arch)

        # 1. Verify .pm file exists
        upper_pm = os.path.join(lib_dir, "Scope", "Upper.pm")
        assert os.path.exists(upper_pm), f"Upper.pm not found: {upper_pm}"

        # 2. Verify .pm content (version string check, avoids XSLoader/dlopen)
        with open(upper_pm, "r") as f:
            pm_content = f.read()
        assert "0.34" in pm_content, "Version 0.34 not found in Upper.pm"
        assert "Scope::Upper" in pm_content, "Scope::Upper package name not found"
        assert "XSLoader" in pm_content, "XSLoader not referenced in Upper.pm"

        # 3. Verify .so exists and is valid ELF
        upper_so = os.path.join(lib_dir, "auto", "Scope", "Upper", "Upper.so")
        assert os.path.exists(upper_so), f"Upper.so not found: {upper_so}"
        with open(upper_so, "rb") as f:
            magic = f.read(4)
            assert magic == b"\x7fELF", f"Upper.so is not a valid ELF file"

        # 4. Verify .so has .codesign section (HarmonyOS ELF signing)
        self.run(f'llvm-readelf -S "{upper_so}" | grep -q codesign')

        # 5. Verify .so copy in lib/ for G4 artifact discovery
        lib_so = os.path.join(pkg, "lib", "Upper.so")
        assert os.path.exists(lib_so), f"Upper.so copy not found in lib/: {lib_so}"

        # 6. Print summary
        print(f"perl-scope-upper 0.34: file verification OK")
        print(f"  Upper.pm:  {os.path.getsize(upper_pm)} bytes")
        print(f"  Upper.so:  {os.path.getsize(upper_so)} bytes (ELF aarch64, self-signed)")
        print(f"  lib/Upper.so: {os.path.getsize(lib_so)} bytes (copy for G4)")
        print(f"  Note: .so runtime load skipped — HarmonyOS SELinux context restriction")
        print(f"  Note: perl -c skipped — XSLoader in BEGIN block triggers dlopen")
