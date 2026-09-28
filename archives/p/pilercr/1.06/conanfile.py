#!/usr/bin/env python3
"""pilercr 1.06: CRISPR repeat finder (standalone command-line tool)."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class PilercrConan(ConanFile):
    name = "pilercr"
    version = "1.06"
    description = "Find CRISPR arrays in FASTA sequences"
    license = "Public-Domain"
    homepage = "https://www.drive5.com/pilercr/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("pilercr supports Linux and OHOS")

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        # Upstream tar has a leading ./ before its pilercr1.06/ root.
        get(self, **self.conan_data["sources"][self.version], strip_root=False)
        root = os.path.join(self.source_folder, "pilercr1.06")
        for entry in os.listdir(root):
            shutil.move(os.path.join(root, entry), os.path.join(self.source_folder, entry))
        os.rmdir(root)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_cxxflags.append("-Wno-register")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        tc = AutotoolsToolchain(self).vars()
        tools = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = tools.get("cpp") or tc.get("CXX")
        if not cxx:
            raise ConanInvalidConfiguration("C++ compiler not set in Conan toolchain")
        # Stripping is optional; CI's OHOS NDK may not ship llvm-strip.
        # Never invoke the host strip on an AArch64 ELF.
        strip = ":" if self.settings.os == "OHOS" else "strip"
        flags = str(tc.get("CXXFLAGS", "-O2")) + " -Wno-register"
        ldflags = str(tc.get("LDFLAGS", ""))
        args = {"GPP": cxx, "CPP": f"{cxx} -c {flags}",
                "LD": f"{cxx} {ldflags}", "CFLAGS": flags,
                "LDLIBS": "-lm -static" if self.settings.os == "OHOS" else "-lm",
                "STRIP": strip}
        overrides = " ".join(f"{k}={shlex.quote(v)}" for k, v in args.items())
        self.run(f"make -B -j2 {overrides}")

    def package(self):
        copy(self, "pilercr", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
