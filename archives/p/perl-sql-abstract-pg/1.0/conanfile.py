#!/usr/bin/env python3
"""Conan recipe for perl-sql-abstract-pg 1.0 — Perl EUMM build system.

SQL::Abstract::Pg extends SQL::Abstract with PostgreSQL features.
Pure Perl module, no C compilation required.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class PerlSqlAbstractPgConan(ConanFile):
    name = "perl-sql-abstract-pg"
    version = "1.0"
    description = "PostgreSQL features for SQL::Abstract"
    license = "Artistic-2.0"
    homepage = "https://mojolicious.org"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime dependency: SQL::Abstract >= 2.0
        # Not declared as Conan requirement because perl-sql-abstract
        # is not yet published to @ohpcd/stable.
        # Install manually: perl Makefile.PL && make && make install
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Install SQL::Abstract prerequisite (not yet published to @ohpcd/stable)
        # Download from CPAN, build and install to DEFAULT_PREFIX/lib/perl5
        default_prefix = os.environ.get("DEFAULT_PREFIX", "/usr/local")
        perl5_lib = os.path.join(default_prefix, "lib", "perl5")
        env = os.environ.copy()
        env["PERL5LIB"] = perl5_lib + (":" + env["PERL5LIB"] if env.get("PERL5LIB") else "")

        deps_dir = os.path.join(self.build_folder, "sql_abstract_dep")
        get(self, **self.conan_data["dep_sources"]["sql_abstract"],
            destination=deps_dir, strip_root=True)
        dep_src = deps_dir
        subprocess.run(
            ["perl", "Makefile.PL", f"INSTALL_BASE={default_prefix}"],
            cwd=dep_src, env=env, check=True,
        )
        subprocess.run(["make", "-j1"], cwd=dep_src, env=env, check=True)
        subprocess.run(["make", "install"], cwd=dep_src, env=env, check=True)

        # Build SQL::Abstract::Pg
        subprocess.run(["perl", "Makefile.PL"], cwd=self.source_folder, env=env, check=True)
        subprocess.run(["make", "-j1"], cwd=self.source_folder, env=env, check=True)

    def package(self):
        subprocess.run(
            ["make", "install", f"DESTDIR={self.package_folder}"],
            cwd=self.source_folder, check=True
        )
        # Copy .pm files to standard lib/ for G4 product check and downstream consumers
        copy(self, "*.pm", src=self.source_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=True)

    def package_info(self):
        # Pure Perl module — no C libraries to link
        self.cpp_info.libs = []
