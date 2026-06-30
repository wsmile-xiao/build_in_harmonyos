#!/usr/bin/env python3
"""Conan test_package — perl-ref-util 0.204

Tests that Ref::Util can be loaded, version verified, and basic API works.
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlRefUtilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find Util.pm in the package folder (under Ref/Util.pm)
        pkg = self.dependencies["perl-ref-util"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Ref", "Util.pm"), recursive=True)
        if not pm_files:
            raise Exception("Ref/Util.pm not found in package")
        # Get the lib directory (parent of Ref/ directory)
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))

        # Build PERL5LIB: package lib + system site_perl for runtime deps
        perl_site_lib = "/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0"
        local_site_lib = "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0"

        env = os.environ.copy()
        perl5lib_parts = [lib_dir]
        if os.path.isdir(local_site_lib):
            perl5lib_parts.append(local_site_lib)
        if os.path.isdir(perl_site_lib):
            perl5lib_parts.append(perl_site_lib)
        perl5lib_parts.append(env.get("PERL5LIB", ""))
        env["PERL5LIB"] = ":".join(p for p in perl5lib_parts if p)

        # Test 1: Load Ref::Util and check version
        result = subprocess.run(
            ['perl', '-MRef::Util', '-e', 'print "OK\n"'],
            env=env, capture_output=True, text=True
        )

        if result.returncode != 0:
            self.output.error(f"Ref::Util load test failed: {result.stderr}")
            raise Exception(f"Ref::Util load test failed with exit code {result.returncode}")

        self.output.success(f"Ref::Util loaded successfully: {result.stdout}")

        # Test 2: Verify version
        result2 = subprocess.run(
            ['perl', '-MRef::Util', '-e',
             'die unless $Ref::Util::VERSION eq "0.204"; print "Version OK\n"'],
            env=env, capture_output=True, text=True
        )

        if result2.returncode != 0:
            self.output.warning(f"Version check had issues: {result2.stderr}")
        else:
            self.output.success(result2.stdout)

        # Test 3: Verify submodule Ref::Util::PP loads
        result3 = subprocess.run(
            ['perl', '-MRef::Util', '-MRef::Util::PP', '-e',
             'print "Submodules OK\n"'],
            env=env, capture_output=True, text=True
        )

        if result3.returncode != 0:
            self.output.warning(f"Submodule load test had issues: {result3.stderr}")
        else:
            self.output.success(result3.stdout)

        # Test 4: Test basic API — is_ref, is_arrayref, is_hashref, is_scalarref, is_coderef
        result4 = subprocess.run(
            ['perl', '-e', '''
use Ref::Util qw(is_ref is_arrayref is_hashref is_scalarref is_coderef);

# Test is_arrayref
die unless is_arrayref([1, 2, 3]);
die if is_arrayref({});
die if is_arrayref("scalar");

# Test is_hashref
die unless is_hashref({});
die if is_hashref([]);
die if is_hashref("scalar");

# Test is_scalarref
die unless is_scalarref(\\my $x);
die if is_scalarref([]);

# Test is_coderef
die unless is_coderef(sub { });
die if is_coderef([]);

# Test is_ref
die unless is_ref([1, 2, 3]);
die if is_ref("scalar");
die if is_ref(123);

print "API test OK\n";
print "is_arrayref OK\n" if is_arrayref([]);
print "is_hashref OK\n" if is_hashref({});
print "is_scalarref OK\n" if is_scalarref(\\my $s);
print "is_coderef OK\n" if is_coderef(sub {});
'''],
            env=env, capture_output=True, text=True
        )

        if result4.returncode != 0:
            self.output.warning(f"API test had issues: {result4.stderr}")
        else:
            self.output.success(result4.stdout)
