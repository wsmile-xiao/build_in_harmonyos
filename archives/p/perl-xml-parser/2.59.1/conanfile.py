#!/usr/bin/env python3
"""Conan recipe — XML::Parser 2.59 (Perl XS module)

Build system: perl Makefile.PL (ExtUtils::MakeMaker)
Depends on expat library for XML parsing.
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class PerlXmlParserConan(ConanFile):
    name = "perl-xml-parser"
    version = "2.59.1"
    description = "Perl XML parsing module based on expat"
    license = "Perl Artistic License"
    homepage = "https://metacpan.org/pod/XML::Parser"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"perl-xml-parser does not support os={self.settings.os}"
            )

    def requirements(self):
        self.requires("expat/2.8.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = Environment()
        # R33: Use full compiler path from Conan conf, not bare compiler name
        compiler_exes = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_exes.get("c", str(self.settings.compiler) if self.settings.compiler else "clang")
        cxx = compiler_exes.get("cpp", f"{cc}++")
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("CFLAGS", "-fPIC -O2")
        # Ensure OHOS SDK bin is first in PATH so bare 'clang' resolves correctly
        cc_dir = os.path.dirname(cc) if cc and "/" in cc else ""
        if cc_dir:
            env.prepend_path("PATH", cc_dir)
        # Expat shared library path for Devel::CheckLib runtime test
        expat = self.dependencies["expat"]
        if expat.cpp_info.libdirs:
            env.append_path("LD_LIBRARY_PATH", expat.cpp_info.libdirs[0])
        envvars = env.vars(self)
        envvars.save_script("perl_xml_parser_env")

    def build(self):
        apply_conandata_patches(self)
        expat = self.dependencies["expat"]
        expat_inc = expat.cpp_info.includedirs[0] if expat.cpp_info.includedirs else ""
        expat_lib = expat.cpp_info.libdirs[0] if expat.cpp_info.libdirs else ""

        inc_flag = f"-I{expat_inc}" if expat_inc else ""
        lib_flag = f"-L{expat_lib} -lexpat" if expat_lib else ""

        self.run(
            f'perl Makefile.PL LIBS="{lib_flag}" INC="{inc_flag}"',
            cwd=self.source_folder,
            env=["perl_xml_parser_env"],
        )
        self.run("make", cwd=self.source_folder, env=["perl_xml_parser_env"])

    def package(self):
        # Install to temp dir, not package_folder, to avoid extra lib/ dirs
        dest = os.path.join(self.build_folder, "destdir")
        self.run(
            f"make install DESTDIR={dest}",
            cwd=self.source_folder,
            env=["perl_xml_parser_env"],
        )
        blib = os.path.join(self.source_folder, "blib")
        # Copy .pm files to lib/
        pm_src = os.path.join(blib, "lib")
        if os.path.isdir(pm_src):
            copy(self, "*.pm", pm_src, os.path.join(self.package_folder, "lib"))
        # Copy .so files to lib/auto/
        so_files = glob.glob(os.path.join(blib, "arch", "auto", "**", "*.so"), recursive=True)
        if so_files:
            for so in so_files:
                rel = os.path.relpath(so, os.path.join(blib, "arch"))
                target = os.path.join(self.package_folder, "lib", rel)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                copy(self, os.path.basename(so), os.path.dirname(so), os.path.dirname(target))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        perl_lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.append("PERL5LIB", perl_lib)
        self.buildenv_info.append("PERL5LIB", perl_lib)
