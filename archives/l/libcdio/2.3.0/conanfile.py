#!/usr/bin/env python3
"""Conan recipe for the libcdio C libraries."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibcdioConan(ConanFile):
    name = "libcdio"
    version = "2.3.0"
    description = "光盘输入与控制库 — 用于 CD-ROM 和光盘镜像访问的便携式库，包含 ISO-9660/UDF 文件系统支持"
    license = "GPL-3.0"
    homepage = "https://www.gnu.org/software/libcdio/"
    url = "https://github.com/libcdio/libcdio"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # OHOS workers and Linux/QEMU cross-tests both need self-contained
        # test and CLI binaries; libtool consumes -all-static and otherwise
        # drops -static from executable link commands.
        if self.settings.os == "OHOS":
            # libtool consumes -all-static and otherwise drops -static from
            # executable link commands even when LDFLAGS contains it.
            tc.extra_ldflags.append("-all-static")
        tc.configure_args.append("--disable-example-progs")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Run the complete upstream test suite in the same build tree.
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # libiso9660 and libudf both link against libcdio. Keeping all three
        # archives in dependency order makes the aggregate Conan target usable
        # for C consumers such as cdw.
        self.cpp_info.libs = ["iso9660", "udf", "cdio"]
        # OpenHarmony exposes iconv in libc; there is no separate libiconv.
        if self.settings.os != "OHOS":
            self.cpp_info.system_libs = ["iconv"]
        if self.settings.os == "Macos":
            self.cpp_info.frameworks = ["CoreFoundation", "DiskArbitration", "IOKit"]
        self.cpp_info.set_property("cmake_file_name", "libcdio")
        self.cpp_info.set_property("cmake_target_name", "libcdio::libcdio")
        self.cpp_info.set_property("pkg_config_name", "libcdio")
