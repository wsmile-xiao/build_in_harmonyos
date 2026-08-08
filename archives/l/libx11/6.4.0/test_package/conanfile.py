#!/usr/bin/env python3
"""Consumer smoke test for libx11/6.4.0."""

import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        include_dirs, lib_dirs, dep_libs = self._collect_dependency_flags()
        include_flags = " ".join(f'-I"{path}"' for path in include_dirs)
        libdir_flags = " ".join(f'-L"{path}"' for path in lib_dirs)
        extra_libs = " ".join(
            f"-l{lib}" for lib in dep_libs if lib not in ("X11", "X11-xcb")
        )
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = self._resolve_compiler(compiler_executables.get("c"), "clang")
        source = os.path.join(self.source_folder, "test.c")
        self.run(
            f'"{cc}" "{source}" -o libx11_consumer '
            f"{include_flags} {libdir_flags} -lX11-xcb -lX11 {extra_libs}"
        )

    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host: compile-link only")
            return
        self.run("./libx11_consumer", env="conanrun")

    def _collect_dependency_flags(self):
        include_dirs = []
        lib_dirs = []
        dep_libs = []
        for _ref, dependency in self.dependencies.host.items():
            package_folder = dependency.package_folder or ""
            self._collect_cpp_info(
                dependency.cpp_info, package_folder, include_dirs, lib_dirs, dep_libs
            )
            for component in dependency.cpp_info.components.values():
                self._collect_cpp_info(
                    component, package_folder, include_dirs, lib_dirs, dep_libs
                )
        return (
            self._dedupe_existing_dirs(include_dirs),
            self._dedupe_existing_dirs(lib_dirs),
            self._dedupe(dep_libs),
        )

    @staticmethod
    def _collect_cpp_info(cpp_info, package_folder, include_dirs, lib_dirs, dep_libs):
        for path in cpp_info.includedirs or []:
            candidate = Path(path)
            if not candidate.is_absolute():
                candidate = Path(package_folder) / path
            include_dirs.append(str(candidate))
        for path in cpp_info.libdirs or []:
            candidate = Path(path)
            if not candidate.is_absolute():
                candidate = Path(package_folder) / path
            lib_dirs.append(str(candidate))
        dep_libs.extend(cpp_info.libs or [])

    @staticmethod
    def _dedupe_existing_dirs(paths):
        result = []
        seen = set()
        for path in paths:
            key = os.path.normcase(os.path.abspath(path))
            if key in seen or not os.path.isdir(path):
                continue
            seen.add(key)
            result.append(path)
        return result

    @staticmethod
    def _dedupe(values):
        result = []
        seen = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    @staticmethod
    def _resolve_compiler(configured, fallback):
        if configured:
            configured_path = str(configured).split()[0].strip("\"'")
            if os.path.exists(configured_path) and os.access(configured_path, os.X_OK):
                return configured
        return shutil.which(fallback) or os.environ.get("CC") or fallback
