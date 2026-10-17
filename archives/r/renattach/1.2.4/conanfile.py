#!/usr/bin/env python3
"""Conan recipe for renattach 1.2.4."""

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RenattachConan(ConanFile):
    name = "renattach"
    version = "1.2.4"
    description = "Rename or delete potentially dangerous email attachments"
    license = "GPL-2.0-or-later"
    homepage = "https://www.pc-tools.net/unix/renattach/"
    url = "https://www.pc-tools.net/unix/renattach/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"renattach supports Linux and OHOS, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            config_h = os.path.join(self.source_folder, "config.h")
            with open(config_h, "w", encoding="utf-8") as cfg:
                cfg.write(
                    "\n".join(
                        [
                            '#define PACKAGE "renattach"',
                            '#define PACKAGE_BUGREPORT ""',
                            '#define PACKAGE_NAME "renattach"',
                            '#define PACKAGE_STRING "renattach 1.2.4"',
                            '#define PACKAGE_TARNAME "renattach"',
                            '#define PACKAGE_VERSION "1.2.4"',
                            '#define VERSION "1.2.4"',
                            "#define STDC_HEADERS 1",
                            "#define HAVE_EXECV 1",
                            "#define HAVE_FORK 1",
                            "#define HAVE_FTRUNCATE 1",
                            "#define HAVE_GETOPT_H 1",
                            "#define HAVE_GETOPT_LONG 1",
                            "#define HAVE_INTTYPES_H 1",
                            "#define HAVE_MALLOC 1",
                            "#define HAVE_MEMORY_H 1",
                            "#define HAVE_MEMSET 1",
                            "#define HAVE_PIPE 1",
                            "#define HAVE_SIGNAL_H 1",
                            "#define HAVE_STDINT_H 1",
                            "#define HAVE_STDLIB_H 1",
                            "#define HAVE_STRCASECMP 1",
                            "#define HAVE_STRCHR 1",
                            "#define HAVE_STRINGS_H 1",
                            "#define HAVE_STRING_H 1",
                            "#define HAVE_STRNCASECMP 1",
                            "#define HAVE_STRRCHR 1",
                            "#define HAVE_STRSTR 1",
                            "#define HAVE_SYSLOG_H 1",
                            "#define HAVE_SYS_STAT_H 1",
                            "#define HAVE_SYS_TYPES_H 1",
                            "#define HAVE_UNISTD_H 1",
                            "",
                        ]
                    )
                )
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            cc = executables.get("c", "cc")
            build_type = str(self.settings.build_type)
            build_flags = {
                "Debug": "-g -O0",
                "Release": "-O3 -DNDEBUG",
                "RelWithDebInfo": "-O2 -g -DNDEBUG",
                "MinSizeRel": "-Os -DNDEBUG",
            }.get(build_type)
            if build_flags is None:
                raise ConanInvalidConfiguration(
                    f"Unsupported build_type for renattach on OHOS: {build_type}"
                )
            with chdir(self, self.source_folder):
                self.run(
                    f'"{cc}" {build_flags} -I. -Isrc '
                    '-DCONF_DIR=\\"/etc\\" '
                    "-o src/renattach "
                    "src/renattach.c src/settings.c src/utility.c"
                )
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
            # Upstream defines an Automake check target but ships no test programs.
            autotools.make(target="check", args=["-j1"])

    def package(self):
        if str(self.settings.os) == "OHOS":
            copy(
                self,
                "renattach",
                src=os.path.join(self.source_folder, "src"),
                dst=os.path.join(self.package_folder, "bin"),
                keep_path=False,
            )
            copy(
                self,
                "renattach.conf.ex",
                src=os.path.join(self.source_folder, "conf"),
                dst=os.path.join(self.package_folder, "etc"),
                keep_path=False,
            )
            copy(
                self,
                "renattach.1",
                src=os.path.join(self.source_folder, "src"),
                dst=os.path.join(self.package_folder, "share", "man", "man1"),
                keep_path=False,
            )
        else:
            autotools = Autotools(self)
            autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        binary = os.path.join(self.package_folder, "bin", "renattach")
        if str(self.settings.os) == "OHOS":
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            sign_tool = executables.get(
                "sign_tool", "/data/service/hnp/bin/binary-sign-tool"
            )
            objcopy = executables.get(
                "objcopy", "/data/service/hnp/bin/llvm-objcopy"
            )
            if not os.path.isfile(sign_tool):
                raise ConanInvalidConfiguration(
                    f"HarmonyOS binary signing tool not found: {sign_tool}"
                )
            if not os.path.isfile(objcopy):
                raise ConanInvalidConfiguration(
                    f"HarmonyOS objcopy tool not found: {objcopy}"
                )
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", binary],
                check=True,
            )
            signed = binary + ".signed"
            subprocess.run(
                [
                    sign_tool,
                    "sign",
                    "-inFile",
                    binary,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            os.replace(signed, binary)

        if os.path.isfile(binary):
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
