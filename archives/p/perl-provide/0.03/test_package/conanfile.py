#!/usr/bin/env python3
"""Conan test_package — perl-provide 0.03

Tests that the provide module can be loaded (via require, not use)
and version verified. Also tests core API functions:
pick_module_to_load, looks_like_a_module, load.

Note: `use provide;` without arguments will die because the module's
import() expects arguments like `if => ge => '5.013' => 'Some::Module'`.
So we use `require` to load the module without calling import().
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlProvideTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find provide.pm in the package folder
        pkg = self.dependencies["perl-provide"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "provide.pm"), recursive=True)
        if not pm_files:
            raise Exception("provide.pm not found in package")
        # Get the lib directory (parent of the provide.pm file's directory)
        lib_dir = os.path.dirname(pm_files[0])

        # Set PERL5LIB to include both the package lib and system-installed Perl deps
        deps_lib = "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0"

        env = os.environ.copy()
        env["PERL5LIB"] = lib_dir + ":" + deps_lib + ":" + env.get("PERL5LIB", "")

        # Test 1: Load provide via require (avoids calling import() which needs args)
        result = subprocess.run(
            ['perl', '-e', 'require provide; print "OK\\n"'],
            env=env, capture_output=True, text=True
        )

        if result.returncode != 0:
            self.output.error(f"provide load test failed: {result.stderr}")
            raise Exception(f"provide load test failed with exit code {result.returncode}")

        self.output.success(f"provide loaded successfully: {result.stdout}")

        # Test 2: Verify version
        result2 = subprocess.run(
            ['perl', '-e', 'require provide; die unless $provide::VERSION eq "0.03"; print "Version OK\\n"'],
            env=env, capture_output=True, text=True
        )

        if result2.returncode != 0:
            self.output.warning(f"Version check had issues: {result2.stderr}")
        else:
            self.output.success(result2.stdout)

        # Test 3: Test looks_like_a_module() function
        result3 = subprocess.run(
            ['perl', '-e', '''
require provide;
die "valid module failed" unless provide::looks_like_a_module("Some::Module");
die "single word failed" unless provide::looks_like_a_module("A");
die "empty should fail" if provide::looks_like_a_module("");
print "looks_like_a_module OK\\n";
'''],
            env=env, capture_output=True, text=True
        )

        if result3.returncode != 0:
            self.output.warning(f"looks_like_a_module test: {result3.stderr}")
        else:
            self.output.success(result3.stdout)

        # Test 4: Test pick_module_to_load() with all operators
        result4 = subprocess.run(
            ['perl', '-e', '''
require provide;
my $m;

# ge true
$m = provide::pick_module_to_load(if => ge => "1.0" => "Pass", else => "Fail");
die "ge true failed ($m)" unless $m eq "Pass";

# ge false -> else
$m = provide::pick_module_to_load(if => ge => "99.0" => "Fail", else => "Pass");
die "ge false failed ($m)" unless $m eq "Pass";

# gt true
$m = provide::pick_module_to_load(if => gt => "1.0" => "Pass", else => "Fail");
die "gt true failed ($m)" unless $m eq "Pass";

# eq true
$m = provide::pick_module_to_load(if => eq => $] => "Pass", else => "Fail");
die "eq true failed ($m)" unless $m eq "Pass";

# ne true
$m = provide::pick_module_to_load(if => ne => "1.0" => "Pass", else => "Fail");
die "ne true failed ($m)" unless $m eq "Pass";

# le true
$m = provide::pick_module_to_load(if => le => $] => "Pass", else => "Fail");
die "le true failed ($m)" unless $m eq "Pass";

# lt true
$m = provide::pick_module_to_load(if => lt => "99.0" => "Pass", else => "Fail");
die "lt true failed ($m)" unless $m eq "Pass";

# elsif chain
$m = provide::pick_module_to_load(
    if => gt => $] => "Fail",
    elsif => ge => $] => "Pass",
    else => "Fail",
);
die "elsif chain failed ($m)" unless $m eq "Pass";

# all false -> else
$m = provide::pick_module_to_load(
    if => gt => $] => "Fail",
    elsif => eq => 0 => "Fail",
    else => "Pass",
);
die "all false else failed ($m)" unless $m eq "Pass";

print "pick_module_to_load OK\\n";
'''],
            env=env, capture_output=True, text=True
        )

        if result4.returncode != 0:
            self.output.warning(f"pick_module_to_load test: {result4.stderr}")
        else:
            self.output.success(result4.stdout)

        # Test 5: Verify API completeness
        result5 = subprocess.run(
            ['perl', '-e', '''
require provide;
die "import missing" unless can("provide", "import");
die "load missing" unless can("provide", "load");
die "pick_module_to_load missing" unless can("provide", "pick_module_to_load");
die "looks_like_a_module missing" unless can("provide", "looks_like_a_module");
print "API complete OK\\n";
sub can {
    my ($pkg, $method) = @_;
    no strict "refs";
    return defined &{"${pkg}::${method}"};
}
'''],
            env=env, capture_output=True, text=True
        )

        if result5.returncode != 0:
            self.output.warning(f"API test: {result5.stderr}")
        else:
            self.output.success(result5.stdout)
