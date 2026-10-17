#!/usr/bin/env python3
"""Conan recipe — Perforce Jam / Argyll-Jam 2.5 (build tool)

Argyll-Jam: FT-Jam 2.5.2 derivative with ArgyllCMS V1.3.3 Jambase as the
default rule set. Used by ArgyllCMS as its build tool (`jam -fJambase`).

Build system: plain C (no external libraries). The upstream `make -f .../Makefile`
bootstrap chain (`make` -> jam0 -> `./jam0` -> child clang) is NOT used,
because calling jam0 triggers a child-process clang call that the OHOS
sandbox restricts for freshly-built user binaries. Instead we compile the
tool directly from source into a single `jam` executable, and regenerate
`jambase.c` from the shipped Argyll Jambase file with mkjambase (pure C,
no child-process clang needed).

License: per FT-Jam / Perforce (see README.ORG / Jam.html).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


# All C sources that make up the jam build tool (mirrors common.mk SOURCES).
JAM_SOURCES = "builtins.c command.c compile.c execnt.c execunix.c execvms.c expand.c " \
              "filent.c fileos2.c fileunix.c filevms.c glob.c hash.c hdrmacro.c headers.c " \
              "jam.c jambase.c jamgram.c lists.c make.c make1.c newstr.c option.c parse.c " \
              "pathunix.c pathvms.c regexp.c rules.c scan.c search.c timestamp.c variable.c"


class JamConan(ConanFile):
    name = "jam"
    version = "ajam-2.5.2-1.3.4"
    description = "Perforce Jam / Argyll-Jam build tool (FT-Jam 2.5.2 + ArgyllCMS V1.3.3 Jambase)"
    license = "Perforce Freeware"
    homepage = "https://www.argyllcms.com/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS / Linux platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get compiler from Conan conf (never bare shell env vars).
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        # 1) Regenerate jambase.c from the shipped Argyll Jambase file.
        #    This bakes ArgyllCMS V1.3.3 rules into the binary as the default.
        self.run(f'{cc} -O2 -o mkjambase mkjambase.c', cwd=self.source_folder)
        self.run('./mkjambase jambase.c Jambase', cwd=self.source_folder)

        # 2) Direct-link all sources into a single `jam` executable.
        #    (Avoids jam0 bootstrap, which would spawn a child clang call.)
        self.run(f'{cc} -O2 -o jam {JAM_SOURCES}', cwd=self.source_folder)

    def package(self):
        # jam is a command-line build tool: install the binary to bin/.
        copy(self, "jam", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line build tool, not a library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
