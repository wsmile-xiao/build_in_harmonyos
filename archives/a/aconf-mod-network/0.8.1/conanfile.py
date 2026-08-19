#!/usr/bin/env python3
"""Conan recipe for aconf-mod-network 0.8.1.

aconf-mod-network is the network module of Alpine's aconf (Alpine
Configurator). It is a pure Lua module installed by Alpine as the
aconf-mod-network subpackage; packaging mirrors that split: only
aconf/modules/network.lua is installed into share/lua/5.3/aconf/modules/.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AconfModNetworkConan(ConanFile):
    name = "aconf-mod-network"
    version = "0.8.1"
    description = "Alpine Configurator network administration module"
    license = "BSD-2-Clause"
    homepage = "https://gitlab.alpinelinux.org/kunkku/aconf/"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        lua_moddir = os.path.join(
            self.package_folder, "share", "lua", "5.3", "aconf", "modules"
        )
        os.makedirs(lua_moddir, exist_ok=True)
        src = os.path.join(self.source_folder, "aconf", "modules", "network.lua")
        if not os.path.isfile(src):
            raise FileNotFoundError(f"upstream module not found: {src}")
        shutil.copy2(src, os.path.join(lua_moddir, "network.lua"))

        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/lua"]
