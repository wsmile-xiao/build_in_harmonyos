#!/usr/bin/env python3
"""Conan recipe — acf-kamailio 0.10.0 (Alpine Configuration Framework Kamailio module).

Pure-Lua ACF module: a Makefile would copy Lua controller/model scripts and
HTML view templates (.lsp) into /usr/share/acf/app/kamailio via
`make install DESTDIR=...`. However, the upstream Makefile's `install` target
also runs a symlink loop over `$(acflibdir)/db-*.lsp` (acf-core's
/usr/share/acf/lib), which does not exist during Conan's isolated build, and
the release tarball ships two dangling relative symlinks into acf-core's
app/ directory. Therefore the recipe bypasses `make install` and handles
packaging manually:
  1. Copy all kamailio-* files into share/acf/app/kamailio/.
  2. Materialize the two shared view templates referenced as dangling
     symlinks (kamailio-edit-html.lsp -> ../filedetails-html.lsp,
     kamailio-status-html.lsp -> ../status-html.lsp) from acf-core's
     share/acf/app/ as regular files — functionally equivalent to upstream.
  3. Normalize the /usr-prefixed layout to the standard Conan package layout
     (consistent with acf-core/acf-mdadm/acf-mariadb conventions).

No C sources are compiled; `make all` is a no-op.

Runtime dependencies (from `require()` in kamailio-controller.lua / kamailio-model.lua):
- acf-core: mvc.lua dispatch + modelfunctions (lib/modelfunctions.lua).
- acf-db: dbcontrollerfunctions.lua + dbmodelfunctions.lua.
- acf-lib-lua5.4: acf.fs / acf.format / acf.validator / acf.db.
- luaposix: posix.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.layout import basic_layout


class AcfKamailioConan(ConanFile):
    name = "acf-kamailio"
    version = "0.10.0"
    description = "Alpine Configuration Framework kamailio module — web-based admin interface for Kamailio SIP server"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-kamailio"
    url = "https://gitlab.alpinelinux.org/acf/acf-kamailio"

    # Pure-Lua module package (no binary, no library)
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # acf-core provides mvc.lua dispatch + modelfunctions (lib/modelfunctions.lua).
        # acf-core/0.24.1 已合入 main 并发布到 ohpcd 制品仓。
        self.requires("acf-core/0.24.1")
        # acf-db provides dbcontrollerfunctions.lua and dbmodelfunctions.lua,
        # imported via require("dbcontrollerfunctions") / require("dbmodelfunctions")
        # in kamailio-controller.lua and kamailio-model.lua.
        # acf-db/0.2.1 已合入 main 并发布到 ohpcd 制品仓。
        self.requires("acf-db/0.2.1")
        # acf-lib-lua5.4 provides acf.fs / acf.format / acf.validator / acf.db,
        # imported in kamailio-model.lua (NOT acf-core — see acf-lib-lua5.4).
        self.requires("acf-lib-lua5.4/0.11.1")
        # luaposix provides `posix`, imported at the top of kamailio-model.lua.
        self.requires("luaposix/36.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R32: recipe supports Linux and OHOS targets only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-kamailio does not support os={self.settings.os}")
        apply_conandata_patches(self)
        # `make all` is a no-op (Makefile `all:` empty); validates Makefile parse.
        self.run(f"make -C {self.source_folder} -j1 all", env="conanbuild")

    def package(self):
        # Manual packaging instead of `make install`:
        # The upstream Makefile's `install` target runs a loop over
        # `$(acflibdir)/db-*.lsp` to create db-* symlinks, and the release
        # tarball contains two dangling relative symlinks into acf-core's
        # app/ directory. We replicate the install logic here and materialize
        # the shared views from acf-core's share/acf/app/ as regular files.
        app_dir = os.path.join(
            self.package_folder, "usr", "share", "acf", "app", "kamailio"
        )
        os.makedirs(app_dir, exist_ok=True)

        # Copy all kamailio-* source files (controller, model, menu, roles, views)
        src = self.source_folder
        for entry in os.listdir(src):
            if entry.startswith("kamailio"):
                copy(self, entry, src=src, dst=app_dir)

        # Normalize /usr-prefixed layout to standard Conan package layout.
        # usr/share/acf/app/kamailio/ → share/acf/app/kamailio/
        usr = os.path.join(self.package_folder, "usr")
        if os.path.isdir(usr):
            for entry in os.listdir(usr):
                src_path = os.path.join(usr, entry)
                dst_path = os.path.join(self.package_folder, entry)
                if not os.path.lexists(dst_path):
                    os.rename(src_path, dst_path)
            shutil.rmtree(usr, ignore_errors=True)

        # Materialize shared view templates from acf-core.
        # Upstream ships these as dangling relative symlinks into acf-core's
        # app/ directory; cross-package symlinks cannot resolve in Conan's
        # isolated package model, so copy the templates as regular files.
        final_app = os.path.join(
            self.package_folder, "share", "acf", "app", "kamailio"
        )
        acf_core = self.dependencies["acf-core"]
        core_app = os.path.join(acf_core.package_folder, "share", "acf", "app")
        view_map = {
            "kamailio-edit-html.lsp": "filedetails-html.lsp",
            "kamailio-status-html.lsp": "status-html.lsp",
        }
        for dest_name, src_name in view_map.items():
            dest_path = os.path.join(final_app, dest_name)
            src_path = os.path.join(core_app, src_name)
            # Remove existing file/symlink from source copy if present
            if os.path.exists(dest_path) or os.path.islink(dest_path):
                os.remove(dest_path)
            if os.path.isfile(src_path):
                copy(self, src_name, src=core_app, dst=final_app)
                # Rename to kamailio-* prefix (copy keeps original name)
                os.rename(
                    os.path.join(final_app, src_name), dest_path
                )
                self.output.info(
                    f"Materialized shared view: {src_name} -> {dest_name}"
                )
            else:
                self.output.warning(
                    f"acf-core view {src_name} not found at {src_path}; "
                    f"shared view {dest_name} will be missing"
                )

    def package_info(self):
        # R32: settings.os check scoped to supported platforms
        if self.settings.os not in ("Linux", "OHOS"):
            return
        # Pure-Lua module: no compiled library, no binary.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        # ACF app dir: modules are installed under share/acf/app/kamailio/
        self.cpp_info.resdirs = ["share/acf/app/kamailio"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "acf-kamailio")
        self.cpp_info.set_property("cmake_target_name", "acf_kamailio::acf_kamailio")
