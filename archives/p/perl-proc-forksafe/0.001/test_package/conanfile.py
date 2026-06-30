#!/usr/bin/env python3
"""Conan test_package — perl-proc-forksafe 0.001

Tests that Proc::ForkSafe can be loaded and its core functionality
(wrap, call, fork-safe reinitialization, destroy callback) works.
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlProcForksafeTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Create comprehensive test script
        test_script = (
            "use strict;\n"
            "use warnings;\n"
            "use Proc::ForkSafe;\n"
            "\n"
            "# Test 1: module loads and has correct version\n"
            "die 'VERSION mismatch' unless $Proc::ForkSafe::VERSION eq '0.001';\n"
            "print \"Test 1 PASS: module loaded, version 0.001\\n\";\n"
            "\n"
            "# Test 2: wrap() creates a ForkSafe object\n"
            "{\n"
            "    package A;\n"
            "    sub new { bless {}, shift }\n"
            "    sub foo { 'foo' }\n"
            "    sub bar { shift->{bar} //= 0; shift->{bar}++ }\n"
            "}\n"
            "\n"
            "my $a = Proc::ForkSafe->wrap(sub { A->new });\n"
            "die 'wrap failed' unless ref($a) eq 'Proc::ForkSafe';\n"
            "die 'missing pid' unless defined $a->{pid};\n"
            "die 'missing obj' unless defined $a->{obj};\n"
            "print \"Test 2 PASS: wrap() creates ForkSafe object\\n\";\n"
            "\n"
            "# Test 3: call() invokes methods on wrapped object\n"
            "my $result = $a->call('foo');\n"
            "die 'call returned wrong value' unless $result eq 'foo';\n"
            "print \"Test 3 PASS: call() invokes method correctly\\n\";\n"
            "\n"
            "# Test 4: same PID, no reinitialization\n"
            "my $pid_before = $a->{pid};\n"
            "$a->call('foo');\n"
            "die 'pid changed without fork' unless $a->{pid} == $pid_before;\n"
            "print \"Test 4 PASS: no reinit without fork\\n\";\n"
            "\n"
            "# Test 5: fork-safe reinitialization\n"
            "my $child = fork();\n"
            "if (!defined $child) {\n"
            "    print \"Test 5 SKIP: fork() not available on this platform\\n\";\n"
            "} elsif ($child == 0) {\n"
            "    # In child: call() should detect PID change and reinitialize\n"
            "    my $r = $a->call('foo');\n"
            "    die 'call failed after fork' unless $r eq 'foo';\n"
            "    die 'pid not updated after fork' unless $a->{pid} != $pid_before;\n"
            "    print \"Test 5 PASS: fork-safe reinit works\\n\";\n"
            "    exit 0;\n"
            "} else {\n"
            "    waitpid($child, 0);\n"
            "    die 'child failed' unless $? == 0;\n"
            "    # Parent: pid should be unchanged\n"
            "    die 'parent pid changed' unless $a->{pid} == $pid_before;\n"
            "    print \"Test 6 PASS: parent unchanged after fork\\n\";\n"
            "}\n"
            "\n"
            "# Test 7: destroy callback called after fork\n"
            "my $destroy_called = 0;\n"
            "my $b = Proc::ForkSafe->wrap(\n"
            "    sub { A->new },\n"
            "    sub { $destroy_called = 1 },\n"
            ");\n"
            "$b->call('foo');\n"
            "die 'destroy called early' if $destroy_called;\n"
            "\n"
            "my $child2 = fork();\n"
            "if (!defined $child2) {\n"
            "    print \"Test 7 SKIP: fork() not available\\n\";\n"
            "} elsif ($child2 == 0) {\n"
            "    die 'destroy called before call' if $destroy_called;\n"
            "    $b->call('foo');\n"
            "    die 'destroy not called after fork' unless $destroy_called;\n"
            "    print \"Test 7 PASS: destroy callback works\\n\";\n"
            "    exit 0;\n"
            "} else {\n"
            "    waitpid($child2, 0);\n"
            "    die 'child2 failed' unless $? == 0;\n"
            "}\n"
            "\n"
            "print \"ALL TESTS PASSED\\n\";\n"
        )
        with open(os.path.join(self.source_folder, "test_forksafe.pl"), "w") as f:
            f.write(test_script)

    def test(self):
        # Find Proc/ForkSafe.pm in the package folder
        pkg = self.dependencies["perl-proc-forksafe"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "ForkSafe.pm"), recursive=True)
        if not pm_files:
            raise Exception("Proc/ForkSafe.pm not found in package")
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))

        env = os.environ.copy()
        env["PERL5LIB"] = lib_dir + (":" + env.get("PERL5LIB", "") if env.get("PERL5LIB") else "")

        result = subprocess.run(
            ['perl', os.path.join(self.source_folder, 'test_forksafe.pl')],
            env=env, capture_output=True, text=True
        )

        if result.returncode != 0:
            self.output.error(f"Test failed: {result.stderr}")
            raise Exception(f"Test failed with exit code {result.returncode}")

        self.output.success(result.stdout)
