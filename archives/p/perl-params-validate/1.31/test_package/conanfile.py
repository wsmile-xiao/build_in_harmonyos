#!/usr/bin/env python3
"""Conan test_package for perl-params-validate — Perl L1 test.

Verifies that the XS.so is present, is a valid ELF, and has the boot function.
Attempts to load Params::Validate (PP fallback via Module::Implementation).
Runtime .so loading may fail due to SELinux/HMDFS — PP fallback is expected.
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanException


class TestPerlParamsValidate(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-params-validate"]
        pkg_folder = dep.package_folder

        # .pm files in site_perl/{version}/ (arch-independent)
        # .so files in site_perl/{version}/{arch}/ (arch-specific)
        # Dynamically find paths (avoid hardcoding Perl version/arch).
        so_candidates = glob.glob(os.path.join(
            pkg_folder, "**", "auto", "Params", "Validate", "XS", "XS.so"
        ), recursive=True)
        assert so_candidates, f"XS.so not found in package: {pkg_folder}"
        so_path = so_candidates[0]

        # Derive site_arch and site_lib from the found .so path.
        # so_path: .../site_perl/{ver}/{arch}/auto/Params/Validate/XS/XS.so
        # site_arch: .../site_perl/{ver}/{arch}/
        # site_lib:  .../site_perl/{ver}/
        site_arch = os.path.dirname(
            os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.dirname(so_path))
            ))
        )
        site_lib = os.path.dirname(site_arch)

        # Use self.run for CI L0d compliance (requires self.run in test())
        self.run(f'file "{so_path}"')
        self.run(f'readelf --dyn-syms --wide "{so_path}" | grep boot_Params__Validate__XS')

        # --- L1: Try loading Params::Validate via test.sh ---
        # Set PERL5LIB so Perl can find .pm files (site_lib) and .so (site_arch).
        # Also add user's local perl5 lib for runtime dependencies
        # (Module::Implementation, Try::Tiny, etc.).
        home = os.path.expanduser("~")
        local_perl5_candidates = [
            # ~/usr/local/lib/perl5/ — where CPAN modules like
            # Module::Implementation, Module::Runtime are installed.
            # CI workers use /bin/sh (no .bash_profile), so PERL5LIB
            # is not set by default — we must add these paths explicitly.
            os.path.join(home, "usr", "local", "lib", "perl5",
                         "aarch64-linux"),
            os.path.join(home, "usr", "local", "lib", "perl5"),
            os.path.join(home, "usr", "local", "lib", "perl5",
                         "site_perl", "5.42.0", "aarch64-linux"),
            os.path.join(home, "usr", "local", "lib", "perl5",
                         "site_perl", "5.42.0"),
            os.path.join(home, "usr", "local", "lib", "site_perl",
                         "5.42.0", "aarch64-linux"),
            os.path.join(home, "usr", "local", "lib", "site_perl", "5.42.0"),
        ]
        perl5lib_paths = [site_arch, site_lib]
        perl5lib_paths.extend(p for p in local_perl5_candidates
                              if os.path.isdir(p))

        old_perl5lib = os.environ.get("PERL5LIB", "")
        os.environ["PERL5LIB"] = ":".join(perl5lib_paths)

        try:
            # Run Perl functional test (test.sh → test.pl).
            # test.sh handles perl binary detection internally.
            # If test fails due to HMDFS/SELinux (expected on HarmonyOS),
            # skip with warning. All other failures are real test failures.
            test_script = os.path.join(self.source_folder, "test.sh")
            try:
                self.run(f'sh "{test_script}"')
                self.output.info("✅ Params::Validate PP mode test passed")
            except ConanException as e:
                err_str = str(e).lower()
                # Skip only if .so loading is blocked by HMDFS/SELinux
                # (platform restriction). Require BOTH a loading failure
                # indicator AND a platform error to avoid false positives.
                load_failure = any(kw in err_str for kw in (
                    "can't load", "dlopen", "shared object"
                ))
                platform_error = any(kw in err_str for kw in (
                    "permission denied", "operation not permitted",
                    "hmdfs", "selinux"
                ))
                if load_failure and platform_error:
                    self.output.warning(
                        "⚠️ Runtime test failed "
                        "(expected on HarmonyOS HMDFS/SELinux)"
                    )
                else:
                    raise
        finally:
            os.environ["PERL5LIB"] = old_perl5lib
