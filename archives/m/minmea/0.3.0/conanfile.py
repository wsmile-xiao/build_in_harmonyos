#!/usr/bin/env python3
"""Conan recipe — minmea 0.3.0 (Makefile)"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MinmeaConan(ConanFile):
    name = "minmea"
    version = "0.3.0"
    description = "A lightweight GPS NMEA 0183 parser library in pure C"
    license = "WTFPL"
    homepage = "https://github.com/kosma/minmea"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The minmea core is dependency-free: it only uses ISO C99 headers
        # (stdio/stdint/stdbool/errno/time/math/sys/time, string/ctype/stdarg).
        pass

    def build_requirements(self):
        # Only the upstream test suite (tests.c) needs Check; it is not part of
        # the installed link interface of libminmea.
        self.test_requires("check/0.15.2")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"minmea supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _dependency(self, name):
        for dependencies in (
            self.dependencies.test,
            self.dependencies.host,
            self.dependencies.build,
        ):
            try:
                return dependencies[name]
            except KeyError:
                continue
        return None

    def build(self):
        apply_conandata_patches(self)

        # R33: read the toolchain from Conan conf, never from shell variables
        # (release workers do not export CC/CFLAGS).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = str(compilers.get("c") or "clang").split()[0].strip("\"'")
        ar = str(compilers.get("ar") or "llvm-ar").split()[0].strip("\"'")

        check = self._dependency("check")
        if check is None:
            raise ConanInvalidConfiguration("check/0.15.2 test dependency not resolved")
        check_include = os.path.join(check.package_folder, "include")
        check_lib = os.path.join(check.package_folder, "lib", "libcheck.a")

        # The upstream Makefile hard-codes `-Werror`; clang 15 flags the Check
        # idiom `ck_assert_msg(expr, non_literal_format)` (tests.c:58) with
        # -Wformat-security, which older compilers accepted. Keep every other
        # upstream flag and demote only that diagnostic — no source change.
        cflags = "-g -Wall -Wextra -Werror -Wno-error=format-security -std=c99 -pthread"

        # 1) Library object, then the static/shared artifact (the upstream
        #    Makefile ships no install target, so packaging happens below).
        self.run(f"make CC={cc} AR={ar} minmea.o", cwd=self.source_folder, env="conanbuild")
        if self.options.shared:
            self.run(
                f"{cc} -shared -fPIC -o libminmea.so minmea.o",
                cwd=self.source_folder,
                env="conanbuild",
            )
        else:
            self.run(
                f"{ar} rcs libminmea.a minmea.o",
                cwd=self.source_folder,
                env="conanbuild",
            )

        # 2) Upstream test suite: `make test` compiles tests.c against Check,
        #    links ./tests and runs it (23 registered Check test cases).
        #    Check 0.15.2 consults TEMP before P_tmpdir, and /tmp is read-only
        #    on OHOS, so all three spellings point into the build folder.
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        test_env = Environment()
        test_env.define("TEMP", tmp)
        test_env.define("TMP", tmp)
        test_env.define("TMPDIR", tmp)

        # Link the static Check archive so ./tests needs no runtime lib path.
        ldlibs = f"{check_lib} -lm -lrt -pthread"
        with test_env.vars(self).apply():
            self.run(
                f'make CC={cc} CFLAGS="{cflags} -I{check_include}" '
                f'LDLIBS="{ldlibs}" tests',
                cwd=self.source_folder,
                env="conanbuild",
            )
            self.run("./tests", cwd=self.source_folder, env="conanbuild")

            # 3) Upstream `example` consumer program — the Makefile's `all`
            #    target builds it as well; only `scan-build` is skipped because
            #    the clang static analyzer wrapper is not shipped here.
            self.run(
                f'make CC={cc} CFLAGS="{cflags}" LDLIBS="{ldlibs}" example',
                cwd=self.source_folder,
                env="conanbuild",
            )

    def package(self):
        copy(
            self,
            "minmea.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        artifact = "libminmea.so" if self.options.shared else "libminmea.a"
        copy(
            self,
            artifact,
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "minmea")
        self.cpp_info.set_property("cmake_target_name", "minmea::minmea")
        self.cpp_info.set_property("pkg_config_name", "minmea")
        self.cpp_info.libs = ["minmea"]
