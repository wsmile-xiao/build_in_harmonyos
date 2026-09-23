#!/usr/bin/env python3
"""Conan recipe — libarc 2.0.2 (tiny C decompression library, plain Makefile).

libarc by Masanao Izumo extracts data compressed with tar / tar.gz /
zip (implode, deflate) / lzh (lh0-lh7, lzs, lz5, lz4) / MIME multipart.
Upstream ships a handwritten Makefile (no configure, no CMake) that
hard-codes ``CC = gcc`` / ``AR = ar -cr`` / ``PREFIX = /usr/local`` and
builds a static ``libarc.a`` by default (``arccat`` is an opt-in extra
target, not part of ``all``). Rather than patching the Makefile, this
recipe compiles the 29 real upstream C sources directly with the
OpenHarmony toolchain (compiler/ar taken from Conan conf, never from
shell env per R33) and archives them into ``libarc.a`` with ``-fPIC``.

No upstream source file is modified and no patch is applied.
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Glob for the real OHOS SDK toolchain dir (version-agnostic: the SDK
# version suffix changes, e.g. ohos-sdk_26.0.0.18). /data/service/hnp/bin
# entries are symlinks into one of these dirs (drogon precedent); when
# the link target is not mounted in the build sandbox, execve fails with
# "/bin/sh: ...: inaccessible or not found", so every candidate below is
# verified executable before use.
_SDK_LLVM_BIN_GLOB = "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin"


def _first_executable(candidates):
    for candidate in candidates:
        if (candidate and os.path.isfile(candidate)
                and os.access(candidate, os.X_OK)):
            return candidate
    return None


def _resolve_tool(conf_value, tool, kind):
    """Verify-first tool resolution (R33: conf stays the primary source).

    Order: explicit conf value (only if it exists and is executable) ->
    environment override -> PATH lookup -> well-known HNP/SDK locations.
    Raises with the conf value and PATH in the message instead of letting
    /bin/sh fail with "inaccessible or not found".
    """
    if kind == "cc":
        candidates = (
            [conf_value, os.environ.get("CC"),
             shutil.which("clang"), shutil.which("cc")]
            + sorted(glob.glob(os.path.join(_SDK_LLVM_BIN_GLOB, tool)))
            + ["/data/service/hnp/bin/%s" % tool]
        )
    else:
        candidates = (
            [conf_value, os.environ.get("AR"),
             shutil.which("llvm-ar"), shutil.which("ar")]
            + sorted(glob.glob(os.path.join(_SDK_LLVM_BIN_GLOB, tool)))
            + ["/data/service/hnp/bin/%s" % tool]
        )
    found = _first_executable(candidates)
    if found is not None:
        return found
    raise ConanInvalidConfiguration(
        "libarc: no executable %s found (conf=%r, tried=%r, PATH=%r)"
        % (tool, conf_value, [c for c in candidates if c],
           os.environ.get("PATH"))
    )


# Exact object list of the upstream Makefile ``OBJS`` (``arccat.o`` and
# ``readdir_win.o`` excluded: arccat is an opt-in sample tool, not part
# of upstream ``all``; readdir_win is Windows-only).
_LIBARC_SOURCES = [
    "inflate.c",
    "url.c",
    "url_file.c",
    "url_inflate.c",
    "net.c",
    "url_buff.c",
    "url_ftp.c",
    "url_mem.c",
    "url_dir.c",
    "url_http.c",
    "url_pipe.c",
    "arc.c",
    "arc_lzh.c",
    "arc_tar.c",
    "arc_zip.c",
    "deflate.c",
    "unlzh.c",
    "memb.c",
    "strtab.c",
    "mblock.c",
    "explode.c",
    "url_uudecode.c",
    "url_b64decode.c",
    "url_cache.c",
    "url_hqxdecode.c",
    "url_qsdecode.c",
    "url_news.c",
    "url_newsgroup.c",
    "url_cgiesc.c",
    "arc_mime.c",
]


class LibarcConan(ConanFile):
    name = "libarc"
    version = "2.0.2"
    package_type = "library"
    description = "Tiny C library to extract tar/tar.gz/zip/lzh/MIME archives"
    license = "GPL-2.0-or-later"
    homepage = "http://www.onicos.com/staff/iz/release/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"
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

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libarc is supported only on Linux/OHOS, not %s"
                % self.settings.os
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "OHOS builds require armv8/aarch64"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R33: read the OpenHarmony toolchain from Conan conf, never
        # from shell env (release workers leave CC/AR empty). The conf
        # path wins only when it is actually executable: /data/service/
        # hnp/bin entries are symlinks into the SDK dir and may dangle
        # in sandboxed workers (preflight: "/bin/sh: .../clang:
        # inaccessible or not found"), so fall back through env, PATH
        # and the version-agnostic SDK glob instead of failing at exec.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = _resolve_tool(compilers.get("c", "clang"), "clang", "cc")
        ar = _resolve_tool(
            compilers.get("ar") or "llvm-ar", "llvm-ar", "ar")
        self.output.info("libarc: using CC=%s AR=%s" % (cc, ar))

        cflags = ["-O2", "-I" + self.source_folder, "-Wall"]
        if self.options.get_safe("fPIC", True):
            cflags.append("-fPIC")
        # Year-2000 K&R-era C: clang 15 promotes implicit declarations
        # to hard errors; demote to warnings (cyrus-sasl precedent).
        cflags.append("-Wno-error=implicit-function-declaration")
        cflags.append("-Wno-error=implicit-int")
        cflags.append("-Wno-error=int-conversion")

        objects = []
        for src in _LIBARC_SOURCES:
            obj = os.path.join(self.build_folder, src.replace(".c", ".o"))
            self.run(
                '"%s" %s -c "%s" -o "%s"'
                % (cc, " ".join(cflags),
                   os.path.join(self.source_folder, src), obj),
                env="conanbuild",
            )
            objects.append('"%s"' % obj)

        self.run(
            '"%s" rcs "%s" %s'
            % (ar, os.path.join(self.build_folder, "libarc.a"),
               " ".join(objects)),
            env="conanbuild",
        )

    def package(self):
        copy(self, "libarc.a", self.build_folder,
             os.path.join(self.package_folder, "lib"))
        # Public headers: exactly the four files the upstream
        # ``install`` target ships (unlzh.h/zip.h stay private).
        for header in ("url.h", "arc.h", "mblock.h", "memb.h"):
            copy(self, header, os.path.join(self.source_folder, "libarc"),
                 os.path.join(self.package_folder, "include", "libarc"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["arc"]
        self.cpp_info.includedirs = ["include"]
