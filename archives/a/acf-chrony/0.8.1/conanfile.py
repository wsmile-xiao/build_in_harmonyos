#!/usr/bin/env python3
"""Conan recipe — acf-chrony 0.8.1 (Alpine Configuration Framework chrony app).

acf-chrony is a pure-Lua ACF application plugin package for chrony: a flat
recursive Makefile copies Lua controller/model scripts, .lsp view templates,
.menu and .roles files into a /usr-prefixed layout via `make install
DESTDIR=...`. No C sources are compiled. Three .lsp templates are symlinks
to shared acf-core templates (expert-html.lsp / logfile-html.lsp /
status-html.lsp) resolved at runtime by the acf-core dependency. The recipe
normalizes the /usr-prefixed layout to the standard Conan package layout
(share/, etc/).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AcfChronyConan(ConanFile):
    name = "acf-chrony"
    version = "0.8.1"
    description = "Alpine Configuration Framework chrony app — Web-based system administration interface for chrony"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-chrony"
    url = "https://gitlab.alpinelinux.org/acf/acf-chrony"

    # ACF application plugin package (Lua scripts + .lsp templates).
    # No CLI binaries shipped directly — CLI entry is acf-core's acf-cli.
    # R38: software-level commands.json declares this package (binary: false,
    # CLI entry provided by acf-core's acf-cli); no new commands added here.
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # acf-core provides the ACF framework (mvc, lib, www, CLI) and the
        # shared .lsp templates that this package's symlinks resolve to.
        self.requires("acf-core/0.24.1")
        # chrony is the runtime target being configured by this app plugin.
        self.requires("chrony/4.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        # R39: official source first; gitlab.alpinelinux.org may 418脚本UA,
        # fallback to distfiles.alpinelinux.org权威镜像 (同校验和).
        src = self.conan_data["sources"]
        try:
            get(self, **src, strip_root=True)
        except Exception:
            fb = "https://distfiles.alpinelinux.org/distfiles/v3.23/acf-chrony-v0.8.1.tar.gz"
            get(self, url=fb, sha256=src["sha256"], strip_root=True)

    def build(self):
        # R32: recipe supports Linux and OHOS targets only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-chrony does not support os={self.settings.os}")
        apply_conandata_patches(self)
        # Flat Makefile (app/bin/lib/lua/www). No C sources; nothing to
        # compile, but the `all` target must succeed (R9: -j1).
        # basic_layout keeps sources in source_folder — run make there.
        self.run(f"make -C {self.source_folder} -j1", env="conanbuild")

    def package(self):
        # make install with DESTDIR; config.mk bakes prefix=/usr so files land
        # under <pkg>/usr/share/acf/app/chrony/ — normalize to the standard
        # Conan layout (share/acf/app/chrony/).
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
        pkg = self.package_folder
        # Expose the packaged ACF app plugin search path so consumers (and the
        # acf-core CLI entry) can locate chrony's controller/model/.lsp via
        # the acf framework's appdir resolution.
        lua_path = ";".join([
            os.path.join(pkg, "share", "acf", "app", "chrony", "?.lua"),
        ])
        self.runenv_info.define("LUA_PATH", lua_path + ";;")
        # No bindirs (no CLI binaries in this plugin package).
        self.cpp_info.set_property("cmake_file_name", "acf-chrony")
        self.cpp_info.set_property("cmake_target_name", "acf-chrony::acf-chrony")
