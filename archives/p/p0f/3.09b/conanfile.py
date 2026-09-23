#!/usr/bin/env python3
"""Conan recipe for p0f 3.09b custom build on HarmonyOS PC."""

import os
import shlex

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class P0fConan(ConanFile):
    name = "p0f"
    version = "3.09b"
    description = "Passive TCP/IP fingerprinting tool"
    license = "LGPL-2.1-only"
    homepage = "https://lcamtuf.coredump.cx/p0f3/"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pcap = self.dependencies["libpcap"].cpp_info
        env = Environment()
        env.define("CONFIG_SHELL", os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash"))
        env.define("SHELL", os.environ.get("SHELL", "/data/service/hnp/bin/bash"))
        env.define("CFLAGS", " ".join(f"-I{path}" for path in pcap.includedirs))
        env.define("LDFLAGS", " ".join(f"-L{path}" for path in pcap.libdirs))
        env.vars(self).save_script("p0f-build-env")

    def build(self):
        apply_conandata_patches(self)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        include_flags = " ".join(
            f"-I{path}" for path in self.dependencies["libpcap"].cpp_info.includedirs
        )
        lib_flags = " ".join(
            f"-L{path}" for path in self.dependencies["libpcap"].cpp_info.libdirs
        )
        bash = "/data/service/hnp/bin/bash"
        command = (
            f"CC={shlex.quote(cc)} CFLAGS={shlex.quote('-fPIC -O2 ' + include_flags)} "
            f"LDFLAGS={shlex.quote(lib_flags)} {bash} ./build.sh all"
        )
        self.run(command, cwd=self.source_folder)
        make = "/data/service/hnp/bin/make"
        self.run(
            f"{make} -C tools CC={shlex.quote(cc)} "
            f"CFLAGS={shlex.quote('-fPIC -O2')} LDFLAGS={shlex.quote(lib_flags)} -j1",
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "p0f", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "p0f-client", os.path.join(self.source_folder, "tools"), os.path.join(self.package_folder, "bin"))
        copy(self, "p0f-sendsyn", os.path.join(self.source_folder, "tools"), os.path.join(self.package_folder, "bin"))
        copy(self, "p0f-sendsyn6", os.path.join(self.source_folder, "tools"), os.path.join(self.package_folder, "bin"))
        copy(self, "p0f.fp", self.source_folder, os.path.join(self.package_folder, "share", "p0f"))
        copy(self, "README", self.source_folder, os.path.join(self.package_folder, "share", "doc", "p0f"))
        copy(self, "docs/COPYING", self.source_folder, os.path.join(self.package_folder, "share", "licenses", "p0f"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.define_path("P0F_DATA_DIR", os.path.join(self.package_folder, "share", "p0f"))
        self.runenv_info.define_path("P0F_DATA_DIR", os.path.join(self.package_folder, "share", "p0f"))
