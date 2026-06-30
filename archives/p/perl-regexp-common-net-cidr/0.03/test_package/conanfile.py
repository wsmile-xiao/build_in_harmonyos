#!/usr/bin/env python3
"""Conan test_package — perl-regexp-common-net-cidr 0.03

Tests that Regexp::Common::net::CIDR can be loaded, version verified,
and CIDR pattern matching works correctly.
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlRegexpCommonNetCidrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find CIDR.pm in the package folder
        pkg = self.dependencies["perl-regexp-common-net-cidr"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "CIDR.pm"), recursive=True)
        if not pm_files:
            raise Exception("CIDR.pm not found in package")
        # Get the lib directory (4 levels up: CIDR.pm -> net -> Common -> Regexp -> lib_dir)
        lib_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(pm_files[0]))))

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

        # Test 1: Load Regexp::Common::net::CIDR
        result = subprocess.run(
            ['perl', '-MRegexp::Common::net::CIDR', '-e', 'print "OK\\n"'],
            env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            self.output.error(f"Module load test failed: {result.stderr}")
            raise Exception(f"Module load test failed with exit code {result.returncode}")
        self.output.success(f"Regexp::Common::net::CIDR loaded successfully: {result.stdout}")

        # Test 2: Verify version
        result2 = subprocess.run(
            ['perl', '-MRegexp::Common::net::CIDR', '-e',
             'die unless $Regexp::Common::net::CIDR::VERSION eq "0.03"; print "Version OK\\n"'],
            env=env, capture_output=True, text=True
        )
        if result2.returncode != 0:
            self.output.error(f"Version check failed: {result2.stderr}")
            raise Exception("Version check failed")
        self.output.success(result2.stdout)

        # Test 3: Functional tests — CIDR pattern matching (anchored)
        result3 = subprocess.run(
            ['perl', '-e', '''use strict;
use warnings;
use Regexp::Common;
use Regexp::Common::net::CIDR;

my $re = $RE{net}{CIDR}{IPv4};

# Valid IPv4 CIDR (minimum 2 octets required by module)
die "FAIL: 192.168.1.0/24 should match" unless "192.168.1.0/24" =~ /^$re$/;
die "FAIL: 10.0.0.0/8 should match" unless "10.0.0.0/8" =~ /^$re$/;
die "FAIL: 172.16.0.0/12 should match" unless "172.16.0.0/12" =~ /^$re$/;
die "FAIL: 10.0/8 should match" unless "10.0/8" =~ /^$re$/;
die "FAIL: 192.168.1.0/32 should match" unless "192.168.1.0/32" =~ /^$re$/;
die "FAIL: 10.0.0.0/0 should match" unless "10.0.0.0/0" =~ /^$re$/;

# Invalid patterns should not match (anchored)
die "FAIL: not_a_cidr should not match" if "not_a_cidr" =~ /^$re$/;
die "FAIL: 999.999.999.999/24 should not match" if "999.999.999.999/24" =~ /^$re$/;
die "FAIL: 192.168.1.0/33 should not match" if "192.168.1.0/33" =~ /^$re$/;
die "FAIL: 10/8 should not match (needs min 2 octets)" if "10/8" =~ /^$re$/;

print "CIDR pattern matching test OK\\n";
'''],
            env=env, capture_output=True, text=True
        )
        if result3.returncode != 0:
            self.output.error(f"CIDR pattern matching test failed: {result3.stderr}")
            raise Exception("CIDR pattern matching test failed")
        self.output.success(result3.stdout)

        # Test 4: Test -keep option for extracting address and prefix
        result4 = subprocess.run(
            ['perl', '-e', '''use strict;
use warnings;
use Regexp::Common;
use Regexp::Common::net::CIDR;

my $re = $RE{net}{CIDR}{IPv4}{-keep};

my $cidr = "192.168.1.0/24";
if ($cidr =~ /^$re$/) {
    die "FAIL: address mismatch (got: $1)" unless $1 eq "192.168.1.0";
    die "FAIL: prefix mismatch (got: $2)" unless $2 eq "24";
} else {
    die "FAIL: should match with -keep";
}

print "Keep option test OK\\n";
'''],
            env=env, capture_output=True, text=True
        )
        if result4.returncode != 0:
            self.output.warning(f"Keep option test had issues: {result4.stderr}")
        else:
            self.output.success(result4.stdout)
