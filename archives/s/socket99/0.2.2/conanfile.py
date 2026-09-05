#!/usr/bin/env python3
"""Conan recipe for socket99 0.2.2.

socket99 is a small C99 BSD-socket wrapper distributed as a static archive.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
)
from conan.tools.layout import basic_layout


class Socket99Conan(ConanFile):
    name = "socket99"
    version = "0.2.2"
    description = "A C99 wrapper library for the BSD sockets API."
    license = "ISC"
    homepage = "https://github.com/silentbicycle/socket99"
    url = "https://github.com/silentbicycle/socket99"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "socket99 0.2.2 only provides the upstream static archive; "
                "use shared=False."
            )

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tool(self, key, fallback):
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return tools.get(key, fallback) if tools else fallback

    def _make_vars(self):
        return {
            "CC": self._tool("c", "clang"),
            "AR": self._tool("ar", "llvm-ar"),
            "RANLIB": self._tool("ranlib", "llvm-ranlib"),
        }

    def _build_flags(self):
        return (
            "-fPIC -std=c99 -g -Wall -Wextra -Wno-padded -pedantic "
            "-D_POSIX_C_SOURCE=200112L -D_C99_SOURCE -O3"
        )

    def _make_command(self, target):
        variables = self._make_vars()
        assignments = " ".join(
            f"{key}={shlex.quote(value)}" for key, value in variables.items()
        )
        flags = shlex.quote(self._build_flags())
        return f"make {assignments} CFLAGS={flags} -j1 {target}"

    def build(self):
        apply_conandata_patches(self)
        self.run(self._make_command("all"), cwd=self.source_folder)
        # Upstream's actual test entrypoint is make test (there is no make check).
        test_prefix = "SOCKET99_SKIP_UNIX=1 " if self.settings.os == "OHOS" else ""
        self.run(test_prefix + self._make_command("test"), cwd=self.source_folder)

    def package(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        include_dir = os.path.join(self.package_folder, "include")
        mkdir(self, lib_dir)
        mkdir(self, include_dir)
        copy(self, "libsocket99.a", src=self.build_folder, dst=lib_dir)
        copy(self, "socket99.h", src=self.source_folder, dst=include_dir)

    def package_info(self):
        self.cpp_info.libs = ["socket99"]
