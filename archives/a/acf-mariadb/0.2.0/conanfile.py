#!/usr/bin/env python3
"""Conan recipe — acf-mariadb 0.2.0 (Alpine Configuration Framework mariadb module).

Pure-Lua ACF module: a Makefile would copy Lua controller/model scripts and
HTML view templates (.lsp) into /usr/share/acf/app/mysql via
`make install DESTDIR=...`. However, the upstream Makefile's `install` target
also creates symlinks referencing acflibdir (acf-core's /usr/share/acf/lib),
which does not exist during Conan's isolated build. Therefore the recipe
bypasses `make install` and handles packaging manually:
  1. Copy all mysql-* files into share/acf/app/mysql/.
  2. Copy shared view templates from acf-core's lib/ (db-*.lsp) as
     mysql-*.lsp — functionally equivalent to the upstream symlinks.
  3. Normalize the /usr-prefixed layout to the standard Conan package layout
     (consistent with acf-core/acf-mdadm/acf-db conventions).

No C sources are compiled; `make all` is a no-op.

Runtime dependencies:
- acf-core: the ACF framework (mvc.lua, modelfunctions, acf.fs, acf.format, acf.db).
- acf-db: provides dbcontrollerfunctions.lua and dbmodelfunctions.lua.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.layout import basic_layout


class AcfMariadbConan(ConanFile):
    name = "acf-mariadb"
    version = "0.2.0"
    description = "Alpine Configuration Framework mariadb module — web-based admin interface for MariaDB"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-mariadb"
    url = "https://gitlab.alpinelinux.org/acf/acf-mariadb"

    # Pure-Lua module package (no binary, no library)
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # acf-core provides mvc.lua dispatch, modelfunctions, acf.fs, acf.format, acf.db.
        # acf-core/0.24.1 已合入 main 并发布到 ohpcd 制品仓。
        self.requires("acf-core/0.24.1")
        # acf-db provides dbcontrollerfunctions.lua and dbmodelfunctions.lua,
        # imported via require("dbcontrollerfunctions") / require("dbmodelfunctions")
        # in mysql-controller.lua and mysql-model.lua.
        # acf-db/0.2.1 已合入 main 并发布到 ohpcd 制品仓。
        self.requires("acf-db/0.2.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R32: recipe supports Linux and OHOS targets only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-mariadb does not support os={self.settings.os}")
        apply_conandata_patches(self)
        # `make all` is a no-op (Makefile `all:` empty); validates Makefile parse.
        self.run(f"make -C {self.source_folder} -j1 all", env="conanbuild")

    def package(self):
        # Manual packaging instead of `make install`:
        # The upstream Makefile's `install` target references acflibdir
        # (/usr/share/acf/lib) for symlink creation, which does not exist
        # during Conan's isolated build. We replicate the install logic here
        # and normalize the /usr-prefixed layout (consistent with acf-core
        # and acf-mdadm package conventions).
        app_dir = os.path.join(
            self.package_folder, "usr", "share", "acf", "app", "mysql"
        )
        os.makedirs(app_dir, exist_ok=True)

        # Copy all mysql-* source files (controller, model, menu, roles, views)
        src = self.source_folder
        for entry in os.listdir(src):
            if entry.startswith("mysql"):
                copy(self, entry, src=src, dst=app_dir)

        # Normalize /usr-prefixed layout to standard Conan package layout.
        # This is consistent with acf-core and acf-mdadm conventions:
        # usr/share/acf/app/mysql/ → share/acf/app/mysql/
        usr = os.path.join(self.package_folder, "usr")
        if os.path.isdir(usr):
            for entry in os.listdir(usr):
                src_path = os.path.join(usr, entry)
                dst_path = os.path.join(self.package_folder, entry)
                if not os.path.lexists(dst_path):
                    os.rename(src_path, dst_path)
            shutil.rmtree(usr, ignore_errors=True)

        # Copy shared view templates from acf-core into this package.
        # Upstream creates symlinks: mysql-*-html.lsp -> ../../lib/db-*-html.lsp
        # However, acf-core does NOT have db-*-html.lsp in its lib/.
        # Instead, the base view templates live in acf-core's share/acf/app/:
        #   expert-html.lsp, logfile-html.lsp, status-html.lsp
        # The upstream Makefile's symlink loop uses acflibdir=/usr/share/acf/lib
        # but acf-core actually installs these views into share/acf/app/.
        # We copy the base templates and rename to the mysql-* prefix.
        final_app = os.path.join(
            self.package_folder, "share", "acf", "app", "mysql"
        )
        acf_core = self.dependencies["acf-core"]
        core_app = os.path.join(acf_core.package_folder, "share", "acf", "app")
        view_map = {
            "mysql-expert-html.lsp": "expert-html.lsp",
            "mysql-logfile-html.lsp": "logfile-html.lsp",
            "mysql-status-html.lsp": "status-html.lsp",
        }
        for dest_name, src_name in view_map.items():
            dest_path = os.path.join(final_app, dest_name)
            src_path = os.path.join(core_app, src_name)
            # Remove existing file/symlink from source copy if present
            if os.path.exists(dest_path) or os.path.islink(dest_path):
                os.remove(dest_path)
            if os.path.isfile(src_path):
                copy(self, src_name, src=core_app, dst=final_app)
                # Rename to mysql-* prefix (copy keeps original name)
                os.rename(
                    os.path.join(final_app, src_name), dest_path
                )
                self.output.info(
                    f"Copied shared view: {src_name} -> {dest_name}"
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
        # ACF app dir: modules are installed under share/acf/app/mysql/
        self.cpp_info.resdirs = ["share/acf/app/mysql"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "acf-mariadb")
        self.cpp_info.set_property("cmake_target_name", "acf_mariadb::acf_mariadb")
