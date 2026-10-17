#!/usr/bin/env python3
"""Conan recipe for the uWSGI router_http plugin 2.0.31."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class UwsgiRouterHttpConan(ConanFile):
    name = "uwsgi-router_http"
    version = "2.0.31"
    description = "uWSGI router_http plugin"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/unbit/uwsgi"
    url = "https://github.com/unbit/uwsgi"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        copy(self, "conandata.yml", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires("pcre2/10.45")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c") or os.environ.get("CC") or "cc"

    def _write_profile(self):
        profile_path = os.path.join(
            self.source_folder, "buildconf", "router_http_conan.ini"
        )
        save(
            self,
            profile_path,
            """[uwsgi]
inherit = minimal
xml = false
yaml = false
json = false
ssl = false
pcre = true
routing = true
debug = false
plugins = router_http
plugin_dir = .
embedded_plugins = null
as_shared_library = false
""",
        )
        return profile_path

    def build(self):
        self._write_profile()
        pcre2_bin = os.path.join(self.dependencies["pcre2"].package_folder, "bin")
        os.environ["PATH"] = pcre2_bin + os.pathsep + os.environ.get("PATH", "")
        os.environ["CC"] = self._compiler()
        os.environ["CPUCOUNT"] = "1"
        os.environ.setdefault("UWSGI_FORCE_REBUILD", "1")
        self.run(
            "python3 uwsgiconfig.py --plugin plugins/router_http router_http_conan",
            cwd=self.source_folder,
        )

        plugin = os.path.join(self.source_folder, "router_http_plugin.so")
        if not os.path.isfile(plugin):
            raise ConanException("router_http_plugin.so was not produced")
        if os.path.getsize(plugin) <= 1024:
            raise ConanException("router_http_plugin.so is unexpectedly small")

    def package(self):
        copy(
            self,
            "router_http_plugin.so",
            self.source_folder,
            os.path.join(self.package_folder, "lib", "uwsgi"),
        )
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "README",
            self.source_folder,
            os.path.join(self.package_folder, "share", "doc", "uwsgi-router_http"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.runenv_info.define_path(
            "UWSGI_ROUTER_HTTP_PLUGIN",
            os.path.join(self.package_folder, "lib", "uwsgi", "router_http_plugin.so"),
        )
