#!/usr/bin/env python3
"""Conan recipe for talloc 2.4.4 on HarmonyOS."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class TallocConan(ConanFile):
    name = "talloc"
    version = "2.4.4"
    description = "Hierarchical, reference-counted memory pool library"
    license = "LGPL-3.0-or-later"
    homepage = "https://talloc.samba.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    exports_sources = "files/*"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
    def generate(self):
        VirtualBuildEnv(self).generate()


    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar")
        if not ar:
            compiler_dir = os.path.dirname(cc) if os.path.sep in cc else ""
            candidate = os.path.join(compiler_dir, "llvm-ar") if compiler_dir else ""
            ar = candidate if candidate and os.path.isfile(candidate) else "llvm-ar"

        obj = os.path.join(self.build_folder, "talloc.o")
        compat_obj = os.path.join(self.build_folder, "talloc_compat.o")
        archive = os.path.join(self.build_folder, "libtalloc.a")
        build_type_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        optimization_flags = build_type_flags.get(
            str(self.settings.build_type), "-O2"
        )
        flags = (
            f"{optimization_flags} -fPIC -std=c11 -D_GNU_SOURCE -include limits.h "
            "-DRTLD_DEFAULT=0 "
            "-D__STDC_WANT_LIB_EXT1__=1 -DNO_CONFIG_H "
            "-DHAVE_STDINT_H -DHAVE_INTTYPES_H -DHAVE_UNISTD_H "
            "-DHAVE_STRING_H -DHAVE_STRINGS_H -DHAVE_VA_COPY "
            "-DHAVE_MEMMOVE -DHAVE_STRNLEN "
            "-DHAVE_VSNPRINTF -DHAVE_C99_VSNPRINTF "
            "-DHAVE_STDBOOL_H -DHAVE_BOOL -DHAVE_INTPTR_T "
            "-DHAVE_UINTPTR_T -DHAVE_PTRDIFF_T -DHAVE_SIZE_T "
            "-DHAVE_USLEEP -DHAVE_COPY_FILE_RANGE -DHAVE_POLL "
            "-DHAVE_CONSTRUCTOR_ATTRIBUTE "
            "-DTALLOC_BUILD_VERSION_MAJOR=2 "
            "-DTALLOC_BUILD_VERSION_MINOR=4 "
            "-DTALLOC_BUILD_VERSION_RELEASE=4"
        )
        self.run(
            '"{}" {} -I"{}" -I"{}" -c "{}" -o "{}"'.format(
                cc,
                flags,
                self.source_folder,
                os.path.join(self.source_folder, "lib", "replace"),
                os.path.join(self.source_folder, "talloc.c"),
                obj,
            )
        )
        self.run(
            '"{}" {} -fPIC -std=c11 -c "{}" -o "{}"'.format(
                cc,
                optimization_flags,
                os.path.join(self.source_folder, "files", "talloc_compat.c"),
                compat_obj,
            )
        )
        self.run(
            '"{}" rcs "{}" "{}" "{}"'.format(ar, archive, obj, compat_obj)
        )
        self._run_upstream_tests(cc, optimization_flags)

    def _run_upstream_tests(self, cc, optimization_flags):
        """Build and run the upstream C test suites against libtalloc.a.

        talloc_testsuite (testsuite_main.c + testsuite.c) is the core C
        test suite; test_magic_differs.sh verifies that two separate talloc
        processes do not share the same magic value.  The Python binding
        test (test_pytalloc.py) requires Python development headers that are
        unavailable in the OHOS cross-build environment, so it is documented
        as excluded rather than built.
        """
        common = (
            f"{optimization_flags} -fPIC -std=c11 -D_GNU_SOURCE -include limits.h "
            "-DRTLD_DEFAULT=0 -D__STDC_WANT_LIB_EXT1__=1 -DNO_CONFIG_H "
            "-DHAVE_STDINT_H -DHAVE_INTTYPES_H -DHAVE_UNISTD_H "
            "-DHAVE_STRING_H -DHAVE_STRINGS_H -DHAVE_VA_COPY "
            "-DHAVE_MEMMOVE -DHAVE_STRNLEN "
            "-DHAVE_VSNPRINTF -DHAVE_C99_VSNPRINTF "
            "-DHAVE_STDBOOL_H -DHAVE_BOOL -DHAVE_INTPTR_T "
            "-DHAVE_UINTPTR_T -DHAVE_PTRDIFF_T -DHAVE_SIZE_T "
            "-DHAVE_USLEEP -DHAVE_COPY_FILE_RANGE -DHAVE_POLL "
            "-DHAVE_CONSTRUCTOR_ATTRIBUTE -DHAVE_PTHREAD -DHAVE___THREAD -DHAVE_STRUCT_TIMESPEC -DHAVE_SYS_TIME_H -DTIME_WITH_SYS_TIME -DHAVE_SNPRINTF -DHAVE_STRDUP -DHAVE_SETLINEBUF "
            f'-I"{self.source_folder}" -I"{self.source_folder}/lib/replace"'
        )
        archive = os.path.join(self.build_folder, "libtalloc.a")
        testsuite_bin = os.path.join(self.build_folder, "talloc_testsuite")
        self.run(
            '"{}" {} "{}" "{}" "{}" -lpthread -o "{}"'.format(
                cc,
                common,
                os.path.join(self.source_folder, "testsuite_main.c"),
                os.path.join(self.source_folder, "testsuite.c"),
                archive,
                testsuite_bin,
            ),
            env="conanbuild",
        )
        if can_run(self):
            self.run('"{}"'.format(testsuite_bin), env="conanbuild")
            self.output.info("upstream talloc_testsuite passed")
        else:
            self.output.info(
                "upstream talloc_testsuite skipped: cannot run target binaries "
                "on the build host (cross build)"
            )

        magic_helper = os.path.join(
            self.build_folder, "talloc_test_magic_differs_helper"
        )
        self.run(
            '"{}" {} "{}" "{}" -o "{}"'.format(
                cc,
                common,
                os.path.join(self.source_folder, "test_magic_differs_helper.c"),
                archive,
                magic_helper,
            ),
            env="conanbuild",
        )
        if can_run(self):
            self.run(
                'sh "{}" "{}"'.format(
                    os.path.join(self.source_folder, "test_magic_differs.sh"),
                    magic_helper,
                ),
                env="conanbuild",
            )
            self.output.info("upstream test_magic_differs passed")
        else:
            self.output.info(
                "upstream test_magic_differs skipped: cannot run target "
                "binaries on the build host (cross build)"
            )
        self.output.info(
            "upstream test_pytalloc.py excluded: Python binding not built "
            "(no Python development headers in OHOS cross-build environment)"
        )
    def package(self):
        copy(
            self,
            "talloc.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libtalloc.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["talloc"]
        self.cpp_info.set_property("cmake_file_name", "talloc")
        self.cpp_info.set_property("cmake_target_name", "talloc::talloc")
        self.cpp_info.set_property("pkg_config_name", "talloc")
