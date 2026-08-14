#!/usr/bin/env python3
"""Conan recipe for the uWSGI logzmq plugin 2.0.31."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class UwsgiLogzmqConan(ConanFile):
    name = "uwsgi-logzmq"
    version = "2.0.31"
    description = "uWSGI ZeroMQ logger plugin"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/unbit/uwsgi"
    url = "https://github.com/unbit/uwsgi"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        copy(self, "conandata.yml", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires("zeromq/4.3.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured = compilers.get("c")
        if configured and os.path.isfile(configured):
            return configured
        if configured:
            found = shutil.which(os.path.basename(configured))
            if found:
                return found
        return os.environ.get("CC") or shutil.which("clang") or "cc"

    def _dependency_flags(self, dependency_name):
        dep = self.dependencies[dependency_name]
        include_flags = []
        lib_flags = []
        for include_dir in dep.cpp_info.includedirs:
            include_flags.append("-I{}".format(include_dir))
        for lib_dir in dep.cpp_info.libdirs:
            lib_flags.append("-L{}".format(lib_dir))
        return include_flags, lib_flags

    def _write_profile(self):
        include_flags, _ = self._dependency_flags("zeromq")
        profile_path = os.path.join(
            self.source_folder, "buildconf", "logzmq_conan.ini"
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
pcre = false
routing = false
debug = false
plugins = logzmq
plugin_dir = .
embedded_plugins = null
as_shared_library = false
cflags = {cflags}
""".format(
                cflags=" ".join(include_flags),
            ),
        )
        return profile_path

    def build(self):
        _, lib_flags = self._dependency_flags("zeromq")
        self._write_profile()
        os.environ["CC"] = self._compiler()
        os.environ["CPUCOUNT"] = "1"
        os.environ["LDFLAGS"] = " ".join(
            lib_flags + os.environ.get("LDFLAGS", "").split()
        )
        os.environ.setdefault("UWSGI_FORCE_REBUILD", "1")
        self.run(
            "python3 uwsgiconfig.py --plugin plugins/logzmq logzmq_conan",
            cwd=self.source_folder,
        )

        plugin = os.path.join(self.source_folder, "logzmq_plugin.so")
        if not os.path.isfile(plugin):
            raise ConanException("logzmq_plugin.so was not produced")
        if os.path.getsize(plugin) <= 1024:
            raise ConanException("logzmq_plugin.so is unexpectedly small")

    def package(self):
        copy(
            self,
            "logzmq_plugin.so",
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
            os.path.join(self.package_folder, "share", "doc", "uwsgi-logzmq"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.runenv_info.define_path(
            "UWSGI_LOGZMQ_PLUGIN",
            os.path.join(self.package_folder, "lib", "uwsgi", "logzmq_plugin.so"),
        )
