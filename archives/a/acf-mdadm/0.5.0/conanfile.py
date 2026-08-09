#!/usr/bin/env python3
"""Conan recipe — acf-mdadm 0.5.0 (Alpine Configuration Framework mdadm module).

Pure-Lua ACF module for mdadm: a Makefile copies Lua controllers/models and
HTML .lsp views into /usr/share/acf/app/mdadm via `make install DESTDIR=...`.
No C sources are compiled; the Makefile uses only cp/mkdir (no coreutils
`install`), so no platform patch is required. The recipe normalizes the
/usr-prefixed layout to the standard Conan package layout (share/).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AcfMdadmConan(ConanFile):
    name = "acf-mdadm"
    version = "0.5.0"
    description = "Alpine Configuration Framework module for mdadm (Lua web admin UI)"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-mdadm"
    url = "https://gitlab.alpinelinux.org/acf/acf-mdadm"

    # Pure Lua/HTML module — no compiled binary, no bin/ output (no commands.json, R38 N/A)
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # acf-mdadm is a pure-Lua data module: its Makefile only copies files
        # into share/acf/app/mdadm — no compile/link against acf-core, so no
        # Conan dependency is needed (acf-core is a runtime framework, not a
        # build dependency; it has not been published to the artifact repo yet).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R32: recipe supports Linux and OHOS targets only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-mdadm does not support os={self.settings.os}")
        apply_conandata_patches(self)
        # Makefile `all` target is empty (pure data module). Run make to
        # satisfy the build step contract (R9: -j1).
        self.run(f"make -C {self.source_folder} -j1", env="conanbuild")

    def package(self):
        # make install with DESTDIR; config.mk bakes prefix=/usr so files land
        # under <pkg>/usr/... — normalize to the standard Conan layout.
        self.run(f"make -C {self.source_folder} install DESTDIR={self.package_folder} -j1",
                 env="conanbuild")
        usr = os.path.join(self.package_folder, "usr")
        if os.path.isdir(usr):
            for entry in os.listdir(usr):
                src = os.path.join(usr, entry)
                dst = os.path.join(self.package_folder, entry)
                if not os.path.lexists(dst):
                    os.rename(src, dst)
            shutil.rmtree(usr, ignore_errors=True)

    def package_info(self):
        # R32: settings.os check scoped to supported platforms
        if self.settings.os not in ("Linux", "OHOS"):
            return
        # Pure-Lua data module: no compiled library, no binary (R38 N/A).
        # Explicitly declare no libs/libdirs per code_style (adr-tools pattern).
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        # ACF app dir: modules are installed under share/acf/app/<name>/
        pkg = self.package_folder
        app_dir = os.path.join(pkg, "share", "acf", "app", "mdadm")
        self.output.info(f"acf-mdadm installed to: {app_dir}")
        self.cpp_info.set_property("cmake_file_name", "acf-mdadm")
        self.cpp_info.set_property("cmake_target_name", "acf_mdadm::acf_mdadm")
