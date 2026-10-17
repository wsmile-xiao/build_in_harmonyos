#!/usr/bin/env python3
"""Conan recipe for the Alpine Configuration Framework PPP module."""

import filecmp
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.layout import basic_layout


class AcfPppConan(ConanFile):
    name = "acf-ppp"
    version = "0.5.0"
    description = "Alpine Configuration Framework web interface for PPP"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-ppp"
    url = "https://gitlab.alpinelinux.org/acf/acf-ppp"
    topics = ("acf", "lua", "ppp", "pppoe", "web-admin")
    # Pure Lua/LSP resources for the ACF dispatcher; no CLI is installed.
    package_type = "unknown"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # The ACF dispatcher and shared model helpers are required at runtime.
        self.requires("acf-core/0.24.1", run=True)
        self.requires("acf-lib-lua5.4/0.11.1", run=True)
        # Alpine's package metadata declares ppp as a hard runtime dependency.
        # Keep it as a Conan dependency; ppp is adapted independently in #2118.
        self.requires("ppp/2.5.2", run=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-ppp supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _is_within(root, path):
        try:
            return os.path.commonpath((root, path)) == root
        except ValueError:
            return False

    @classmethod
    def _materialize_dependency_resources(
        cls, source_root, destination_root, resources
    ):
        """Copy dependency-owned data when cross-package links are unsupported."""
        source_root = os.path.realpath(source_root)
        destination_root = os.path.realpath(destination_root)

        for destination_name, source_name in resources.items():
            source_lexical_path = os.path.abspath(
                os.path.join(source_root, source_name)
            )
            source_path = os.path.realpath(source_lexical_path)
            destination_path = os.path.abspath(
                os.path.join(destination_root, destination_name)
            )
            destination_parent = os.path.realpath(
                os.path.dirname(destination_path)
            )

            if not cls._is_within(source_root, source_path):
                raise ConanInvalidConfiguration(
                    f"shared resource escapes dependency root: {source_name}"
                )
            if not cls._is_within(source_root, source_lexical_path):
                raise ConanInvalidConfiguration(
                    f"shared resource escapes dependency root: {source_name}"
                )
            if not cls._is_within(destination_root, destination_path):
                raise ConanInvalidConfiguration(
                    f"materialized resource escapes package root: {destination_name}"
                )
            if not cls._is_within(destination_root, destination_parent):
                raise ConanInvalidConfiguration(
                    f"materialized parent escapes package root: {destination_name}"
                )
            if (
                not os.path.isfile(source_path) or os.path.islink(source_lexical_path)
            ):
                raise ConanInvalidConfiguration(
                    f"dependency resource is not a regular file: {source_path}"
                )

            # copy2() follows an existing destination link. Remove even a
            # dangling link first so the package receives a regular file.
            if os.path.lexists(destination_path):
                os.unlink(destination_path)
            shutil.copy2(source_path, destination_path)

            if os.path.islink(destination_path) or not os.path.isfile(
                destination_path
            ):
                raise ConanInvalidConfiguration(
                    f"failed to materialize regular file: {destination_path}"
                )
            if not filecmp.cmp(source_path, destination_path, shallow=False):
                raise ConanInvalidConfiguration(
                    f"materialized resource differs from dependency: {destination_name}"
                )

    def build(self):
        # This is a pure Lua/LSP module. The empty all target still validates
        # that the upstream Makefile parses on the target platform.
        self.run(f"make -C {self.source_folder} -j1 all", env="conanbuild")

    def package(self):
        self.run(
            f"make -C {self.source_folder} install "
            f"DESTDIR={self.package_folder} -j1",
            env="conanbuild",
        )

        # The release links four app views to shared acf-core templates. OHOS
        # drops dangling links during extraction and HMDFS rejects symlink(),
        # so materialize byte-identical copies from the declared dependency.
        app_dir = os.path.join(
            self.package_folder, "usr", "share", "acf", "app", "ppp"
        )
        shared_dir = os.path.join(
            self.dependencies["acf-core"].package_folder,
            "share",
            "acf",
            "app",
        )
        shared_views = {
            "ppp-editchap-html.lsp": "filedetails-html.lsp",
            "ppp-editpap-html.lsp": "filedetails-html.lsp",
            "ppp-editpeer-html.lsp": "filedetails-html.lsp",
            "ppp-status-html.lsp": "status-html.lsp",
        }
        self._materialize_dependency_resources(shared_dir, app_dir, shared_views)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["usr/share/acf/app/ppp"]
