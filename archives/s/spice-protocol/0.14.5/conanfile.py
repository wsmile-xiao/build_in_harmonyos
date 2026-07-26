import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class SpiceProtocolConan(ConanFile):
    name = "spice-protocol"
    version = "0.14.5"
    description = "SPICE protocol headers"
    license = "BSD-3-Clause"
    homepage = "https://www.spice-space.org/"
    url = "https://gitlab.freedesktop.org/spice/spice-protocol"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "spice"),
            dst=os.path.join(self.package_folder, "include", "spice-1", "spice"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        pkgconfig = os.path.join(self.package_folder, "share", "pkgconfig")
        content = """prefix=${pcfiledir}/../..
includedir=${prefix}/include

Name: spice-protocol
Description: SPICE protocol headers
Version: 0.14.5
Cflags: -I${includedir}/spice-1
"""
        save(self, os.path.join(pkgconfig, "spice-protocol.pc"), content)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = [os.path.join("include", "spice-1")]
        self.cpp_info.set_property("cmake_file_name", "spice-protocol")
        self.cpp_info.set_property("cmake_target_name", "spice-protocol::spice-protocol")
        self.cpp_info.set_property("pkg_config_name", "spice-protocol")
        self.cpp_info.libs = []
