#!/usr/bin/env python3
"""Conan recipe for the Alpine ACF OpenSSH application module."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AcfOpensshConan(ConanFile):
    name = "acf-openssh"
    version = "0.11.2"
    description = "Alpine Configuration Framework application for OpenSSH"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-openssh"
    url = "https://gitlab.alpinelinux.org/acf/acf-openssh"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # These are runtime requirements of openssh-model.lua and the service
        # it manages. Keep them on the package itself, not only test_package.
        self.requires("acf-core/0.24.1")
        self.requires("acf-lib-lua5.4/0.11.1")
        self.requires("lua-subprocess/0.02")
        self.requires("luaposix/36.3.1.1")
        self.requires("lua/5.4.8")
        self.requires("openssh/10.0p1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-openssh supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Upstream has an empty all target. Running it still validates the
        # hand-written Makefile and keeps the build phase observable.
        self.run(f'make -C "{self.source_folder}" -j1 all', env="conanbuild")

    def package(self):
        # Preserve upstream's /usr ACF layout.
        self.run(
            f'make -C "{self.source_folder}" -j1 install '
            f'DESTDIR="{self.package_folder}"',
            env="conanbuild",
        )

        # The release archive contains three dangling relative symlinks into
        # acf-core. HMDFS rejects symlink creation, so materialize the exact
        # dependency templates as regular files for a portable no-link layout.
        app_dir = os.path.join(
            self.package_folder, "usr", "share", "acf", "app", "openssh"
        )
        core_app_dir = os.path.join(
            self.dependencies["acf-core"].package_folder, "share", "acf", "app"
        )
        view_templates = {
            "openssh-expert-html.lsp": "expert-html.lsp",
            "openssh-logfile-html.lsp": "logfile-html.lsp",
            "openssh-status-html.lsp": "status-html.lsp",
        }
        for name, source_name in view_templates.items():
            destination = os.path.join(app_dir, name)
            if os.path.lexists(destination):
                os.unlink(destination)
            shutil.copyfile(os.path.join(core_app_dir, source_name), destination)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["usr/share/acf/app/openssh"]
        self.cpp_info.set_property("cmake_file_name", "acf-openssh")
        self.cpp_info.set_property("cmake_target_name", "acf_openssh::acf_openssh")

        openssh = self.dependencies["openssh"]
        self.runenv_info.define(
            "ACF_OPENSSH_CONFIG",
            os.path.join(
                openssh.package_folder, "usr", "local", "etc", "sshd_config"
            ),
        )
