#!/usr/bin/env python3
"""Conan recipe — acf-unbound 0.1.0 (Alpine Configuration Framework app for unbound).

Pure Lua + data package: the Makefile only copies unbound* files (cp -a) and
has no compile toolchain. Adapted for HarmonyOS PC (arm64).

Installs into usr/share/acf/app/unbound/{unbound-controller.lua,
unbound-model.lua, unbound.menu, unbound.roles}. The ACF web framework
(acf-core) auto-discovers apps under share/acf/app/*.

Runtime deps:
  - acf-core/0.24.1  (ACF framework: lua mvc, cgi-bin, modelfunctions)
  - unbound/1.22.0   (the DNS server this app configures)
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class AcfUnboundConan(ConanFile):
    name = "acf-unbound"
    version = "0.1.0"
    description = ("Alpine Configuration Framework (ACF) app - web UI to "
                   "configure the unbound DNS server")
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-unbound"
    url = "https://gitlab.alpinelinux.org/acf/acf-unbound"

    package_type = "application"

    settings = "os", "arch"

    def validate(self):
        # R32: os check must accept both Linux and OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ACF web framework + the unbound server this app manages
        self.requires("acf-core/0.24.1")
        self.requires("unbound/1.22.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # noarch: no compilation targets, only apply patches if any.
        apply_conandata_patches(self)

    def package(self):
        # Makefile installs into $package_folder/usr/share/acf/app/unbound
        # (config.mk: prefix=/usr, appdir=${datadir}/acf/app). Keep FHS layout.
        self.run("make install DESTDIR={} -j1".format(self.package_folder),
                 cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        # Pure data/Lua package: no C/C++ libraries or binaries.
        # ACF apps are discovered by acf-core at usr/share/acf/app/<name>.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
