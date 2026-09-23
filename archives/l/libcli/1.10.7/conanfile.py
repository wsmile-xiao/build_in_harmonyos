#!/usr/bin/env python3
"""Conan recipe — libcli 1.10.7 (raw Makefile, no configure script)."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.layout import basic_layout


class LibcliConan(ConanFile):
    name = "libcli"
    version = "1.10.7"
    description = "Cisco-like command-line interface shared library"
    license = "LGPL-2.1-only"
    homepage = "https://github.com/dparrish/libcli"
    url = "https://github.com/dparrish/libcli"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def _is_usable_executable(self, path):
        # Absolute paths must exist and be executable (preflight toolchain
        # may move: profile conf can point at a stale
        # /data/service/hnp/bin/clang that no longer exists -> make then
        # fails with "No such file or directory"). Bare names resolve via
        # PATH (HMBS prepends real tool dirs), so accept them.
        if not path:
            return False
        path = str(path)
        if not os.path.isabs(path):
            return True
        return os.path.isfile(path) and os.access(path, os.X_OK)

    def _resolve_tool(self, key, fallbacks):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cand = compilers.get(key)
        if self._is_usable_executable(cand):
            # Conf value usable: prefer it (R33: from Conan conf).
            # Bare names fall through to PATH resolution below.
            if os.path.isabs(str(cand)):
                return str(cand)
        for name in fallbacks:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        # Known OHOS absolute locations (profile PATH order) before giving up.
        for abs_path in ("/data/service/hnp/bin/clang",
                         "/data/service/hnp/bin/llvm-ar",
                         "/data/service/hnp/bin/ar",
                         "/storage/Users/currentUser/usr/local/bin/clang"):
            if fallbacks and os.path.basename(abs_path) in fallbacks:
                if self._is_usable_executable(abs_path):
                    return abs_path
        if self._is_usable_executable(cand):
            return str(cand)
        return fallbacks[0]

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Modern clang (-std=c99 -Werror -Wstrict-prototypes in the upstream
        # Makefile) rejects the K&R-style definition `cli_init()` in libcli.c
        # (libcli.h already declares it as `(void)`). A unified-diff patch
        # proved line-number fragile against the tag tarball, so fix it here
        # with an exact-string replacement instead: no hunk context to drift.
        replace_in_file(self, os.path.join(self.source_folder, "libcli.c"),
                        "struct cli_def *cli_init() {",
                        "struct cli_def *cli_init(void) {")
        # R33: compiler paths come from Conan conf, never from shell env vars
        # (release workers leave $CC/$CFLAGS empty). Conf values are only
        # used when the absolute path actually exists; stale profile paths
        # (e.g. /data/service/hnp/bin/clang missing on preflight) fall back
        # to PATH lookup (HMBS prepends real tool dirs).
        cc = self._resolve_tool("c", ["clang", "cc"])
        if not cc:
            raise ConanInvalidConfiguration("A C compiler is required to build libcli")
        ar = self._resolve_tool("ar", ["llvm-ar", "ar"])
        if not ar:
            raise ConanInvalidConfiguration("An archiver (llvm-ar or ar) is required to build libcli")
        self.output.info("libcli CC={} AR={}".format(cc, ar))
        args = [
            "CC={}".format(cc),
            "AR={}".format(ar),
            "DYNAMIC_LIB={}".format("1" if self.options.shared else "0"),
            "STATIC_LIB={}".format("0" if self.options.shared else "1"),
            # TESTS=0 skips the clitest demo server (interactive telnet
            # example using fork(), same as the OpenWrt package build).
            "TESTS=0",
            # The Makefile hardcodes LIBS=-lcrypt on non-Darwin. OHOS uses
            # musl libc, which provides its own simplified crypt() in libc
            # itself, and no standalone libcrypt exists on the device, so
            # clear LIBS instead of linking it.
            "LIBS=",
            # R9: always single-job make on OHOS workers.
            "-j1",
        ]
        self.run("make {}".format(" ".join(args)), cwd=self.source_folder)

    def package(self):
        # Copy artifacts directly instead of `make install` so the layout is
        # deterministic regardless of the device's install(1) behavior.
        copy(self, "libcli.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "libcli.so.1.10.7", self.source_folder, libdir)
            # Recreate the version-symlink aliases as real file copies: the
            # OHOS worker filesystem may not support symlinks, and consumers
            # only need libcli.so for -lcli plus the SONAME file at runtime.
            for alias in ("libcli.so.1.10", "libcli.so"):
                shutil.copy2(
                    os.path.join(libdir, "libcli.so.1.10.7"),
                    os.path.join(libdir, alias),
                )
        else:
            copy(self, "libcli.a", self.source_folder, libdir)

    def package_info(self):
        # The artifact is libcli.so / libcli.a, linked as -lcli.
        self.cpp_info.libs = ["cli"]
        self.cpp_info.set_property("cmake_file_name", "libcli")
        self.cpp_info.set_property("cmake_target_name", "libcli::libcli")
