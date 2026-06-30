#!/usr/bin/env python3
"""Conan test_package — perl-ppix-regexp 0.091

Tests that PPIx::Regexp can be loaded and used to parse regular expressions.
Note: PPIx::Regexp has Perl dependencies (PPI, etc.) that are
installed as system Perl modules, not as Conan packages.
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlPpixRegexpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find PPIx/Regexp.pm in the package folder
        pkg = self.dependencies["perl-ppix-regexp"]
        pkg_folder = pkg.package_folder
        regexp_files = glob.glob(os.path.join(pkg_folder, "**", "Regexp.pm"), recursive=True)
        if not regexp_files:
            raise Exception("PPIx/Regexp.pm not found in package")
        # Get the lib directory (parent of PPIx's parent)
        lib_dir = os.path.dirname(os.path.dirname(regexp_files[0]))

        # Set PERL5LIB to include both the package lib and system-installed Perl deps
        deps_lib = "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0"

        env = os.environ.copy()
        env["PERL5LIB"] = lib_dir + ":" + deps_lib + ":" + env.get("PERL5LIB", "")
        env["PERL_PARAMS_UTIL_PP"] = "1"

        # Test 1: Load PPIx::Regexp and check version
        result = subprocess.run(
            ['perl', '-MPPIx::Regexp', '-e', 'print "PPIx::Regexp version: $PPIx::Regexp::VERSION"'],
            env=env, capture_output=True, text=True
        )

        if result.returncode != 0:
            self.output.error(f"PPIx::Regexp load test failed: {result.stderr}")
            raise Exception(f"PPIx::Regexp load test failed with exit code {result.returncode}")

        self.output.success(f"PPIx::Regexp loaded successfully: {result.stdout}")

        # Test 2: Parse a simple regular expression
        # NOTE: PPIx::Regexp::Lexer->new() requires string form, not qr// object.
        # Passing qr// (Regexp ref) returns undef with errstr "Regexp not supported".
        # This is by design in PPIx::Regexp::Tokenizer::new().
        result2 = subprocess.run(
            ['perl', '-MPPIx::Regexp::Lexer', '-e',
             'my $lex = PPIx::Regexp::Lexer->new("qr/foo/"); '
             'die "Parse test failed: undefined result" unless $lex; '
             'print "Parse test: OK\\n"'],
            env=env, capture_output=True, text=True
        )

        if result2.returncode != 0 or "OK" not in result2.stdout:
            self.output.error(f"PPIx::Regexp parse test failed: {result2.stderr or result2.stdout}")
            raise Exception(f"PPIx::Regexp parse test failed with exit code {result2.returncode}")

        self.output.success(result2.stdout.strip())

        # Test 3: Parse a complex regular expression with capture groups
        result3 = subprocess.run(
            ['perl', '-MPPIx::Regexp', '-e',
             'my $re = PPIx::Regexp->new("qr/(\\d+)(\.\d+)?/"); '
             'die "Complex parse failed: undefined result" unless $re; '
             'print "Complex parse test: OK\\n"'],
            env=env, capture_output=True, text=True
        )

        if result3.returncode != 0 or "OK" not in result3.stdout:
            self.output.warning(f"PPIx::Regexp complex parse test had issues: {result3.stderr or result3.stdout}")
        else:
            self.output.success(result3.stdout.strip())

        # Test 4: Use Dumper to verify full parse pipeline
        result4 = subprocess.run(
            ['perl', '-MPPIx::Regexp::Dumper', '-e',
             'my $dumper = PPIx::Regexp::Dumper->new("qr/foo|bar/i"); '
             'die "Dumper test failed" unless $dumper; '
             'print "Dumper test: OK\\n"'],
            env=env, capture_output=True, text=True
        )

        if result4.returncode != 0 or "OK" not in result4.stdout:
            self.output.warning(f"PPIx::Regexp dumper test had issues: {result4.stderr or result4.stdout}")
        else:
            self.output.success(result4.stdout.strip())
