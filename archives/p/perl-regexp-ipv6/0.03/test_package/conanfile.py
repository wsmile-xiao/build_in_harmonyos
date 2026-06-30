#!/usr/bin/env python3
"""Conan test_package — Perl smoke test for Regexp::IPv6.

Verifies that the module can be loaded and the $IPv6_re regex works.
"""
import os
import subprocess

from conan import ConanFile


class PerlRegexpIPv6TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a pure Perl smoke test

    def test(self):
        # Get the package's lib/perl5 directory from PERL5LIB
        perllib = []
        for dep in self.dependencies.values():
            perllib.append(os.path.join(dep.package_folder, "lib", "perl5"))
        # Also add system site_perl (query perl at runtime for portability)
        sys_site = subprocess.run(
            ["perl", "-e", "use Config; print $Config{sitelib}"],
            capture_output=True, text=True
        )
        if sys_site.returncode == 0 and sys_site.stdout.strip():
            perllib.append(sys_site.stdout.strip())
        perl5lib = ":".join(perllib)

        # Test 1: Module loads successfully
        env = os.environ.copy()
        env["PERL5LIB"] = perl5lib
        result = subprocess.run(
            ["perl", "-MRegexp::IPv6", "-e", "1"],
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise Exception(f"Failed to load Regexp::IPv6: {result.stderr}")
        self.output.info("✅ Regexp::IPv6 loaded successfully")

        # Test 2: IPv6 regex works on a valid address
        result = subprocess.run(
            ["perl", "-MRegexp::IPv6", "-e",
             "use Regexp::IPv6 qw($IPv6_re); "
             "exit(1) unless '2001:db8::1' =~ /^$IPv6_re$/; "
             "exit(0)"],
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise Exception(f"IPv6 regex test failed: {result.stderr}")
        self.output.info("✅ IPv6 regex matches valid address '2001:db8::1'")

        # Test 3: IPv6 regex rejects invalid address
        result = subprocess.run(
            ["perl", "-MRegexp::IPv6", "-e",
             "use Regexp::IPv6 qw($IPv6_re); "
             "exit(0) if 'not-an-ipv6-address' !~ /^$IPv6_re$/; "
             "exit(1)"],
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise Exception(f"IPv6 regex should reject invalid address: {result.stderr}")
        self.output.info("✅ IPv6 regex rejects invalid address")
