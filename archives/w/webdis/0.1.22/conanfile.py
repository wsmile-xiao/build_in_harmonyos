#!/usr/bin/env python3
"""Conan recipe — webdis 0.1.22 (HTTP interface to Redis).

webdis exposes a Redis instance over HTTP: every request path is a Redis
command (`/SET/key/value`, `/GET/key`, ...) and the reply is rendered as JSON,
raw text, MessagePack or a custom format.  It can also upgrade a request to a
WebSocket, where the same commands are sent as frames.

Build system: plain upstream Makefile (`make` -> `webdis`, no configure step).
The 0.1.22 tarball vendors its client-side dependencies under src/ (hiredis,
jansson, http-parser, b64, md5, sha1), so the only external dependency is
libevent.  `webdis` is a command-line tool, hence package_type=application.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class WebdisConan(ConanFile):
    name = "webdis"
    version = "0.1.22"
    description = ("Webdis — HTTP/WebSocket interface to Redis (JSON, raw, "
                   "MessagePack and custom output formats)")
    license = "BSD-2-Clause"
    homepage = "https://webdis.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"webdis only supports Linux/OHOS builds, got {self.settings.os}"
            )

    def requirements(self):
        # Only external link-time dependency of webdis 0.1.22.
        self.requires("libevent/2.1.13")
        # MessagePack output format (/GET/key.msg).  Upstream treats it as
        # optional and auto-detects it through /usr/lib/libmsgpack*.so, which
        # does not exist on OHOS; upstream's own CI installs libmsgpack-dev, so
        # this recipe wires msgpack-c in explicitly to keep the same feature set
        # (and the same 25 upstream python tests) available.
        self.requires("msgpack-c/7.0.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dependency_cflags(self):
        flags = []
        for name in ("libevent", "msgpack-c"):
            info = self.dependencies[name].cpp_info.aggregated_components()
            flags.extend(f"-I{path}" for path in info.includedirs)
        return " ".join(flags)

    def _dependency_ldflags(self):
        flags = []
        for name in ("libevent", "msgpack-c"):
            info = self.dependencies[name].cpp_info.aggregated_components()
            flags.extend(f"-L{path}" for path in info.libdirs)
            flags.extend(f"-l{lib}" for lib in info.libs)
            flags.extend(f"-l{lib}" for lib in info.system_libs)
        return " ".join(flags)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler and flags come from the Conan toolchain, never from the
        # shell environment (${CC}/${CFLAGS} are empty on release workers).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        toolchain_cflags = self.conf.get(
            "tools.build:cflags", default=[], check_type=list
        ) or []

        # The upstream Makefile initialises CFLAGS with `CFLAGS ?=`, which never
        # fires when the build environment already exports CFLAGS — the
        # default include paths would then be lost and the build would stop at
        # `'hiredis/async.h' file not found`.  The upstream defaults are
        # therefore repeated here verbatim.
        upstream_cflags = (
            "-std=c99 -Wall -Wextra -Isrc -Isrc/jansson/src -Isrc/http-parser "
            "-D_POSIX_C_SOURCE=200809L -Wno-pragmas -fPIC"
        )
        cflags = " ".join(
            flag
            for flag in (
                upstream_cflags,
                # Upstream enables the optional MessagePack format with
                # `CFLAGS += -DMSGPACK=1` in its own auto-detection branch;
                # messagepack support is wired in unconditionally here (see
                # requirements(): upstream CI also builds with libmsgpack-dev).
                "-DMSGPACK=1",
                " ".join(toolchain_cflags),
                self._dependency_cflags(),
            )
            if flag
        )
        ldflags = f"{self._dependency_ldflags()} -pthread"

        # The Makefile appends src/formats/msgpack.o only in its own
        # /usr/lib/libmsgpack*.so auto-detection branch, so the object list is
        # passed explicitly (same objects as upstream, plus msgpack.o).
        format_objs = (
            "src/formats/json.o src/formats/raw.o src/formats/common.o "
            "src/formats/custom-type.o src/formats/msgpack.o"
        )

        # R9: build serially (-j1) for reproducibility on the build workers.
        self.run(
            f'make CC="{cc}" CFLAGS="{cflags}" LDFLAGS="{ldflags}" '
            f'FORMAT_OBJS="{format_objs}" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        # `webdis` links libevent shared, so no RPATH is embedded (absolute
        # build paths must not leak into the binary); LD_LIBRARY_PATH comes from
        # the Conan run environment.
        copy(self, "webdis", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        for config_file in ("webdis.json", "webdis.prod.json"):
            copy(self, config_file, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "webdis"))

    def package_info(self):
        # CLI application: only bin/ is populated.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
