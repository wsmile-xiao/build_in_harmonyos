"""Conan test_package for perl-safe-isa — Perl smoke test.

Verifies that Safe::Isa can be loaded and basic safe isa/can works.
The module exports $_isa, $_can, $_does, $_DOES, $_call_if_object, $_call_if_can
via @EXPORT (imported by default with 'use Safe::Isa').
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.layout import basic_layout


class PerlsafeisaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Build PERL5LIB from all dependency package folders
        perl5lib_paths = []
        for dep in self.dependencies.values():
            pkg_lib = os.path.join(dep.package_folder, "lib", "perl5")
            if os.path.isdir(pkg_lib):
                perl5lib_paths.append(pkg_lib)

        perl5lib = ":".join(perl5lib_paths)

        test_script = (
            "use Safe::Isa;"
            "die 'Safe::Isa version mismatch' unless $Safe::Isa::VERSION eq '1.000010';"
            "my $obj = bless {}, 'Foo';"
            "my $isa_ok = $obj->$_isa('Foo');"
            "die 'safe isa should return true for matching class' unless $isa_ok;"
            "my $can_ok = $obj->$_can('can');"
            "die 'safe can should return coderef' unless $can_ok;"
            "my $undef_isa = undef->$_isa('Bar');"
            "die 'safe isa should return false on undef' if $undef_isa;"
            "print 'Safe::Isa smoke test passed (version: ' . $Safe::Isa::VERSION . ')';"
        )

        env = os.environ.copy()
        if perl5lib:
            existing = env.get("PERL5LIB", "")
            env["PERL5LIB"] = perl5lib + (":" + existing if existing else "")

        result = subprocess.run(
            ["perl", "-e", test_script],
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise Exception(
                "Safe::Isa smoke test FAILED:\n"
                "stdout: {}\nstderr: {}".format(result.stdout, result.stderr)
            )
        self.output.info(result.stdout)
