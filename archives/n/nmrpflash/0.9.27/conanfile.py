#!/usr/bin/env python3
"""Conan recipe for nmrpflash 0.9.27 — Netgear Unbrick Utility."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class NmrpflashConan(ConanFile):
    name = "nmrpflash"
    version = "0.9.27"
    description = "Netgear Unbrick Utility — flash Netgear routers with alternative firmware"
    license = "GPL-3.0"
    homepage = "https://github.com/jclehner/nmrpflash"
    url = "https://github.com/jclehner/nmrpflash"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libnl/3.7.0")
        self.requires("libpcap/1.10.6")

    def layout(self):
        basic_layout(self)

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Get dependency info from conan
        libnl = self.dependencies["libnl"]
        libpcap = self.dependencies["libpcap"]
        # libnl3 standard layout: headers under package_folder/include/libnl3/
        # Prefer this known path over cpp_info.includedirs (which may be "include" without "libnl3")
        nl_include = libnl.package_folder + "/include/libnl3"
        if not os.path.isdir(nl_include) and libnl.cpp_info.includedirs:
            nl_include = os.path.join(libnl.package_folder, libnl.cpp_info.includedirs[0])
        opt_level = "-O2" if self.settings.build_type == "Release" else "-O0 -g"
        cflags = (f"-fPIC {opt_level} -DNMRPFLASH_VERSION=\\\"{self.version}\\\""
                  f" -D_UAPI_LINUX_SOCKET_H"
                  f" -D__kernel_sa_family_t=ushort"
                  f" -I{nl_include}"
                  f" -I{libpcap.cpp_info.includedirs[0] if libpcap.cpp_info.includedirs else libpcap.package_folder + '/include'}")
        ldflags = (f"-L{libnl.package_folder}/lib -L{libpcap.package_folder}/lib"
                   f" -lnl-route-3 -lnl-3 -lpcap")
        self.run(f"make CC={self.settings.compiler} "
                 f"CFLAGS='{cflags}' "
                 f"LDFLAGS='{ldflags}'",
                 cwd=self.source_folder)
        # Run upstream make check (added via patch)
        if can_run(self):
            self.run("make check", cwd=self.source_folder)

    def package(self):
        self.run(f"make install PREFIX={self.package_folder}", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []