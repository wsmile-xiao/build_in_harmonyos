#!/usr/bin/env python3
"""Conan test_package for perl-proc-waitstat 1.00.

L1 test: verify Proc::WaitStat (pure Perl module) can be loaded
and that waitstat(), waitstat_reuse(), waitstat_die() work correctly
on HarmonyOS. Uses inline env var prefix for Conan 2.x compatibility.
"""
import os
import glob

from conan import ConanFile


class PerlProcWaitstatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        test_script = (
            "use strict;\n"
            "use warnings;\n"
            "use POSIX qw(:sys_wait_h);\n"
            "use Proc::WaitStat qw(waitstat waitstat_reuse waitstat_die close_die);\n"
            "\n"
            "# Test 1: module loaded and version correct\n"
            "die 'VERSION mismatch' unless $Proc::WaitStat::VERSION eq '1.00';\n"
            "print \"Test 1 PASS: module loaded, version 1.00\\n\";\n"
            "\n"
            "# Test 2: waitstat() with normal exit status\n"
            "# Construct a wait status for exit code 0 (WIFEXITED=1, WEXITSTATUS=0)\n"
            "my $status_0 = 0;  # exit 0 => status 0\n"
            "my $desc_0 = waitstat($status_0);\n"
            "die \"waitstat(0) should return '0', got '$desc_0'\" unless $desc_0 eq '0';\n"
            "print \"Test 2 PASS: waitstat(0) = '$desc_0'\\n\";\n"
            "\n"
            "# Test 3: waitstat() with non-zero exit status\n"
            "my $status_42 = 42 << 8;  # WEXITSTATUS=42 => status = 42*256\n"
            "my $desc_42 = waitstat($status_42);\n"
            "die \"waitstat(42<<8) should return '42', got '$desc_42'\" unless $desc_42 eq '42';\n"
            "print \"Test 3 PASS: waitstat(42<<8) = '$desc_42'\\n\";\n"
            "\n"
            "# Test 4: waitstat_reuse() with normal exit\n"
            "my $reuse_0 = waitstat_reuse($status_0);\n"
            "die \"waitstat_reuse(0) should return 0, got $reuse_0\" unless $reuse_0 == 0;\n"
            "print \"Test 4 PASS: waitstat_reuse(0) = $reuse_0\\n\";\n"
            "\n"
            "# Test 5: waitstat_reuse() with non-zero exit\n"
            "my $reuse_42 = waitstat_reuse($status_42);\n"
            "die \"waitstat_reuse(42<<8) should return 42, got $reuse_42\" unless $reuse_42 == 42;\n"
            "print \"Test 5 PASS: waitstat_reuse(42<<8) = $reuse_42\\n\";\n"
            "\n"
            "# Test 6: waitstat_die() with zero status (should not die)\n"
            "eval { waitstat_die($status_0, 'test-program'); };\n"
            "die \"waitstat_die(0) should not die: $@\" if $@;\n"
            "print \"Test 6 PASS: waitstat_die(0) did not die\\n\";\n"
            "\n"
            "# Test 7: waitstat_die() with non-zero status (should die)\n"
            "eval { waitstat_die($status_42, 'test-program'); };\n"
            "die \"waitstat_die(42<<8) should die\" unless $@;\n"
            "print \"Test 7 PASS: waitstat_die(42<<8) died as expected: $@\";\n"
            "\n"
            "# Test 8: fork + waitpid + waitstat integration test\n"
            "my $child = fork();\n"
            "if (!defined $child) {\n"
            "    print \"Test 8 SKIP: fork() not available on this platform\\n\";\n"
            "} elsif ($child == 0) {\n"
            "    exit(7);\n"
            "} else {\n"
            "    my $pid = waitpid($child, 0);\n"
            "    my $desc = waitstat($?);\n"
            "    my $reuse = waitstat_reuse($?);\n"
            "    if ($pid == $child && $desc eq '7' && $reuse == 7) {\n"
            "        print \"Test 8 PASS: fork+waitpid+waitstat integration: exit=7, desc='$desc', reuse=$reuse\\n\";\n"
            "    } else {\n"
            "        die \"Test 8 FAIL: pid=$pid (expected $child), desc='$desc', reuse=$reuse\";\n"
            "    }\n"
            "}\n"
            "\n"
            "# Test 9: close_die() with a pipe to a successful command\n"
            "my $fh;\n"
            "my $opened = open($fh, '-|', 'echo', 'hello');\n"
            "if ($opened) {\n"
            "    my $line = <$fh>;\n"
            "    eval { close_die($fh, 'echo'); };\n"
            "    die \"close_die should not die for successful command: $@\" if $@;\n"
            "    print \"Test 9 PASS: close_die(echo) did not die\\n\";\n"
            "} else {\n"
            "    print \"Test 9 SKIP: cannot open pipe to echo\\n\";\n"
            "}\n"
            "\n"
            "print \"ALL TESTS PASSED\\n\";\n"
        )
        with open(os.path.join(self.source_folder, "test_waitstat.pl"), "w") as f:
            f.write(test_script)

    def build(self):
        pass

    def test(self):
        # Find WaitStat.pm in the package folder to determine PERL5LIB
        pkg = self.dependencies["perl-proc-waitstat"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "WaitStat.pm"), recursive=True)
        if not pm_files:
            raise Exception("Proc/WaitStat.pm not found in package")
        # lib_dir is the directory that contains 'Proc/' (two levels up from WaitStat.pm)
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))

        # IPC::Signal is a dependency installed at user site_perl
        deps_lib = "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0"

        # Conan 2.x: use inline env var prefix (self.run env param expects list, not dict)
        test_script = os.path.join(self.source_folder, "test_waitstat.pl")
        self.run(f"PERL5LIB='{lib_dir}:{deps_lib}' perl {test_script}")
