#!/usr/bin/env python3
"""Conan recipe for cronutils 1.1."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get, replace_in_file
from conan.tools.layout import basic_layout


class CronutilsConan(ConanFile):
    name = "cronutils"
    version = "1.1"
    description = "Utilities for limiting, timing, and recording batch jobs"
    license = "Apache-2.0"
    homepage = "http://code.google.com/p/cronutils"
    url = "https://snapshot.debian.org/package/cronutils/1.1-3/"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "LICENSE"

    _source_url = (
        "https://snapshot.debian.org/archive/debian/20110723T212944Z/"
        "pool/main/c/cronutils/cronutils_1.1.orig.tar.gz"
    )
    _source_sha256 = (
        "28a5bbba67a1977be553aacc0b4087b61fef83857f8d7703b9bb823c07454035"
    )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cronutils requires a POSIX target (Linux or OHOS)"
            )

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        # Keep the source URL in the recipe so CI does not enter the
        # conandata.yml pre-download path with its known BUILD_DIR issue.
        get(
            self,
            url=self._source_url,
            sha256=self._source_sha256,
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)

        # The Debian 1.1-3 portability fix makes HOST_NAME_MAX optional.
        runstat = os.path.join(self.source_folder, "runstat.c")
        fallback = (
            '#include "tempdir.h"\n\n'
            "/* HOST_NAME_MAX is absent from some POSIX header sets. */\n"
            "#if !defined(HOST_NAME_MAX) && defined(_POSIX_HOST_NAME_MAX)\n"
            "#define HOST_NAME_MAX _POSIX_HOST_NAME_MAX\n"
            "#endif\n"
        )
        replace_in_file(
            self,
            runstat,
            '#include "tempdir.h"\n',
            fallback,
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "runlock.c"),
            "  int status;\n",
            "  int status = EX_OSERR;\n",
        )

        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc = compilers.get("c", "clang")

        # The upstream Makefile has three small direct compiler targets. Keep
        # the same target/source mapping without requiring host make.
        cflags = "-O2 -Wall -Wextra -D_XOPEN_SOURCE=700"
        ldflags = ""
        if self.settings.os == "OHOS":
            # Use the worker linker by default, with a local SDK override for
            # Windows-hosted DevEco cross builds.
            ld_path = self.conf.get(
                "user.ohos:ld_path",
                default="",
                check_type=str,
            )
            ld_path = ld_path or os.environ.get("OHOS_LD", "")
            if ld_path:
                ldflags = f'-fuse-ld="{ld_path}"'
            else:
                ldflags = "-fuse-ld=/data/service/hnp/bin/ld"
            ldlibs = ""
        else:
            ldlibs = "-lrt"

        common = f'{cflags} {ldflags}'.strip()
        targets = {
            "runalarm": ("runalarm.c", "subprocess.c"),
            "runlock": ("runlock.c", "subprocess.c", "tempdir.c"),
            "runstat": ("runstat.c", "subprocess.c", "tempdir.c"),
        }
        for target, sources in targets.items():
            source_files = " ".join(
                f'"{os.path.join(self.source_folder, source)}"'
                for source in sources
            )
            output = os.path.join(self.build_folder, target)
            self.run(
                f'"{cc}" {common} -o "{output}" {source_files} {ldlibs}',
                cwd=self.source_folder,
            )

    def package(self):
        # Mirror the upstream install layout without requiring host make.
        copy(
            self,
            "runalarm",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "runlock",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "runstat",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "*.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.export_sources_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        for name in ("runalarm", "runlock", "runstat"):
            path = os.path.join(self.package_folder, "bin", name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
                self._sign_ohos_binary(path)

    def _sign_ohos_binary(self, path):
        if str(self.settings.os) != "OHOS":
            return

        signer = self.conf.get(
            "user.ohos:sign_tool",
            default="",
            check_type=str,
        )
        signer = (
            signer
            or os.environ.get("OHOS_SIGN_TOOL", "")
            or shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool is unavailable; skipping OHOS ELF signing"
            )
            return

        objcopy = self.conf.get(
            "user.ohos:objcopy",
            default="",
            check_type=str,
        )
        objcopy = (
            objcopy
            or os.environ.get("OHOS_OBJCOPY", "")
            or shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        if os.path.isfile(objcopy):
            self.run(
                f'"{objcopy}" --remove-section .codesign "{path}"',
                ignore_errors=True,
            )

        signed = f"{path}.signed"
        self.run(
            f'"{signer}" sign -inFile "{path}" '
            f'-outFile "{signed}" -selfSign 1'
        )
        if not os.path.isfile(signed):
            raise ConanException(f"binary-sign-tool produced no output for {path}")
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
