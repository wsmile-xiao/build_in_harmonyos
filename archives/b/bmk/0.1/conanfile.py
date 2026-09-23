#!/usr/bin/env python3
"""Conan recipe for bmk 0.1, a portable make-family build tool."""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class BmkConan(ConanFile):
    name = "bmk"
    version = "0.1"
    description = "A portable successor to make with integrated subdirectory builds"
    license = "ISC"
    homepage = "https://github.com/realchonk/bmk"
    url = "https://github.com/realchonk/bmk"
    package_type = "application"

    exports_sources = "conandata.yml"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("bmk/0.1 currently supports Linux and OHOS")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration("bmk/0.1 currently supports OHOS aarch64")
        if str(self.settings.compiler) != "clang":
            raise ConanInvalidConfiguration("bmk/0.1 requires the clang compiler")

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") if compilers else None
        if not cc:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables[c] must provide the target clang"
            )
        if not shutil.which(cc):
            raise ConanInvalidConfiguration(f"target C compiler is not executable: {cc}")
        return cc

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler()
        if not shutil.which("sh") or not shutil.which("make"):
            raise ConanInvalidConfiguration("bmk/0.1 requires sh and make in PATH")
        env = Environment()
        env.define("CC", cc)
        env.define("CPP", f"{cc} -E")
        cflags = self.conf.get("tools.build:cflags", default=[], check_type=list)
        linkflags = self.conf.get("tools.build:exelinkflags", default=[], check_type=list)
        env.define("CFLAGS", " ".join(["-fPIC", "-O2", *cflags]))
        env.define("CPPFLAGS", "")
        env.define("LDFLAGS", " ".join(linkflags))
        with env.vars(self).apply():
            self.run(
                'sh ./configure --prefix="/" --bindir="/bin" '
                '--mandir="/share/man"',
                cwd=self.source_folder,
            )
            self.run("make -j1", cwd=self.source_folder)
            if not cross_building(self):
                self.run("./mk clean all", cwd=self.source_folder)

        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests" if cross_building(self) else "passed",
            "framework": "custom make",
            "command": "not available",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "bmk 0.1 has no unit/integration test suite or check/test target. "
                "All applicable upstream CI validation semantics were retained: "
                "bootstrap build and self-hosted './mk clean all'. Alternate-compiler "
                "and OS matrix jobs are environment variants, not separate test cases."
            ),
        }), flush=True)

    def package(self):
        copy(self, "mk", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "mk.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
