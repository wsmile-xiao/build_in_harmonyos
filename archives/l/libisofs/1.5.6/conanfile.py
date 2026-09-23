#!/usr/bin/env python3
"""Conan recipe — libisofs 1.5.6 (Autotools).

libisofs is a library to create and read ISO 9660 filesystems (with
Rock Ridge, Joliet, El Torito extensions) for HarmonyOS PC aarch64.
Static library build; the zisofs filter pulls zlib symbols, declared
as system_libs so consumers link -lz.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibisofsConan(ConanFile):
    name = "libisofs"
    version = "1.5.6"
    description = "Library to create and read ISO 9660 filesystems with Rock Ridge, Joliet and El Torito extensions"
    license = "GPL-2.0-or-later"
    homepage = "http://libburnia-project.org"
    url = "http://libburnia-project.org"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Upstream config.guess cannot recognize HarmonyOS uname output and
            # config.sub has no ohos system; the linux-ohos triplet works
            # together with 0001-config.sub.patch.
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Library file is libisofs.a; Conan cpp_info.libs uses the bare name
        # (no "lib" prefix / extension), matching the shipped libisofs-1.pc.
        self.cpp_info.libs = ["isofs"]
        # zisofs filter uses zlib (compress2/uncompress/compressBound); the
        # archive does not bundle these symbols, so consumers must link -lz.
        self.cpp_info.system_libs = ["z"]
