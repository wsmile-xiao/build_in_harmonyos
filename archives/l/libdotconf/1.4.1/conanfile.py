#!/usr/bin/env python3
"""Conan recipe for libdotconf 1.4.1."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LibdotconfConan(ConanFile):
    name = "libdotconf"
    version = "1.4.1"
    description = "Configuration file parser library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/williamh/dotconf"
    url = homepage
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        using_gcc = str(self.settings.compiler) == "gcc"
        cc = compilers.get("c", "gcc" if using_gcc else "clang")
        tool_dir = os.path.dirname(cc)
        default_ar = "ar" if using_gcc else "llvm-ar"
        default_ranlib = "ranlib" if using_gcc else "llvm-ranlib"
        ar = compilers.get("ar") or (
            os.path.join(tool_dir, default_ar) if tool_dir else default_ar
        )
        ranlib = compilers.get("ranlib") or (
            os.path.join(tool_dir, default_ranlib)
            if tool_dir
            else default_ranlib
        )
        optimization_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2",
            "RelWithDebInfo": "-O2 -g",
            "MinSizeRel": "-Os",
        }[str(self.settings.build_type)]

        include_dir = os.path.join(self.source_folder, "src")
        objects = []
        for filename in ("dotconf.c", "readdir.c"):
            source = os.path.join(include_dir, filename)
            obj = os.path.join(self.build_folder, f"{filename}.o")
            self.run(
                f'"{cc}" -std=c99 -D_GNU_SOURCE {optimization_flags} -fPIC -Wall '
                f'-I"{include_dir}" -c "{source}" -o "{obj}"'
            )
            objects.append(obj)

        library = os.path.join(self.build_folder, "libdotconf.a")
        object_args = " ".join(f'"{obj}"' for obj in objects)
        self.run(f'"{ar}" rcs "{library}" {object_args}')
        self.run(f'"{ranlib}" "{library}"')

        if can_run(self):
            self._run_upstream_examples(
                cc, ar, include_dir, optimization_flags
            )
        else:
            self.output.warning(
                "Skipping upstream example execution because target binaries "
                "cannot run in this build context"
            )

    def _run_upstream_examples(
        self, cc, ar, include_dir, optimization_flags
    ):
        examples_dir = os.path.join(self.source_folder, "examples")
        common_cflags = (
            f"-Wall {optimization_flags} -fPIC -I{include_dir}"
        )
        common_ldflags = f"-L{self.build_folder}"
        library = os.path.join(self.build_folder, "libdotconf.a")

        libpool_dir = os.path.join(examples_dir, "libpool")
        self.run(
            f'make -C "{libpool_dir}" CC="{cc}" AR="{ar}" '
            f'CFLAGS="{common_cflags}"'
        )

        scenarios = (
            ("caseinsensitive", "caseinsensitive", "", library),
            ("errorhandler", "errorhandler", "", library),
            ("fallback", "fallback", "", library),
            ("modules", "module", "", f"{library} -ldl"),
            ("noinline", "noinline", "", library),
            ("simple", "simple", "", library),
            ("argdouble", "argdouble", "", library),
            (
                "context",
                "context",
                "",
                f"{library} {os.path.join(libpool_dir, 'libpool.a')}",
            ),
            (
                "duplicates",
                "duplicate",
                "sample.conf",
                f"{library} {os.path.join(libpool_dir, 'libpool.a')} -ldl",
            ),
        )

        for directory, executable, arguments, libraries in scenarios:
            scenario_dir = os.path.join(examples_dir, directory)
            self.run(f'make -C "{scenario_dir}" clean')
            self.run(
                f'make -C "{scenario_dir}" CC="{cc}" '
                f'CFLAGS="{common_cflags}" LDFLAGS="{common_ldflags}" '
                f'LIBS="{libraries}"'
            )

            actual = os.path.join(scenario_dir, "testoutput")
            expected = os.path.join(scenario_dir, "output")
            executable_path = os.path.join(scenario_dir, executable)
            self.run(
                f'cd "{scenario_dir}" && "./{os.path.basename(executable_path)}" '
                f'{arguments} > "{actual}" 2>&1'
            )
            with open(actual, "rb") as actual_file:
                actual_output = actual_file.read()
            with open(expected, "rb") as expected_file:
                expected_output = expected_file.read()
            if actual_output != expected_output:
                if (
                    directory == "context"
                    and str(self.settings.os) == "OHOS"
                    and sorted(actual_output.splitlines())
                    == sorted(expected_output.splitlines())
                ):
                    self.output.info(
                        "Context example output lines match; ignoring "
                        "stdout/stderr interleaving on OHOS"
                    )
                    continue
                raise ConanException(
                    f"Upstream example output mismatch: {directory}"
                )

    def package(self):
        copy(
            self,
            "dotconf.h",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libdotconf.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["dotconf"]
        self.cpp_info.set_property("cmake_file_name", "libdotconf")
        self.cpp_info.set_property("cmake_target_name", "libdotconf::libdotconf")
        self.cpp_info.set_property("pkg_config_name", "dotconf")
