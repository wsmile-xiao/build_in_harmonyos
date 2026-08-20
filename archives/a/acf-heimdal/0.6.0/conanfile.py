#!/usr/bin/env python3
"""Conan recipe — acf-heimdal 0.6.0 (Alpine Configuration Framework heimdal module).

Pure-Lua ACF module for Heimdal Kerberos: a Makefile copies Lua
controller/model scripts and HTML view templates (.lsp) into
/usr/share/acf/app/heimdal via `make install DESTDIR=...`. No C sources are
compiled; `make all` is a no-op.

The upstream tarball ships two dangling relative symlinks into acf-core's
shared views:
  heimdal-expert-html.lsp -> ../expert-html.lsp
  heimdal-status-html.lsp -> ../status-html.lsp
A relative path cannot resolve across independent Conan package_folders, and
HMDFS rejects symlink creation. The recipe therefore materializes those two
views as regular files copied from acf-core's share/acf/app/. The /usr-prefixed
layout produced by `make install` (config.mk bakes prefix=/usr) is normalized
to the standard Conan package layout (share/).

Runtime dependencies:
- acf-core:       the ACF framework (mvc.lua dispatch, modelfunctions,
                  htmlviewfunctions, cfe) plus the shared view templates.
- acf-lib-lua5.4: the ACF Lua libraries (acf.fs, acf.html) imported by the
                  model (fs.write_file) and view (html.html_escape).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AcfHeimdalConan(ConanFile):
    name = "acf-heimdal"
    version = "0.6.0"
    description = "Alpine Configuration Framework heimdal module — web-based admin interface for Heimdal Kerberos"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-heimdal"
    url = "https://gitlab.alpinelinux.org/acf/acf-heimdal"

    # Pure-Lua module package (no binary, no library)
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # acf-core provides mvc.lua dispatch, modelfunctions (getstatus,
        # getfiledetails, setfiledetails, run_executable), htmlviewfunctions,
        # cfe, and the shared view templates (expert-html.lsp / status-html.lsp).
        # acf-core/0.24.1 已合入 main 并发布到 ohpcd 制品仓。
        self.requires("acf-core/0.24.1")
        # acf-lib-lua5.4 provides acf.fs (fs.write_file in heimdal-model.lua)
        # and acf.html (html.html_escape in heimdal-klist-html.lsp).
        self.requires("acf-lib-lua5.4/0.11.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R32: recipe supports Linux and OHOS targets only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-heimdal does not support os={self.settings.os}")
        apply_conandata_patches(self)
        # `make all` is a no-op (Makefile `all:` empty); validates Makefile parse.
        self.run(f"make -C {self.source_folder} -j1 all", env="conanbuild")

    def package(self):
        # `make install DESTDIR=<pkg>` runs `mkdir -p` + `cp -a heimdal*`,
        # copying controller/model/menu/roles/klist-view and the two dangling
        # symlinks into <pkg>/usr/share/acf/app/heimdal (config.mk prefix=/usr).
        self.run(
            f"make -C {self.source_folder} -j1 install "
            f'DESTDIR="{self.package_folder}"',
            env="conanbuild",
        )

        # Normalize the /usr-prefixed layout to the standard Conan package
        # layout (usr/share/... -> share/...), consistent with acf-core,
        # acf-mdadm, acf-openssh and acf-mariadb conventions.
        usr = os.path.join(self.package_folder, "usr")
        if os.path.isdir(usr):
            for entry in os.listdir(usr):
                src_path = os.path.join(usr, entry)
                dst_path = os.path.join(self.package_folder, entry)
                if not os.path.lexists(dst_path):
                    os.rename(src_path, dst_path)
            shutil.rmtree(usr, ignore_errors=True)

        # Materialize the two dangling relative symlinks (expert/status) as
        # regular files copied from acf-core's share/acf/app/. HMDFS rejects
        # symlink creation and a relative path cannot resolve across
        # independent Conan package_folders.
        app_dir = os.path.join(
            self.package_folder, "share", "acf", "app", "heimdal"
        )
        core_app_dir = os.path.join(
            self.dependencies["acf-core"].package_folder, "share", "acf", "app"
        )
        view_map = {
            "heimdal-expert-html.lsp": "expert-html.lsp",
            "heimdal-status-html.lsp": "status-html.lsp",
        }
        for dest_name, src_name in view_map.items():
            dest_path = os.path.join(app_dir, dest_name)
            if os.path.lexists(dest_path):
                os.unlink(dest_path)
            shutil.copyfile(os.path.join(core_app_dir, src_name), dest_path)
            self.output.info(
                f"Materialized shared view: {src_name} -> {dest_name}"
            )

    def package_info(self):
        # R32: settings.os check scoped to supported platforms
        if self.settings.os not in ("Linux", "OHOS"):
            return
        # Pure-Lua module: no compiled library, no binary.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        # ACF app dir: modules are installed under share/acf/app/heimdal/
        self.cpp_info.resdirs = ["share/acf/app/heimdal"]
        self.cpp_info.set_property("cmake_file_name", "acf-heimdal")
        self.cpp_info.set_property("cmake_target_name", "acf_heimdal::acf_heimdal")
