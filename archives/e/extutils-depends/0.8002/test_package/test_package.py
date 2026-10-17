#!/usr/bin/env python3
"""Test source for extutils-depends Conan test_package.

This script verifies that the ExtUtils::Depends Perl module is installed
and functional by running a Perl test script.
"""
import glob
import os
import subprocess
import sys
import tempfile


def find_module(pkg_folder):
    """Find ExtUtils/Depends.pm in the Conan package folder."""
    pm_files = glob.glob(
        os.path.join(pkg_folder, "**", "ExtUtils", "Depends.pm"),
        recursive=True,
    )
    if not pm_files:
        print("ERROR: ExtUtils/Depends.pm not found in package", file=sys.stderr)
        sys.exit(1)
    perl_lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))
    return perl_lib_dir


def run_test(perl_lib_dir):
    """Run Perl test to verify ExtUtils::Depends module functionality."""
    test_script = os.path.join(tempfile.gettempdir(), "test_extutils_depends.pl")
    with open(test_script, "w") as f:
        f.write("use ExtUtils::Depends;\n")
        f.write("my $dep = ExtUtils::Depends->new('Test::Module');\n")
        f.write("die 'not a ExtUtils::Depends object' unless ref($dep) eq 'ExtUtils::Depends';\n")
        f.write("die 'wrong name' unless $dep->{name} eq 'Test::Module';\n")
        f.write("die 'no typemaps' unless ref($dep->{typemaps}) eq 'ARRAY';\n")
        f.write("die 'no deps' unless ref($dep->{deps}) eq 'HASH';\n")
        f.write("print \"ExtUtils::Depends test OK\\n\";\n")
    env = os.environ.copy()
    env["PERL5LIB"] = perl_lib_dir
    result = subprocess.run(["perl", test_script], env=env, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        sys.exit(1)


if __name__ == "__main__":
    pkg_folder = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CONAN_PKG_FOLDER", "")
    if not pkg_folder:
        print("ERROR: package folder not provided", file=sys.stderr)
        sys.exit(1)
    perl_lib_dir = find_module(pkg_folder)
    run_test(perl_lib_dir)
