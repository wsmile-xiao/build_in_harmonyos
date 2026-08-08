#!/usr/bin/env python3
"""Conan recipe for bgpq4 1.16."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class Bgpq4Conan(ConanFile):
    name = "bgpq4"
    version = "1.16"
    description = "BGP filtering automation tool"
    license = "BSD-2-Clause"
    homepage = "https://github.com/bgp/bgpq4"
    url = "https://github.com/bgp/bgpq4"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _get_cc(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get("c") or "clang"

    def _compiler_is_clang(self):
        return "clang" in str(self.settings.compiler).lower()

    def _write_config_h(self):
        config = """
#define PACKAGE_NAME "bgpq4"
#define PACKAGE_VERSION "1.16"
#define PACKAGE "bgpq4"
#define PACKAGE_STRING "bgpq4 1.16"
#define VERSION "1.16"
#define SPT_TYPE SPT_REUSEARGV
""".lstrip()
        save(self, os.path.join(self.source_folder, "config.h"), config)

    def build(self):
        self._write_config_h()
        cc = self._get_cc()
        os.makedirs(self.build_folder, exist_ok=True)

        cflags = [
            "-fPIE",
            "-Wall",
            "-Wstrict-prototypes",
            "-Wmissing-prototypes",
            "-Wmissing-declarations",
            "-Wshadow",
            "-Wpointer-arith",
            "-Wsign-compare",
            "-Werror=implicit-function-declaration",
            "-Wno-pointer-sign",
            "-D_DEFAULT_SOURCE",
            "-D_BSD_SOURCE",
            "-D_GNU_SOURCE",
            "-DHAVE_CONFIG_H=1",
            "-include",
            f'"{os.path.join(self.source_folder, "config.h")}"',
            f'-I"{self.source_folder}"',
            f'-I"{os.path.join(self.source_folder, "include")}"',
            f'-I"{os.path.join(self.source_folder, "compat")}"',
        ]
        build_type = str(self.settings.build_type)
        if build_type == "Debug":
            cflags.extend(["-O0", "-g"])
        elif build_type == "RelWithDebInfo":
            cflags.extend(["-O2", "-g", "-DNDEBUG"])
        elif build_type == "MinSizeRel":
            cflags.extend(["-Os", "-DNDEBUG"])
        else:
            cflags.extend(["-O2", "-DNDEBUG"])
        if self._compiler_is_clang():
            cflags.append("-Qunused-arguments")

        sources = [
            "main.c",
            "printer.c",
            "expander.c",
            "sx_prefix.c",
            "sx_report.c",
            "sx_slentry.c",
            os.path.join("compat", "strlcpy.c"),
        ]
        srcs = " ".join(f'"{os.path.join(self.source_folder, source)}"' for source in sources)
        output = os.path.join(self.build_folder, "bgpq4")
        self.run(f'"{cc}" {" ".join(cflags)} {srcs} -o "{output}" -pie -Wl,-z,relro,-z,now', cwd=self.source_folder)

        if can_run(self):
            self.run(f'"{output}" -v')

    def package(self):
        copy(self, "bgpq4", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "bgpq4.8", self.source_folder, os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "COPYRIGHT", self.source_folder, os.path.join(self.package_folder, "licenses"))
        binary = os.path.join(self.package_folder, "bin", "bgpq4")
        if os.path.exists(binary):
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
