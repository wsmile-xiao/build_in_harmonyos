#!/usr/bin/env python3
"""Conan recipe for libmpdclient 2.23."""

import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.meson import Meson, MesonToolchain


class LibmpdclientConan(ConanFile):
    name = "libmpdclient"
    version = "2.23"
    description = "C client library for the Music Player Daemon protocol"
    license = "BSD-2-Clause AND BSD-3-Clause"
    homepage = "https://www.musicpd.org/libs/libmpdclient/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["documentation"] = "false"
        tc.project_options["test"] = "false"
        tc.project_options["tcp"] = "true"
        tc.generate()
        self._inject_ohos_archiver()

    def _inject_ohos_archiver(self):
        if self.settings.os != "OHOS":
            return

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        with open(native_file, encoding="utf-8") as f:
            content = f.read()

        if "\nar =" in content:
            return

        archiver = os.environ.get("AR")
        candidates = [
            archiver,
            "/data/service/hnp/binutils.org/binutils_2.45/bin/ar",
            "/data/service/hnp/bin/ar",
            "/storage/Users/currentUser/tmp/wrappers/llvm-ar",
            "/storage/Users/currentUser/tmp/wrappers/ar",
        ]
        ar_path = next(
            (path for path in candidates if path and os.path.exists(path)), None
        )
        if not ar_path:
            raise RuntimeError("Unable to locate an OHOS archiver for Meson")

        marker = "[binaries]\nc ="
        if marker not in content:
            raise RuntimeError("Unable to inject Meson archiver into native file")

        content = content.replace(marker, f"[binaries]\nar = '{ar_path}'\nc =", 1)
        with open(native_file, "w", encoding="utf-8") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        self._materialize_ohos_shared_links()

    def _materialize_ohos_shared_links(self):
        if self.settings.os != "OHOS" or not self.options.shared:
            return

        libdir = os.path.join(self.package_folder, "lib")
        versioned = os.path.join(libdir, "libmpdclient.so.2.23")
        if not os.path.exists(versioned):
            return

        for name in ("libmpdclient.so.2", "libmpdclient.so"):
            target = os.path.join(libdir, name)
            if not os.path.exists(target):
                shutil.copyfile(versioned, target)

    def package_info(self):
        self.cpp_info.libs = ["mpdclient"]
        self.cpp_info.set_property("cmake_file_name", "libmpdclient")
        self.cpp_info.set_property(
            "cmake_target_name", "libmpdclient::libmpdclient"
        )
        self.cpp_info.set_property("pkg_config_name", "libmpdclient")
