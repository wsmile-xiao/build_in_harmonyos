#!/usr/bin/env python3
"""Conan recipe for iselect 1.4.2."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class IselectConan(ConanFile):
    name = "iselect"
    version = "1.4.2"
    description = "Interactive curses-based line selection tool"
    license = "GPL-2.0-only"
    homepage = "http://www.ossp.org/pkg/tool/iselect/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.6")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _compiler(self, key, fallback):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get(key, fallback)

    @staticmethod
    def _quote(value):
        return shlex.quote(str(value).replace("\\", "/"))

    @staticmethod
    def _embed_text(input_path, output_path, symbol):
        lines = input_path.read().splitlines()[1:]
        output = [
            '#include "iselect.h"',
            '#pragma GCC diagnostic ignored "-Wcast-qual"',
            f"const Line {symbol}[] = {{",
        ]
        for line in lines:
            escaped = line.replace("\\", "\\\\").replace('"', '\\"')
            output.append(
                f'{{.cpLine = (char *)"{escaped}", .nLine = sizeof("{escaped}") - 1}},'
            )
        output.append("{0} };")
        output_path.write("\n".join(output) + "\n")

    def _generate_sources(self):
        os.makedirs(self.build_folder, exist_ok=True)
        save(
            self,
            os.path.join(self.build_folder, "config.h"),
            '#define ISELECT_VERSION_STR "This is iSelect, Version 1.4.2 (2024-11-17)"\n',
        )

        source = _Path(self.source_folder)
        build = _Path(self.build_folder)
        readme = source.joinpath("iselect_readme.txt.in").read()
        readme = readme.replace("@ISELECT_VERSION_LONG@", "1.4.2 (2024-11-17)")
        build.joinpath("iselect_readme.txt").write(readme)

        manpage = source.joinpath("iselect.1.in").read()
        replacements = {
            "@ISELECT_VERSION_MDOC_DATE@": "November 17, 2024",
            "@ISELECT_VERSION_RAW@": "1.4.2",
            "@ISELECT_1_EXAMPLE_LOCATION@": ".Lk https://git.sr.ht/~nabijaczleweli/ossp-iselect/tree/trunk/item/example",
        }
        for key, value in replacements.items():
            manpage = manpage.replace(key, value)
        build.joinpath("iselect.1").write(manpage)

        self._embed_text(
            source.joinpath("iselect_help.txt"),
            build.joinpath("iselect_help.c"),
            "iSelect_Help",
        )
        self._embed_text(
            build.joinpath("iselect_readme.txt"),
            build.joinpath("iselect_readme.c"),
            "iSelect_README",
        )

    def _dep_flags(self, dep_name):
        dep = self.dependencies[dep_name].cpp_info
        includes = [f"-I{path}" for path in dep.includedirs]
        libdirs = [f"-L{path}" for path in dep.libdirs]
        libs = [f"-l{lib}" for lib in dep.libs]
        system_libs = [f"-l{lib}" for lib in dep.system_libs]
        return includes, libdirs, libs + system_libs

    def _has_reallocarray(self, cc, flags):
        probe = os.path.join(self.build_folder, "check_reallocarray.c")
        exe = os.path.join(self.build_folder, "check_reallocarray")
        save(
            self,
            probe,
            "\n".join(
                [
                    "#include <stdlib.h>",
                    "int main(void) {",
                    "    void *p = reallocarray(NULL, 1, 1);",
                    "    free(p);",
                    "    return 0;",
                    "}",
                    "",
                ]
            ),
        )
        cmd_flags = " ".join(
            self._quote(flag)
            for flag in flags + ["-Werror=implicit-function-declaration"]
        )
        return (
            self.run(
                f"{self._quote(cc)} {cmd_flags} {self._quote(probe)} -o {self._quote(exe)}",
                env="conanbuild",
                ignore_errors=True,
            )
            == 0
        )

    def build(self):
        self._generate_sources()
        cc = self._compiler("c", "clang")
        cxx = self._compiler("cpp", "clang++")
        includes, libdirs, libs = self._dep_flags("ncurses")
        common_flags = [
            "-D_GNU_SOURCE",
            "-D_XOPEN_SOURCE_EXTENDED",
            "-Wall",
            "-Wextra",
            "-Wno-switch",
            "-I" + self.source_folder,
            "-I" + self.build_folder,
        ] + includes

        if not self._has_reallocarray(cc, common_flags):
            common_flags.append("-DISELECT_NEED_REALLOCARRAY")

        c_objects = []
        c_sources = [
            os.path.join(self.source_folder, "iselect_main.c"),
            os.path.join(self.source_folder, "iselect_browse.c"),
            os.path.join(self.source_folder, "iselect_keys.c"),
            os.path.join(self.build_folder, "iselect_help.c"),
            os.path.join(self.build_folder, "iselect_readme.c"),
            os.path.join(self.source_folder, "dokey.c"),
        ]
        for source in c_sources:
            obj = os.path.join(self.build_folder, os.path.basename(source) + ".o")
            flags = " ".join(self._quote(flag) for flag in common_flags + ["-O2"])
            self.run(
                f"{self._quote(cc)} {flags} -c {self._quote(source)} -o {self._quote(obj)}",
                env="conanbuild",
            )
            c_objects.append(obj)

        enter_obj = os.path.join(self.build_folder, "enter.cpp.o")
        cxx_flags = " ".join(
            self._quote(flag) for flag in common_flags + ["-std=c++2b", "-O2"]
        )
        self.run(
            f"{self._quote(cxx)} {cxx_flags} -c "
            f"{self._quote(os.path.join(self.source_folder, 'enter.cpp'))} "
            f"-o {self._quote(enter_obj)}",
            env="conanbuild",
        )

        exe = os.path.join(self.build_folder, "iselect")
        objects = " ".join(self._quote(path) for path in c_objects + [enter_obj])
        ldflags = " ".join(self._quote(flag) for flag in libdirs + libs)
        self.run(
            f"{self._quote(cxx)} {objects} {ldflags} -o {self._quote(exe)}",
            env="conanbuild",
        )

    def package(self):
        copy(self, "*", os.path.join(self.source_folder, "LICENSES"), os.path.join(self.package_folder, "licenses"))
        copy(self, "README", self.source_folder, os.path.join(self.package_folder, "share", "iselect"), keep_path=False)
        copy(self, "iselect", self.build_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "iselect.1", self.build_folder, os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        exe = os.path.join(self.package_folder, "bin", "iselect")
        if os.path.isfile(exe) and os.name != "nt":
            os.chmod(exe, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))


class _Path(str):
    def joinpath(self, *parts):
        return _Path(os.path.join(self, *parts))

    def read(self):
        with open(self, "r", encoding="utf-8") as handle:
            return handle.read()

    def write(self, content):
        with open(self, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
