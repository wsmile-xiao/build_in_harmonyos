#!/usr/bin/env python3
"""Conan recipe for perl-redis 2.000 (Redis).

Pure Perl module - Perl binding for Redis database.
Build system: ExtUtils::MakeMaker (Makefile.PL) — fallback for Module::Build::Tiny.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class PerlRedisConan(ConanFile):
    name = "perl-redis"
    version = "2.000"
    description = "Perl binding for Redis database - Pure Perl module"
    license = "artistic_2"
    homepage = "https://github.com/PerlRedis/perl-redis"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Set PERL_MM_FALLBACK_SILENCE_WARNING via Environment (Conan 2 API)
        env = Environment()
        env.define("PERL_MM_FALLBACK_SILENCE_WARNING", "1")
        envvars = env.vars(self)
        envvars.save_script("perl_redis_env")

    def build(self):
        # Apply patches if any (from conandata.yml)
        apply_conandata_patches(self)

        # Run perl Makefile.PL && make
        # The source ships with Makefile.PL (ExtUtils::MakeMaker fallback)
        # PERL_MM_FALLBACK_SILENCE_WARNING suppresses Module::Build::Tiny warning and 10s sleep
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to staging directory
        staging = os.path.join(self.build_folder, "staging")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)

        # Copy Perl .pm files to lib/ at package root for G4 compatibility
        for pm_file in glob.glob(os.path.join(staging, "**", "*.pm"), recursive=True):
            rel = os.path.relpath(pm_file, staging)
            parts = rel.split(os.sep)
            if 'site_perl' in parts:
                idx = parts.index('site_perl')
                target_rel = os.path.join('lib', 'perl5', *parts[idx:])
            else:
                target_rel = os.path.join('lib', 'perl5', rel)
            target = os.path.join(self.package_folder, target_rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            copy(self, os.path.basename(pm_file), src=os.path.dirname(pm_file), dst=os.path.dirname(target))

    def package_info(self):
        # Pure Perl module — libraries are .pm files in lib/perl5
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.libs = []
        # Set PERL5LIB for consumers — use glob to find the actual site_perl path
        for site_lib in glob.glob(os.path.join(self.package_folder, "lib", "perl5", "site_perl", "*")):
            if os.path.isdir(site_lib):
                self.runenv_info.append_path("PERL5LIB", site_lib)
                break
