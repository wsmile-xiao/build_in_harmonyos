#!/usr/bin/env python3
"""Conan recipe — ratpoints 2.1.3 (Makefile/direct Clang build)."""

import filecmp
import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class RatpointsConan(ConanFile):
    name = "ratpoints"
    version = "2.1.3"
    description = "Library and program for finding rational points on hyperelliptic curves"
    license = "GPL-2.0-or-later"
    homepage = "https://www.mathe2.uni-bayreuth.de/stoll/programs/"
    url = "https://www.mathe2.uni-bayreuth.de/stoll/programs/"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ratpoints is supported on Linux and OHOS only"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _tool(self, language, fallback):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        candidate = (compilers.get(language) or "").strip()
        if candidate:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
            self.output.warning(
                "Configured %s compiler is not executable: %s" %
                (language, candidate)
            )
        return shutil.which(fallback) or fallback

    def _run_args(self, args, cwd=None, env=None):
        self.run(shlex.join([str(arg) for arg in args]), cwd=cwd, env=env)

    def _gmp_flags(self):
        dependency = self.dependencies["gmp"]
        include_flags = ["-I" + path for path in dependency.cpp_info.includedirs]
        library_flags = ["-L" + path for path in dependency.cpp_info.libdirs]
        # ratpoints uses GMP's C API only; avoid pulling the optional C++ wrapper.
        library_flags.append("-lgmp")
        return include_flags, library_flags

    def _compile_generators(self, cc, include_flags, library_flags):
        for stem in ("gen_init_sieve_h", "gen_find_points_h"):
            executable = os.path.join(self.build_folder, stem)
            self._run_args(
                [cc, "-O2", "-Wall", "-Wextra", "-I" + self.source_folder]
                + include_flags
                + [os.path.join(self.source_folder, stem + ".c"), "-o", executable]
                + library_flags
                + ["-lm"],
                cwd=self.build_folder,
            )
            header = os.path.join(
                self.build_folder,
                "init_sieve.h" if stem == "gen_init_sieve_h" else "find_points.h",
            )
            self.run(
                "%s > %s" % (shlex.quote(executable), shlex.quote(header)),
                cwd=self.build_folder,
                env="conanrun",
            )

    def _compile_objects(self, cc, include_flags):
        objects = []
        common = [
            cc,
            "-O2" if str(self.settings.build_type) == "Release" else "-O0",
            "-fPIC",
            "-fomit-frame-pointer",
            "-Wall",
            "-DRATPOINTS_MAX_BITS_IN_PRIME=7",
            "-DUSE_SSE",
            "-I" + self.source_folder,
            "-I" + self.build_folder,
        ] + include_flags
        for stem in ("sift", "init", "sturm", "find_points"):
            obj = os.path.join(self.build_folder, stem + ".o")
            extra = ["-funroll-loops"] if stem in ("sift", "init") else []
            self._run_args(
                common + extra
                + ["-c", os.path.join(self.source_folder, stem + ".c"), "-o", obj],
                cwd=self.build_folder,
            )
            objects.append(obj)
        return objects

    def _run_upstream_tests(self, cc, static_library, include_flags, library_flags):
        test_binary = os.path.join(self.build_folder, "rptest")
        actual = os.path.join(self.build_folder, "rptest.out")
        expected = os.path.join(self.source_folder, "testbase")
        self._run_args(
            [
                cc,
                "-O2",
                "-Wall",
                "-DRATPOINTS_MAX_BITS_IN_PRIME=7",
                "-DUSE_SSE",
                "-I" + self.source_folder,
                os.path.join(self.source_folder, "rptest.c"),
                static_library,
                "-o",
                test_binary,
            ] + include_flags + library_flags + ["-lm"],
            cwd=self.build_folder,
        )
        if not can_run(self):
            raise ConanException("The complete upstream test suite must run natively")
        self.run(
            "%s > %s" % (shlex.quote(test_binary), shlex.quote(actual)),
            cwd=self.build_folder,
            env="conanrun",
        )
        if not filecmp.cmp(expected, actual, shallow=False):
            raise ConanException(
                "rptest output does not match the upstream 1000-curve testbase"
            )
        with open(actual, encoding="utf-8") as result_file:
            executed = sum(1 for _line in result_file)
        if executed != 1000:
            raise ConanException(
                "rptest executed %d cases, expected 1000" % executed
            )
        marker = {
            "status": "passed",
            "framework": "upstream-rptest",
            "command": "rptest > rptest.out && cmp testbase rptest.out",
            "discovered": 1000,
            "executed": executed,
            "passed": executed,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )

    def build(self):
        cc = self._tool("c", "clang")
        ar = self._tool("ar", "llvm-ar")
        include_flags, library_flags = self._gmp_flags()
        self._compile_generators(cc, include_flags, library_flags)
        objects = self._compile_objects(cc, include_flags)

        static_library = os.path.join(self.build_folder, "libratpoints.a")
        self._run_args([ar, "rcs", static_library] + objects, cwd=self.build_folder)

        if self.options.shared:
            shared_library = os.path.join(self.build_folder, "libratpoints.so")
            self._run_args(
                [cc, "-shared", "-o", shared_library] + objects
                + library_flags + ["-lm"],
                cwd=self.build_folder,
            )

        executable = os.path.join(self.build_folder, "ratpoints")
        self._run_args(
            [
                cc,
                "-O2",
                "-Wall",
                "-DRATPOINTS_MAX_BITS_IN_PRIME=7",
                "-DUSE_SSE",
                "-I" + self.source_folder,
                os.path.join(self.source_folder, "main.c"),
                static_library,
                "-o",
                executable,
            ] + include_flags + library_flags + ["-lm"],
            cwd=self.build_folder,
        )
        self._run_upstream_tests(
            cc, static_library, include_flags, library_flags
        )

    def package(self):
        copy(
            self,
            "ratpoints.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        library = "libratpoints.so" if self.options.shared else "libratpoints.a"
        copy(
            self,
            library,
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "ratpoints",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "gpl-2.0.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["ratpoints"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "ratpoints")
        self.cpp_info.set_property("cmake_target_name", "ratpoints::ratpoints")
