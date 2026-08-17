#!/usr/bin/env python3
"""Conan test_package for perl-object-insideout — package + runtime test.

Verifies that the Object::InsideOut module package is correctly built:
  1. Package structure: .pm files at lib/perl5/Object/InsideOut.pm
  2. Version verification: parse VERSION from .pm file
  3. Content completeness: all 16 .pm sub-modules present in package
  4. Runtime module load: loads Object::InsideOut using bundled runtime
     dependencies (Devel::StackTrace, Class::Data::Inheritable,
     Exception::Class .pm files in test_package/perl_lib/), then creates
     an object and verifies field get/set functionality.
"""
import os

from conan import ConanFile


class PerlObjectInsideOutTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-object-insideout"]
        dep_pkg = dep.package_folder
        oio_pm = os.path.join(dep_pkg, "lib", "perl5", "Object", "InsideOut.pm")

        # Verify package structure: .pm files must be at lib/perl5/
        if not os.path.isfile(oio_pm):
            raise Exception(
                f"Object::InsideOut.pm not found at expected path: {oio_pm}"
            )

        # Build PERL5LIB from dependency package folders
        perl5lib_paths = []
        for d in self.dependencies.values():
            pkg_lib = os.path.join(d.package_folder, "lib", "perl5")
            if os.path.isdir(pkg_lib):
                perl5lib_paths.append(pkg_lib)
        perl5lib = ":".join(perl5lib_paths)

        # Run the test script
        test_script = os.path.join(os.path.dirname(__file__), "test_oio.py")
        self.run(
            f'PERL5LIB="{perl5lib}" OIO_PM_PATH="{oio_pm}" python3 "{test_script}"'
        )
