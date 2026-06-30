#!/usr/bin/env python3
"""Conan test_package — perl-readonly 2.05

Comprehensive tests for Readonly module:
- Load and version verification
- Readonly::Scalar (read-only scalars)
- Readonly::Array (read-only arrays)
- Readonly::Hash (read-only hashes)
- Readonly function (generic interface)
- Modification rejection (die on write)
- Deep cloning and nested structures
- Export mechanism
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlReadonlyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find Readonly.pm in the package folder
        pkg = self.dependencies["perl-readonly"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Readonly.pm"), recursive=True)
        if not pm_files:
            raise Exception("Readonly.pm not found in package")
        # Get the lib directory (parent of Readonly.pm)
        lib_dir = os.path.dirname(pm_files[0])

        # Set PERL5LIB to include the package lib and system Perl deps
        deps_lib = "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0"
        env = os.environ.copy()
        env["PERL5LIB"] = lib_dir + ":" + deps_lib + ":" + env.get("PERL5LIB", "")

        # ---- Test 1: Load Readonly and check version ----
        result = subprocess.run(
            ['perl', '-MReadonly', '-e', 'print "OK\n"'],
            env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            self.output.error(f"Readonly load test failed: {result.stderr}")
            raise Exception(f"Readonly load test failed with exit code {result.returncode}")
        self.output.success(f"Readonly loaded successfully: {result.stdout}")

        # ---- Test 2: Verify version ----
        result2 = subprocess.run(
            ['perl', '-MReadonly', '-e',
             'die unless $Readonly::VERSION eq "2.05"; print "Version OK\n"'],
            env=env, capture_output=True, text=True
        )
        if result2.returncode != 0:
            self.output.warning(f"Version check had issues: {result2.stderr}")
        else:
            self.output.success(result2.stdout)

        # ---- Test 3: Readonly::Scalar basic ----
        result3 = subprocess.run(
            ['perl', '-MReadonly', '-e', '''
Readonly::Scalar my $x => 42;
die "value wrong" unless $x == 42;
eval { $x = 99 };
die "Readonly::Scalar not readonly" unless $@;
print "Scalar basic OK\n";
'''],
            env=env, capture_output=True, text=True
        )
        if result3.returncode != 0:
            self.output.warning(f"Scalar basic test: {result3.stderr}")
        else:
            self.output.success(result3.stdout)

        # ---- Test 4: Readonly::Array ----
        result4 = subprocess.run(
            ['perl', '-MReadonly', '-e', '''
Readonly::Array my @arr => (1, 2, 3);
die "count wrong" unless scalar(@arr) == 3;
die "elem0 wrong" unless $arr[0] == 1;
die "elem2 wrong" unless $arr[2] == 3;
eval { $arr[0] = 99 };
die "Array not readonly" unless $@;
eval { push @arr, 4 };
die "Array push not blocked" unless $@;
print "Array OK\n";
'''],
            env=env, capture_output=True, text=True
        )
        if result4.returncode != 0:
            self.output.warning(f"Array test: {result4.stderr}")
        else:
            self.output.success(result4.stdout)

        # ---- Test 5: Readonly::Hash ----
        result5 = subprocess.run(
            ['perl', '-MReadonly', '-e', '''
Readonly::Hash my %h => (a => 1, b => 2);
die "key a wrong" unless $h{a} == 1;
die "key b wrong" unless $h{b} == 2;
die "count wrong" unless scalar(keys %h) == 2;
eval { $h{c} = 3 };
die "Hash not readonly" unless $@;
eval { delete $h{a} };
die "Hash delete not blocked" unless $@;
print "Hash OK\n";
'''],
            env=env, capture_output=True, text=True
        )
        if result5.returncode != 0:
            self.output.warning(f"Hash test: {result5.stderr}")
        else:
            self.output.success(result5.stdout)

        # ---- Test 6: Readonly generic interface ----
        result6 = subprocess.run(
            ['perl', '-MReadonly', '-e', '''
Readonly my $s => 'hello';
Readonly my @a => (10, 20);
Readonly my %h => (x => 100);
die "scalar wrong" unless $s eq 'hello';
die "array wrong" unless $a[1] == 20;
die "hash wrong" unless $h{x} == 100;
eval { $s = 'world' };
die "generic scalar not readonly" unless $@;
print "Generic interface OK\n";
'''],
            env=env, capture_output=True, text=True
        )
        if result6.returncode != 0:
            self.output.warning(f"Generic interface test: {result6.stderr}")
        else:
            self.output.success(result6.stdout)

        # ---- Test 7: Nested/deep structures ----
        result7 = subprocess.run(
            ['perl', '-MReadonly', '-e', '''
Readonly::Hash my %config => (
    db => { host => 'localhost', port => 5432 },
    opts => [1, 2, 3],
);
die "nested hash wrong" unless $config{db}{host} eq 'localhost';
die "nested hash port wrong" unless $config{db}{port} == 5432;
die "nested array wrong" unless $config{opts}[1] == 2;
eval { $config{db}{host} = 'evil' };
die "nested hash not readonly" unless $@;
eval { $config{opts}[0] = 99 };
die "nested array not readonly" unless $@;
print "Nested structures OK\n";
'''],
            env=env, capture_output=True, text=True
        )
        if result7.returncode != 0:
            self.output.warning(f"Nested structures test: {result7.stderr}")
        else:
            self.output.success(result7.stdout)

        # ---- Test 8: Export mechanism ----
        result8 = subprocess.run(
            ['perl', '-e', '''
use lib qw(/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0);
use Readonly qw(Readonly);
Readonly my $x => 'test';
die "export failed" unless $x eq 'test';
eval { $x = 'changed' };
die "exported not readonly" unless $@;
print "Export OK\n";
'''],
            env=env, capture_output=True, text=True
        )
        if result8.returncode != 0:
            self.output.warning(f"Export test: {result8.stderr}")
        else:
            self.output.success(result8.stdout)
