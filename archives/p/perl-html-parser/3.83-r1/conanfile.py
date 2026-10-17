#!/usr/bin/env python3
"""Conan recipe — HTML::Parser Perl XS module.

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module that compiles C sources into a shared library
(Parser.so) loaded by Perl's XSLoader/DynaLoader.

Adaptations for OHOS:
- C_INCLUDE_PATH and LIBRARY_PATH set to OHOS SDK sysroot for musl headers
- OTHERLDFLAGS="-nostartfiles -nodefaultlibs" to bypass CRT linking issues
  (XS .so is loaded via dlopen by Perl, no standalone entry point needed)
- R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment


class PerlHtmlParserConan(ConanFile):
    name = "perl-html-parser"
    version = "3.83-r1"
    description = "Perl module for parsing HTML documents with event-driven interface"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/pod/HTML::Parser"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: Only configure build env on Linux/OHOS
        if self.settings.os in ("Linux", "OHOS"):
            env = Environment()
            # Auto-detect OHOS SDK path from standard installation directory.
            sdk_base = "/data/service/hnp/ohos-sdk.org"
            sdk_dirs = sorted(
                d for d in os.listdir(sdk_base) if d.startswith("ohos-sdk_")
            ) if os.path.isdir(sdk_base) else []
            if sdk_dirs:
                sdk_root = os.path.join(sdk_base, sdk_dirs[-1], "ohos/native")
                sysroot = os.path.join(sdk_root, "sysroot/usr")
                llvm_lib = os.path.join(sdk_root, "llvm/lib/aarch64-linux-ohos")
                c_include = f"{sysroot}/include:{sysroot}/include/aarch64-linux-ohos"
                library_path = f"{sysroot}/lib/aarch64-linux-ohos:{llvm_lib}"
                env.define("C_INCLUDE_PATH", c_include)
                env.define("LIBRARY_PATH", library_path)
                self.output.info(f"Configuring Perl XS build environment for {self.settings.os}")
                self.output.info(f"  SDK: {sdk_root}")
                self.output.info(f"  C_INCLUDE_PATH: {c_include}")
                self.output.info(f"  LIBRARY_PATH: {library_path}")
            else:
                self.output.warning(f"OHOS SDK not found at {sdk_base}, skipping env setup")
            env.vars(self).save_script("perl_html_parser_env")

    def build(self):
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # Build env list: perl_html_parser_env only exists on Linux/OHOS
        env_list = ["conanbuild", "perl_html_parser_env"] if self.settings.os in ("Linux", "OHOS") else ["conanbuild"]

        # Step 1: Generate Makefile using ExtUtils::MakeMaker
        self.run("perl Makefile.PL", cwd=self.source_folder, env=env_list)

        # Step 2: Build with special linker flags for XS module
        # -nostartfiles -nodefaultlibs: XS .so loaded via dlopen by Perl,
        #   no standalone entry point or default CRT libraries needed
        self.run('make -j1 OTHERLDFLAGS="-nostartfiles -nodefaultlibs"', cwd=self.source_folder, env=env_list)

    def package(self):
        # Build env list
        env_list = ["conanbuild", "perl_html_parser_env"] if self.settings.os in ("Linux", "OHOS") else ["conanbuild"]

        # Install to a temporary DESTDIR
        dest_dir = os.path.join(self.build_folder, "destdir")
        self.run("make install DESTDIR={}".format(dest_dir), cwd=self.source_folder, env=env_list)

        # Find and copy the compiled .so (XS shared library)
        so_files = glob.glob(os.path.join(dest_dir, "**", "auto", "HTML", "Parser", "Parser.so"), recursive=True)
        if so_files:
            perl_target = os.path.join(self.package_folder, "lib", "perl5", "auto", "HTML", "Parser")
            os.makedirs(perl_target, exist_ok=True)
            shutil.copy2(so_files[0], perl_target)

        # Find and copy all .pm (Perl module files)
        pm_files = glob.glob(os.path.join(dest_dir, "**", "HTML", "*.pm"), recursive=True)
        for pm_file in pm_files:
            target_dir = os.path.join(self.package_folder, "lib", "perl5", "HTML")
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(pm_file, target_dir)

    def package_info(self):
        # This is a Perl XS module, not a C library
        # The .so is loaded by Perl's XSLoader at runtime
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.output.info(f"Perl library path: {perl_lib}")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
