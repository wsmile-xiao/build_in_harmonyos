#!/usr/bin/env python3
"""Conan recipe for YACPI 3.0.1, an ACPI/CPU monitor for terminals."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class YacpiConan(ConanFile):
    name = "yacpi"
    version = "3.0.1"
    description = "Yet Another Configuration and Power Interface monitor"
    license = "GPL-2.0-or-later"
    homepage = "http://www.ngolde.de/yacpi.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires("libacpi/0.2")
        self.requires("ncurses/6.5")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"yacpi supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dependency_flags(self):
        include_dirs = []
        library_dirs = []
        libraries = []

        # YACPI uses only the wide-character curses library plus libacpi.
        for name, selected_libs in (
            ("ncurses", ("ncursesw",)),
            ("libacpi", ("acpi",)),
        ):
            dependency = self.dependencies[name]
            info = dependency.cpp_info
            include_dirs.extend(
                os.path.join(dependency.package_folder, path)
                for path in (info.includedirs or [])
            )
            library_dirs.extend(
                os.path.join(dependency.package_folder, path)
                for path in (info.libdirs or [])
            )
            available = list(info.libs or [])
            libraries.extend(
                selected_libs
                if all(library in available for library in selected_libs)
                else available
            )

        cppflags = " ".join(f"-I{shlex.quote(path)}" for path in include_dirs)
        ldflags = " ".join(f"-L{shlex.quote(path)}" for path in library_dirs)
        ldlibs = " ".join(f"-l{library}" for library in libraries)
        return cppflags, ldflags, ldlibs

    def build(self):
        apply_conandata_patches(self)

        # The upstream Makefile hardcodes the compiler/link line and strip.
        # Route these through standard make variables so Conan can supply the
        # target compiler and dependency paths without relying on shell CC/CFLAGS.
        makefile = os.path.join(self.source_folder, "Makefile")
        with open(makefile, "r", encoding="utf-8") as source:
            contents = source.read()
        replacements = (
            (
                "@${CC} -c ${CFLAGS} $<",
                "@${CC} ${CPPFLAGS} -c ${CFLAGS} $<",
            ),
            (
                "@${CC} -Wall get_cpu.o yacpi.o -o ${BIN} -lncurses -lacpi",
                "@${CC} ${LDFLAGS} -Wall get_cpu.o yacpi.o -o ${BIN} ${LDLIBS}",
            ),
            ("@strip ${BIN}", "@${STRIP} ${BIN}"),
        )
        for old, new in replacements:
            if contents.count(old) != 1:
                raise ConanInvalidConfiguration(
                    f"unexpected upstream Makefile; cannot adapt line: {old}"
                )
            contents = contents.replace(old, new, 1)
        with open(makefile, "w", encoding="utf-8", newline="\n") as target:
            target.write(contents)

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c", "clang")
        strip = executables.get("strip", "strip")
        cppflags, ldflags, ldlibs = self._dependency_flags()
        cflags = f'-O2 -Wall -DVERSION=\\"{self.version}\\"'
        arguments = (
            f"CC={shlex.quote(cc)} "
            f"STRIP={shlex.quote(strip)} "
            f"CPPFLAGS={shlex.quote(cppflags)} "
            f"CFLAGS={shlex.quote(cflags)} "
            f"LDFLAGS={shlex.quote(ldflags)} "
            f"LDLIBS={shlex.quote(ldlibs)}"
        )
        self.run(f"make {arguments} -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        executable = os.path.join(self.source_folder, "yacpi")
        packaged_executable = os.path.join(bindir, "yacpi")
        if self.settings.os == "OHOS":
            # A normal copy loses HarmonyOS MAC labels in the Conan package
            # cache, so mirror the built binary with cat as established by
            # other OHOS application recipes in this repository.
            self.run(f'cat "{executable}" > "{packaged_executable}" && chmod 755 "{packaged_executable}"')
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            self.run(
                f'"{objcopy}" --remove-section .codesign "{packaged_executable}" 2>/dev/null || true',
                quiet=True,
            )
            signed_executable = packaged_executable + ".signed"
            self.run(
                f'"{sign_tool}" sign -inFile "{packaged_executable}" '
                f'-outFile "{signed_executable}" -selfSign 1',
                quiet=True,
            )
            os.replace(signed_executable, packaged_executable)
            os.chmod(packaged_executable, 0o755)
        else:
            copy(self, "yacpi", src=self.source_folder, dst=bindir, keep_path=False)
        copy(
            self,
            "yacpi.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        for pattern in ("README", "CHANGELOG", "THANKS"):
            copy(
                self,
                pattern,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "share", "doc", "yacpi"),
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
