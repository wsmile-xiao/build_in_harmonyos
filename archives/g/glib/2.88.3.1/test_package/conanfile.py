#!/usr/bin/env python3
"""Conan consumer test for GLib 2.88.3.1."""

import filecmp
import os
import re
import shlex
import stat
from io import StringIO

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class Glib2TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    _shared_library_stems = (
        "libglib-2.0",
        "libgobject-2.0",
        "libgmodule-2.0",
        "libgio-2.0",
        "libgthread-2.0",
        "libgirepository-2.0",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("pcre2/10.47")
        self.requires("libffi/3.5.2")
        self.requires("zlib/1.3.2")
        self.requires("proxy-libintl/0.5")

    def layout(self):
        cmake_layout(self)

    def _require_materialized_shared_library_aliases(self, package_lib):
        for stem in self._shared_library_stems:
            pattern = re.compile(
                rf"^{re.escape(stem)}[.]so[.](?P<major>[0-9]+)$"
            )
            runtime_libraries = [
                os.path.join(package_lib, name)
                for name in os.listdir(package_lib)
                if pattern.fullmatch(name)
                and os.path.isfile(os.path.join(package_lib, name))
                and not os.path.islink(os.path.join(package_lib, name))
            ]
            if len(runtime_libraries) != 1:
                raise ConanInvalidConfiguration(
                    f"expected one regular runtime SONAME for {stem!r}, "
                    f"found {len(runtime_libraries)}"
                )

            source = runtime_libraries[0]
            forbidden_versioned = re.compile(
                rf"^{re.escape(stem)}[.]so[.][0-9]+[.][0-9]+"
            )
            residual = [
                name
                for name in os.listdir(package_lib)
                if forbidden_versioned.match(name)
            ]
            if residual:
                raise ConanInvalidConfiguration(
                    f"full-version shared objects remain beside the runtime "
                    f"SONAME for {stem!r}: {residual}"
                )
            source_mode = stat.S_IMODE(
                os.stat(source, follow_symlinks=False).st_mode
            )
            if os.name == "posix" and not source_mode & stat.S_IXUSR:
                raise ConanInvalidConfiguration(
                    f"versioned shared object is not owner-executable: {source!r}"
                )
            aliases = (f"{stem}.so",)
            alias_modes = []
            for alias_name in aliases:
                alias = os.path.join(package_lib, alias_name)
                alias_mode = (
                    stat.S_IMODE(os.stat(alias, follow_symlinks=False).st_mode)
                    if os.path.lexists(alias)
                    else None
                )
                if (
                    not os.path.isfile(alias)
                    or os.path.islink(alias)
                    or not filecmp.cmp(alias, source, shallow=False)
                    or alias_mode != source_mode
                ):
                    raise ConanInvalidConfiguration(
                        f"shared-library alias must be a byte-and-mode-identical "
                        f"regular file: {alias!r}"
                    )
                alias_modes.append(f"{alias_name}={oct(alias_mode)}")
            self.output.info(
                f"validated materialized aliases for {stem}: "
                f"source_mode={oct(source_mode)} " + " ".join(alias_modes)
            )

    def _runtime_environment(self):
        dependency = self.dependencies[self.tested_reference_str]
        package_lib = os.path.abspath(
            os.path.join(dependency.package_folder, "lib")
        )
        if not os.path.isdir(package_lib):
            raise ConanInvalidConfiguration(
                f"GLib package library directory is missing: {package_lib}"
            )
        self._require_materialized_shared_library_aliases(package_lib)
        runtime_paths = [package_lib]
        seen_paths = {os.path.normcase(package_lib)}
        for dependency_requirement, host_dependency in self.dependencies.items():
            if dependency_requirement.build or dependency_requirement.test:
                continue
            if not host_dependency.package_folder:
                continue
            for libdir in host_dependency.cpp_info.libdirs:
                libdir = os.fspath(libdir)
                if not os.path.isabs(libdir):
                    libdir = os.path.join(
                        host_dependency.package_folder, libdir
                    )
                libdir = os.path.abspath(libdir)
                if not os.path.isdir(libdir):
                    continue
                identity = os.path.normcase(libdir)
                if identity in seen_paths:
                    continue
                seen_paths.add(identity)
                runtime_paths.append(libdir)

        runtime_path = os.pathsep.join(runtime_paths)
        self.output.info(f"GLIB2_RUNTIME_PATHS={runtime_path}")
        return runtime_path, runtime_paths

    def generate(self):
        _, runtime_paths = self._runtime_environment()
        toolchain = CMakeToolchain(self)
        if str(self.settings.os) in ("Linux", "OHOS"):
            runtime_path = ":".join(runtime_paths)
            toolchain.variables["GLIB2_TEST_RPATH_LINK_OPTION"] = (
                f"-Wl,--disable-new-dtags,-rpath,{runtime_path}"
            )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])

    def test(self):
        if not can_run(self):
            self.output.info("NOT_RUN GLIB2_CONSUMER=0/1 reason=cross_building")
            return

        runtime_path, runtime_paths = self._runtime_environment()
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c")
        if not compiler:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables is missing the C compiler"
            )
        readelf = os.path.join(os.path.dirname(compiler), "llvm-readelf")
        if not os.path.isfile(readelf):
            raise ConanInvalidConfiguration(f"llvm-readelf is missing: {readelf}")

        package_lib = runtime_paths[0]
        loader_libraries = []
        for stem in self._shared_library_stems:
            pattern = re.compile(rf"^{re.escape(stem)}[.]so[.][0-9]+$")
            matches = [
                os.path.join(package_lib, name)
                for name in os.listdir(package_lib)
                if pattern.fullmatch(name)
                and os.path.isfile(os.path.join(package_lib, name))
                and not os.path.islink(os.path.join(package_lib, name))
            ]
            if len(matches) != 1:
                raise ConanInvalidConfiguration(
                    f"expected one runtime SONAME for loader probe {stem!r}, "
                    f"found {len(matches)}"
                )
            loader_libraries.append(matches[0])
        self.output.info(
            "GLIB2_LOADER_PROBE_PATHS=" + os.pathsep.join(loader_libraries)
        )
        self.run(
            f"LD_LIBRARY_PATH={shlex.quote(runtime_path)} "
            "./test_glib2_loader "
            + " ".join(shlex.quote(path) for path in loader_libraries),
            env="conanrun",
            scope="run",
        )

        dynamic_output = StringIO()
        self.run(
            f"{shlex.quote(readelf)} -d ./test_glib2",
            stdout=dynamic_output,
            env=None,
            scope="run",
        )
        dynamic_text = dynamic_output.getvalue()
        rpath_lines = [
            line.strip()
            for line in dynamic_text.splitlines()
            if "(RPATH)" in line
        ]
        if len(rpath_lines) != 1 or "(RUNPATH)" in dynamic_text:
            raise ConanInvalidConfiguration(
                "GLib target consumer must use DT_RPATH without DT_RUNPATH"
            )
        self.output.info(f"GLIB2_CONSUMER_DYNAMIC_RPATH={rpath_lines[0]}")
        missing_paths = [path for path in runtime_paths if path not in dynamic_text]
        if missing_paths:
            raise ConanInvalidConfiguration(
                f"GLib consumer RPATH is missing runtime directories: {missing_paths}"
            )

        self.run(
            f"LD_LIBRARY_PATH={shlex.quote(runtime_path)} "
            "./test_glib2",
            env="conanrun",
            scope="run",
        )
