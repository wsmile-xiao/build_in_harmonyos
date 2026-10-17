#!/usr/bin/env python3
"""Conan test_package — extutils-cppguess 0.27

Tests that ExtUtils::CppGuess can be loaded and correctly detects
the C++ compiler and flags on the OHOS platform.
"""
import os
import glob

from conan import ConanFile


class ExtUtilsCppGuessTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    _capture_tiny_lib = None

    def _ensure_capture_tiny(self):
        """Ensure Capture::Tiny is available for loading ExtUtils::CppGuess."""
        try:
            self.run("perl -MCapture::Tiny -e 'exit 0'", env="conanrun", quiet=True)
            return
        except Exception:
            pass

        tmp_dir = os.path.join(self.build_folder, "_capture_tiny")
        os.makedirs(tmp_dir, exist_ok=True)
        ct_install = os.path.join(tmp_dir, "perl5lib")
        if not os.path.isdir(os.path.join(ct_install, "lib", "perl5", "Capture")):
            self.run(
                'cd "{}" && curl -k -L '
                '"https://cpan.metacpan.org/authors/id/D/DA/DAGOLDEN/Capture-Tiny-0.48.tar.gz" '
                '-o Capture-Tiny.tar.gz && tar -xzf Capture-Tiny.tar.gz && '
                'cd Capture-Tiny-0.48 && perl Makefile.PL INSTALL_BASE="{}" && '
                'make && make install INSTALL_BASE="{}"'.format(
                    tmp_dir, ct_install, ct_install
                ),
                env="conanrun",
            )
        self._capture_tiny_lib = os.path.join(ct_install, "lib", "perl5")

    def _write_test_script(self, name, code):
        """Write a Perl test script to a temp file and return its path."""
        script_dir = os.path.join(self.build_folder, "_test_scripts")
        os.makedirs(script_dir, exist_ok=True)
        script_path = os.path.join(script_dir, name)
        with open(script_path, "w") as f:
            f.write(code)
        return script_path

    def test(self):
        # Find ExtUtils/CppGuess.pm in the package folder
        pkg = self.dependencies["extutils-cppguess"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "CppGuess.pm"), recursive=True)
        if not pm_files:
            raise Exception("ExtUtils/CppGuess.pm not found in package")
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))

        # Ensure Capture::Tiny is available
        self._ensure_capture_tiny()

        # Build PERL5LIB for all commands
        perl5lib_parts = [lib_dir]
        if self._capture_tiny_lib:
            perl5lib_parts.append(self._capture_tiny_lib)
        current = os.environ.get("PERL5LIB", "")
        if current:
            perl5lib_parts.append(current)
        perl5lib = ":".join(perl5lib_parts)

        # Test 1: Load ExtUtils::CppGuess and verify version
        test1 = self._write_test_script("test1.pl", """\
use ExtUtils::CppGuess;
my $v = $ExtUtils::CppGuess::VERSION;
die "version mismatch: expected 0.27, got $v\\n" unless $v eq "0.27";
print "Test 1 PASS: version $v\\n";
""")
        self.run(
            'PERL5LIB="{}" perl "{}"'.format(perl5lib, test1),
            env="conanrun",
        )

        # Test 2: Verify C++ compiler detection via makemaker_options
        test2 = self._write_test_script("test2.pl", """\
use ExtUtils::CppGuess;
my $g = ExtUtils::CppGuess->new;
my %opts = $g->makemaker_options;
die "no CC detected\\n" unless $opts{CC};
die "no CCFLAGS detected\\n" unless $opts{CCFLAGS};
my $ld = $opts{dynamic_lib}{OTHERLDFLAGS} || "none";
print "Test 2 PASS: CC=$opts{CC} LDFLAGS=$ld\\n";
""")
        self.run(
            'PERL5LIB="{}" perl "{}"'.format(perl5lib, test2),
            env="conanrun",
        )

        # Test 3: Verify is_clang() returns true (OHOS uses clang)
        test3 = self._write_test_script("test3.pl", """\
use ExtUtils::CppGuess;
my $g = ExtUtils::CppGuess->new;
my $clang = $g->is_clang ? "Yes" : "No";
my $gcc = $g->is_gcc ? "Yes" : "No";
my $msvc = $g->is_msvc ? "Yes" : "No";
print "Test 3 PASS: is_clang=$clang is_gcc=$gcc is_msvc=$msvc\\n";
""")
        self.run(
            'PERL5LIB="{}" perl "{}"'.format(perl5lib, test3),
            env="conanrun",
        )

        # Test 4: Verify module_build_options works
        test4 = self._write_test_script("test4.pl", """\
use ExtUtils::CppGuess;
my $g = ExtUtils::CppGuess->new;
my %mb = $g->module_build_options;
die "no module_build cc\\n" unless $mb{config}{cc};
print "Test 4 PASS: MB cc=$mb{config}{cc}\\n";
""")
        self.run(
            'PERL5LIB="{}" perl "{}"'.format(perl5lib, test4),
            env="conanrun",
        )
