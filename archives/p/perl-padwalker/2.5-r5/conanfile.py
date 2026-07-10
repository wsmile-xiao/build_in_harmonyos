#!/usr/bin/env python3
"""Conan recipe — perl-padwalker 2.5-r5 (Perl XS module)

PadWalker is a Perl XS module that provides access to lexical variables
in other scopes. It uses ExtUtils::MakeMaker (Makefile.PL) as its build system.

Key OHOS adaptations:
- System headers: add -I for musl libc headers backup directory
- Linker: bypass missing CRT files with -nostartfiles -nodefaultlibs -L/system/lib64 -lc
"""
import os

from conan import ConanFile
from conan.tools.files import get


class PerlPadwalkerConan(ConanFile):
    name = "perl-padwalker"
    version = "2.5-r5"
    description = "PadWalker - play with other peoples' lexical variables (Perl XS module)"
    license = "MIT"
    homepage = "https://metacpan.org/pod/PadWalker"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        pass

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        makefile_pl = os.path.join(self.source_folder, "Makefile.PL")

        # --- OHOS Adaptation: Modify Makefile.PL ---
        # 1. Add system header include paths to INC
        # 2. Add dynamic_lib OTHERLDFLAGS to bypass missing CRT files
        if self.settings.os in ("Linux", "OHOS"):
            prefix = os.environ.get("DEFAULT_PREFIX", "/usr/local")
            sys_headers = os.path.join(prefix, "include", "_sysheaders_backup")
            local_inc = os.path.join(prefix, "include")

            with open(makefile_pl, "r") as f:
                content = f.read()

            # Replace INC line
            content = content.replace(
                "'INC'\t=> '',",
                f"'INC'\t=> '-I{sys_headers} -I{local_inc}',",
            )

            # Add dynamic_lib before the closing );
            if "dynamic_lib" not in content:
                content = content.replace(
                    "    MIN_PERL_VERSION => \"5.008001\",\n);",
                    "    MIN_PERL_VERSION => \"5.008001\",\n"
                    "    dynamic_lib => { OTHERLDFLAGS => '-nostartfiles -nodefaultlibs -L/system/lib64 -lc' },\n"
                    ");",
                )

            with open(makefile_pl, "w") as f:
                f.write(content)

        # Step 1: Generate Makefile
        self.run("perl Makefile.PL", cwd=self.source_folder)

        # Step 2: Build
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Install to package directory using Perl's make install with DESTDIR
        dest = self.package_folder
        self.run(
            f'make install DESTDIR="{dest}"',
            cwd=self.source_folder,
        )

    def package_info(self):
        # PadWalker.so is a Perl XS shared library
        self.cpp_info.libs = ["PadWalker"]
