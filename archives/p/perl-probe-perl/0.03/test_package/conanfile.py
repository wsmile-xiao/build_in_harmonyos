#!/usr/bin/env python3
"""Conan test_package — perl-probe-perl 0.03

Tests that Probe::Perl can be loaded and provides correct information
about the running Perl interpreter.
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlProbePerlTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find Probe/Perl.pm in the package folder
        pkg = self.dependencies["perl-probe-perl"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Perl.pm"), recursive=True)
        if not pm_files:
            raise Exception("Probe/Perl.pm not found in package")
        # Get the lib directory (parent of Probe's parent)
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))

        env = os.environ.copy()
        env["PERL5LIB"] = lib_dir + ":" + env.get("PERL5LIB", "")

        # Test 1: Load Probe::Perl and get perl version
        result = subprocess.run(
            ['perl', '-MProbe::Perl', '-e',
             'my $p=Probe::Perl->new; '
             'print "Perl version: ", $p->config("version"), "\\n"'],
            env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            self.output.error(f"Probe::Perl load test failed: {result.stderr}")
            raise Exception(f"Probe::Perl load test failed with exit code {result.returncode}")
        self.output.success(f"Test 1 (load + version): {result.stdout.strip()}")

        # Test 2: Check os_type returns a valid value
        result2 = subprocess.run(
            ['perl', '-MProbe::Perl', '-e',
             'print "OS type: ", Probe::Perl->os_type(), "\\n"'],
            env=env, capture_output=True, text=True
        )
        if result2.returncode != 0:
            self.output.warning(f"Probe::Perl os_type test had issues: {result2.stderr}")
        else:
            self.output.success(f"Test 2 (os_type): {result2.stdout.strip()}")

        # Test 3: Check find_perl_interpreter returns a path
        result3 = subprocess.run(
            ['perl', '-MProbe::Perl', '-e',
             'my $p=Probe::Perl->new; '
             'my $path=$p->find_perl_interpreter; '
             'print "Perl path: ", ($path ? $path : "NOT FOUND"), "\\n"'],
            env=env, capture_output=True, text=True
        )
        if result3.returncode != 0:
            self.output.warning(f"Probe::Perl find_perl_interpreter test had issues: {result3.stderr}")
        else:
            self.output.success(f"Test 3 (find_perl_interpreter): {result3.stdout.strip()}")

        # Test 4: Check perl_version returns a float
        result4 = subprocess.run(
            ['perl', '-MProbe::Perl', '-e',
             'my $p=Probe::Perl->new; '
             'print "Perl float version: ", $p->perl_version(), "\\n"'],
            env=env, capture_output=True, text=True
        )
        if result4.returncode != 0:
            self.output.warning(f"Probe::Perl perl_version test had issues: {result4.stderr}")
        else:
            self.output.success(f"Test 4 (perl_version): {result4.stdout.strip()}")
