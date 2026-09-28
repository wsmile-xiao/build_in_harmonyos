#!/usr/bin/env python3
"""Conan recipe for the libcdio 2.3.0 command-line tools.

The package intentionally depends on libcdio/2.3.0 and exports only the
installed tools. It does not export or duplicate the libcdio libraries.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibcdioToolsConan(ConanFile):
    name = "libcdio-tools"
    version = "2.3.0"
    description = "Command-line tools for CD-ROM and ISO-9660/UDF access from libcdio"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/libcdio/"
    url = "https://github.com/libcdio/libcdio"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _TOOLS = ("cd-drive", "cd-info", "cd-read", "iso-info", "iso-read", "mmc-tool")
    _SOURCES = {
        "cd-drive": ("cd-drive.c", "util.c", "getopt.c", "getopt1.c"),
        "cd-info": ("cd-info.c", "cddb.c", "util.c", "getopt.c", "getopt1.c"),
        "cd-read": ("cd-read.c", "util.c", "getopt.c", "getopt1.c"),
        "iso-info": ("iso-info.c", "util.c", "getopt.c", "getopt1.c"),
        "iso-read": ("iso-read.c", "util.c", "getopt.c", "getopt1.c"),
        "mmc-tool": ("mmc-tool.c", "util.c", "getopt.c", "getopt1.c"),
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libcdio/2.3.0")

    def configure(self):
        # The command-line tools are shipped as self-contained executables.
        self.options["libcdio"].shared = False

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration(
                "libcdio-tools is validated on OpenHarmony and Linux"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-shared",
                "--enable-static",
                "--disable-cxx",
                "--disable-nls",
                "--disable-example-progs",
                "--without-cdda-player",
                "--disable-cddb",
                "--disable-vcd-info",
            ]
        )
        if self.settings.os == "OHOS":
            # Direct clang links need no libtool compatibility flags.
            tc.extra_ldflags.append("-static")
        tc.generate()

    def _absolute_dirs(self, dependency, dirs):
        return [
            path if os.path.isabs(path) else os.path.join(dependency.package_folder, path)
            for path in dirs
        ]

    def _compile_tools(self):
        dependency = self.dependencies["libcdio"]
        cpp_info = dependency.cpp_info
        include_dirs = self._absolute_dirs(dependency, cpp_info.includedirs or ["include"])
        library_dirs = self._absolute_dirs(dependency, cpp_info.libdirs or ["lib"])

        library_names = list(cpp_info.libs)
        if not library_names:
            raise ConanException("libcdio/2.3.0 did not expose any library names")

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        cflags = list(self.conf.get("tools.build:cflags", default=[], check_type=list))
        exe_linkflags = list(
            self.conf.get("tools.build:exelinkflags", default=[], check_type=list)
        )

        cflags.extend(["-DHAVE_CONFIG_H", "-D_FILE_OFFSET_BITS=64"])
        cflags.extend("-I" + path for path in include_dirs)
        cflags.append("-I" + self.build_folder)
        # The CLI sources need config.h and upstream-private driver headers.
        cflags.append("-I" + os.path.join(self.source_folder, "lib", "driver"))

        link_flags = list(exe_linkflags)
        link_flags.extend("-L" + path for path in library_dirs)
        if self.settings.os == "OHOS":
            link_flags.append("-static")

        link_libraries = ["-l" + library for library in library_names]
        link_libraries.extend("-l" + library for library in cpp_info.system_libs)
        for framework in cpp_info.frameworks:
            link_libraries.extend(["-framework", framework])

        src_dir = os.path.join(self.source_folder, "src")
        for tool in self._TOOLS:
            command = [cc]
            command.extend(cflags)
            command.extend(["-O2", "-o", os.path.join(self.build_folder, tool)])
            command.extend(os.path.join(src_dir, source) for source in self._SOURCES[tool])
            command.extend(link_flags)
            command.extend(link_libraries)
            self.output.info("Building %s against libcdio/2.3.0" % tool)
            subprocess.run(command, cwd=self.build_folder, check=True)

    def build(self):
        apply_conandata_patches(self)

        # configure only creates config.h and the platform feature definitions.
        # The binaries are compiled directly against the installed libcdio
        # dependency; no in-tree libcdio library is built or packaged.
        autotools = Autotools(self)
        autotools.configure()
        self._compile_tools()

    def package(self):
        for tool in self._TOOLS:
            copy(
                self,
                tool,
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "bin"),
            )
            os.chmod(os.path.join(self.package_folder, "bin", tool), 0o755)

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._sign_executables()

    def _sign_executables(self):
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(sign_tool) and os.path.isfile(objcopy)):
            self.output.info("HarmonyOS signing tools not present; skipping ELF signing")
            return

        for tool in self._TOOLS:
            path = os.path.join(self.package_folder, "bin", tool)
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path],
                check=False,
                capture_output=True,
            )
            signed = path + ".signed"
            last_error = None
            for _ in range(3):
                result = subprocess.run(
                    [
                        sign_tool,
                        "sign",
                        "-inFile",
                        path,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ],
                    capture_output=True,
                    timeout=30,
                )
                if result.returncode == 0 and os.path.isfile(signed):
                    os.replace(signed, path)
                    os.chmod(path, 0o755)
                    break
                last_error = result.stderr.decode("utf-8", "replace")
            else:
                raise ConanException(
                    "ELF signing failed for %s: %s" % (tool, last_error)
                )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
