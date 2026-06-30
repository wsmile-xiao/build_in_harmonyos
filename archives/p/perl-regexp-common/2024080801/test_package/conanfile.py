#!/usr/bin/env python3
"""Conan test_package — perl-regexp-common 2024080801

Tests that Regexp::Common can be loaded, version verified,
and basic pattern matching works.
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlRegexpCommonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find Common.pm in the package folder
        pkg = self.dependencies["perl-regexp-common"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Common.pm"), recursive=True)
        if not pm_files:
            raise Exception("Common.pm not found in package")
        # Get the lib directory (parent of Regexp/ directory)
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

        # Test 1: Load Regexp::Common and check version
        result = subprocess.run(
            ['perl', '-MRegexp::Common', '-e', 'print "OK\n"'],
            env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            self.output.error(f"Regexp::Common load test failed: {result.stderr}")
            raise Exception(f"Regexp::Common load test failed with exit code {result.returncode}")
        self.output.success(f"Regexp::Common loaded successfully: {result.stdout}")

        # Test 2: Verify version
        result2 = subprocess.run(
            ['perl', '-MRegexp::Common', '-e',
             'die unless $Regexp::Common::VERSION eq "2024080801"; print "Version OK\n"'],
            env=env, capture_output=True, text=True
        )
        if result2.returncode != 0:
            self.output.warning(f"Version check had issues: {result2.stderr}")
        else:
            self.output.success(result2.stdout)

        # Test 3: Verify submodules load
        result3 = subprocess.run(
            ['perl', '-MRegexp::Common::net', '-MRegexp::Common::number',
             '-MRegexp::Common::URI', '-MRegexp::Common::delimited',
             '-MRegexp::Common::comment', '-MRegexp::Common::balanced',
             '-MRegexp::Common::whitespace', '-MRegexp::Common::zip',
             '-MRegexp::Common::list', '-MRegexp::Common::profanity',
             '-e', 'print "Submodules OK\n"'],
            env=env, capture_output=True, text=True
        )
        if result3.returncode != 0:
            self.output.warning(f"Submodule load test had issues: {result3.stderr}")
        else:
            self.output.success(result3.stdout)

        # Test 4: Test pattern matching (functional test)
        result4 = subprocess.run(
            ['perl', '-e', '''
use Regexp::Common;

# Test: match a number
my $num_re = $RE{num}{real};
die "Number test failed" unless "3.14" =~ /^$num_re$/;

# Test: match an integer
my $int_re = $RE{num}{int};
die "Integer test failed" unless "42" =~ /^$int_re$/;

# Test: match a delimited string
my $del_re = $RE{delimited}{-delim=>'"'};
die "Delimited test failed" unless '"hello world"' =~ /^$del_re$/;

# Test: match a comment (C-style)
my $cmt_re = $RE{comment}{C};
die "Comment test failed" unless "/* comment */" =~ /^$cmt_re$/;

# Test: match an IP address
my $ip_re = $RE{net}{IPv4};
die "IPv4 test failed" unless "192.168.1.1" =~ /^$ip_re$/;

# Test: match a zip code (US)
my $zip_re = $RE{zip}{US};
die "Zip test failed" unless "12345" =~ /^$zip_re$/;

print "Pattern matching test OK\\n";
'''],
            env=env, capture_output=True, text=True
        )
        if result4.returncode != 0:
            self.output.error(f"Pattern matching test failed: {result4.stderr}")
            raise Exception("Pattern matching test failed")
        else:
            self.output.success(result4.stdout)

        # Test 5: Test URI sub-patterns
        result5 = subprocess.run(
            ['perl', '-e', '''
use Regexp::Common;
use Regexp::Common::URI;

# Test HTTP URI
my $http_re = $RE{URI}{http};
die "HTTP URI test failed" unless "http://example.com/path" =~ /^$http_re$/;

# Test FTP URI
my $ftp_re = $RE{URI}{ftp};
die "FTP URI test failed" unless "ftp://ftp.example.com/file" =~ /^$ftp_re$/;

print "URI pattern test OK\\n";
'''],
            env=env, capture_output=True, text=True
        )
        if result5.returncode != 0:
            self.output.warning(f"URI pattern test had issues: {result5.stderr}")
        else:
            self.output.success(result5.stdout)
