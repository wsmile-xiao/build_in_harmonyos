"""Conan recipe — bottlerocket 0.05b3 (X10 FireCracker controller)"""
from conan import ConanFile
from conan.tools.files import get, copy
import os


class BottlerocketConan(ConanFile):
    name = "bottlerocket"
    version = "0.05b3"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    license = "GPL-2.0"
    description = "Controller for X10 FireCracker home automation kit"
    url = "https://packages.debian.org/bottlerocket"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # autotools build: ./configure && make
        cc_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_execs.get("c", "cc")
        self.run(f"CC={cc} ./configure --disable-dependency-tracking", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        copy(self, "br", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
