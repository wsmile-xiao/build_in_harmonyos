#!/usr/bin/env python3
"""Conan test_package for perl-sql-abstract 2.000001.

Verifies that SQL::Abstract can be loaded and basic SQL generation works.
"""
import os

from conan import ConanFile


class PerlSqlAbstractTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # Pure Perl module, no build step needed

    def _find_perl5lib_roots(self, pkg_folder):
        """Find PERL5LIB root directories from package .pm files.

        Perl module dirs start with uppercase (SQL, DBIx); internal dirs are
        lowercase (site_perl, 5.42.0). PERL5LIB must point to the directory
        that contains the top-level module directory.
        """
        roots = set()
        lib_dir = os.path.join(pkg_folder, "lib")
        if not os.path.isdir(lib_dir):
            return roots
        for root, _, files in os.walk(lib_dir):
            for f in files:
                if f.endswith(".pm"):
                    rel = os.path.relpath(os.path.join(root, f), lib_dir)
                    parts = rel.split(os.sep)
                    root_parts = []
                    for part in parts[:-1]:
                        if part and part[0].isupper():
                            break
                        root_parts.append(part)
                    r = os.path.join(lib_dir, *root_parts) if root_parts else lib_dir
                    roots.add(r)
                    break
        return roots

    def test(self):
        # Find the package's lib directory from the dependency
        pkg_folder = None
        for dep in self.dependencies.values():
            if hasattr(dep, "package_folder") and dep.package_folder:
                pkg_folder = dep.package_folder
                break

        # Build PERL5LIB from the package folder
        perl5lib_paths = list(self._find_perl5lib_roots(pkg_folder)) if pkg_folder else []

        # Merge with existing PERL5LIB (from runenv_info / conanrun.sh)
        existing = os.environ.get("PERL5LIB", "")
        if existing:
            for p in existing.split(":"):
                if p and p not in perl5lib_paths:
                    perl5lib_paths.append(p)

        perl5lib = ":".join(perl5lib_paths)
        if perl5lib:
            os.environ["PERL5LIB"] = perl5lib

        # Run smoke test via self.run() (required by CI L0d gate)
        test_script = os.path.join(self.source_folder, "run_smoke_test.sh")
        self.run(f"sh {test_script}")
