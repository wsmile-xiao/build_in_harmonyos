#!/usr/bin/env python3
"""Conan recipe for mongoose 7.21 — embedded web server library.

Mongoose is a single-file C/C++ library (mongoose.c + mongoose.h) providing
HTTP/HTTPS/MQTT/WebSocket protocol support. Built as static library only
(shared lib has ELF signing issues on OHOS).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class MongooseConan(ConanFile):
    name = "mongoose"
    version = "7.21"
    description = "Embedded Web server C/C++ library with SSL/TLS support"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/cesanta/mongoose"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R33: Get compiler from Conan conf, never from shell env vars
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = _ce.get("c", "clang")
        ar = _ce.get("ar", "llvm-ar")

        src = self.source_folder

        # Mongoose is a single-file amalgamated library (mongoose.c + mongoose.h)
        self.run(f"{cc} -O2 -fPIC -c {src}/mongoose.c -o {src}/mongoose.o", cwd=src)
        self.run(f"{ar} rcs {src}/libmongoose.a {src}/mongoose.o", cwd=src)

    def package(self):
        copy(self, "mongoose.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "libmongoose.a", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["mongoose"]
