#!/usr/bin/env python3
"""Conan recipe — acf-lvm2 0.7.0 (Alpine Configuration Framework lvm2 module).

Pure-Lua ACF application module: a recursive Makefile copies Lua
controller/model scripts and HTML view templates (.lsp) into a
/usr/share/acf/app/lvm2 layout via `make install DESTDIR=...`. No C
sources are compiled; `make all` is a no-op. The recipe mirrors that:
source() fetches the upstream tarball, build() runs `make all` (no-op,
validates Makefile syntax), and package() runs `make install DESTDIR=<pkg>`.
The /usr-prefixed layout is preserved and exposed via cpp_info.resdirs.

Runtime dependency: acf-core (the ACF framework mvc.lua that dispatches this
module's controller; lvm2-model.lua requires acf.fs / acf.format).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AcfLvm2Conan(ConanFile):
    name = "acf-lvm2"
    version = "0.7.0"
    description = "Alpine Configuration Framework lvm2 module — web-based admin interface for LVM"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-lvm2"
    url = "https://gitlab.alpinelinux.org/acf/acf-lvm2"

    # Pure-Lua module package (no binary, no library)
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime framework dependency; acf-core provides mvc.lua dispatch.
        # acf-core/0.24.1 已合入 main 并发布到 ohpcd 制品仓。
        self.requires("acf-core/0.24.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R32: recipe supports Linux and OHOS targets only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-lvm2 does not support os={self.settings.os}")
        apply_conandata_patches(self)
        # `make all` is a no-op (Makefile `all:` empty); validates Makefile parse.
        self.run(f"make -C {self.source_folder} -j1 all", env="conanbuild")

    def package(self):
        # `make install DESTDIR=<pkg>` copies lvm2* into <pkg>/usr/share/acf/app/lvm2;
        # config.mk bakes prefix=/usr, so files land under <pkg>/usr/...
        self.run(
            f"make -C {self.source_folder} install DESTDIR={self.package_folder} -j1",
            env="conanbuild",
        )

    def package_info(self):
        # Pure-Lua module: no cpp_info.libs, no bindirs.
        # Expose share/acf/app/lvm2 as resdir for consumers (acf-core mvc dispatch).
        self.cpp_info.resdirs = ["usr/share/acf/app/lvm2"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
