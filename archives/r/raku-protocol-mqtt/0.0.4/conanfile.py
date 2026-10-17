#!/usr/bin/env python3
"""Conan recipe for Protocol::MQTT 0.0.4."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RakuProtocolMqttConan(ConanFile):
    name = "raku-protocol-mqtt"
    version = "0.0.4"
    description = "Raku classes for encoding and decoding MQTT protocol packets"
    license = "Artistic-2.0"
    homepage = "https://github.com/Leont/raku-protocol-mqtt"
    url = "https://github.com/Leont/raku-protocol-mqtt"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("rakudo/2025.11", headers=False, libs=False, run=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Protocol::MQTT supports Linux and OHOS")
        if str(self.settings.arch) not in ("armv8", "x86_64"):
            raise ConanInvalidConfiguration("Protocol::MQTT recipe supports armv8 and x86_64")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        tests = [
            "t/01-filter.rakutest",
            "t/02-messages.rakutest",
            "t/03-dispatcher.rakutest",
            "t/04-client.rakutest",
        ]
        for test in tests:
            self.run(
                f"raku -Ilib {test}",
                cwd=self.source_folder,
                env=["conanbuild", "conanrun"],
            )

    def package(self):
        copy(self, "*.rakumod", src=os.path.join(self.source_folder, "lib"), dst=os.path.join(self.package_folder, "lib"))
        copy(self, "META6.json", src=self.source_folder, dst=self.package_folder)
        copy(self, "README.md", src=self.source_folder, dst=self.package_folder)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        module_path = os.path.join(self.package_folder, "lib")
        self.runenv_info.prepend_path("RAKULIB", module_path)
        self.buildenv_info.prepend_path("RAKULIB", module_path)
