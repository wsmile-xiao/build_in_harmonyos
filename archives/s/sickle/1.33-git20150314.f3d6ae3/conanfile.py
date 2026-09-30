"""Sickle 1.33 command line FASTQ trimmer for OpenHarmony/Linux."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SickleConan(ConanFile):
    name = "sickle"
    version = "1.33-git20150314.f3d6ae3"
    description = "Quality-based FASTQ read trimmer"
    license = "MIT"
    homepage = "https://github.com/najoshi/sickle"
    url = homepage
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("sickle supports Linux and OHOS")

    def requirements(self):
        self.requires("zlib/1.3.2.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compiler = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compiler.get("c", "cc")
        dep = self.dependencies["zlib"].cpp_info
        includes = " ".join("-I" + shlex.quote(p) for p in dep.includedirs)
        # The upstream Makefile hardcodes gcc and -lz; override both with
        # the Conan-selected compiler and the published dependency's archive.
        libz = os.path.join(dep.libdirs[0], "libz.a")
        if not os.path.isfile(libz):
            raise ConanInvalidConfiguration("zlib static archive is required")
        flags = "-Wall -pedantic -DVERSION=1.33 " + includes
        self.run("make -j2 " + " ".join((
            "CC=" + shlex.quote(cc),
            "CFLAGS=" + shlex.quote(flags),
            "LDFLAGS=-static" if str(self.settings.os) == "OHOS" else "LDFLAGS=",
            "LIBS=" + shlex.quote(libz),
            "build",
        )), cwd=self.source_folder)

    def package(self):
        copy(self, "sickle", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
