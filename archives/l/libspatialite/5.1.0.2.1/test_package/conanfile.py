#!/usr/bin/env python3
"""Consumer validation for libspatialite 5.1.0.2.1."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment


class LibspatialiteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The consumer directly includes and calls SQLite's public API.
        self.requires("sqlite3/3.49.1")

    def _validate_dependency_contract(self):
        expected_versions = {
            "sqlite3": "3.49.1",
            "zlib": "1.3.1.1",
            "proj": "9.3.1.1",
            "librttopo": "1.1.0",
            "geos": "3.13.1",
            "libxml2": "2.15.3",
        }
        for name, expected_version in expected_versions.items():
            try:
                dependency = self.dependencies[name]
            except KeyError as error:
                raise ConanInvalidConfiguration(
                    "consumer dependency graph is missing {}".format(name)
                ) from error
            actual_version = str(dependency.ref.version)
            if actual_version != expected_version:
                raise ConanInvalidConfiguration(
                    "consumer dependency {} has version {}, expected {}".format(
                        name, actual_version, expected_version
                    )
                )
            if dependency.package_folder is None:
                # zlib is a runtime-only transitive dependency of the shared
                # libspatialite package and may be skipped by Conan's test
                # graph; its exact version is still checked above.
                if name == "zlib":
                    continue
                raise ConanInvalidConfiguration(
                    "consumer dependency {} has no binary package folder".format(name)
                )
            if not os.path.isdir(dependency.package_folder):
                raise ConanInvalidConfiguration(
                    "consumer dependency {} has no binary package folder".format(name)
                )
            if not dependency.cpp_info.includedirs:
                raise ConanInvalidConfiguration(
                    "consumer dependency {} has no include metadata".format(name)
                )
            if not dependency.cpp_info.libdirs:
                raise ConanInvalidConfiguration(
                    "consumer dependency {} has no library metadata".format(name)
                )

    def build(self):
        self._validate_dependency_contract()
        package_order = [
            "libspatialite",
            "sqlite3",
            "zlib",
            "proj",
            "geos",
            "librttopo",
            "libxml2",
        ]
        dependencies = []
        for name in package_order:
            try:
                dependency = self.dependencies[name]
            except KeyError:
                continue
            if dependency.package_folder is not None:
                dependencies.append(dependency)

        include_dirs = []
        lib_dirs = []
        libraries = []
        system_libraries = []
        for dependency in dependencies:
            include_dirs.extend(dependency.cpp_info.includedirs)
            lib_dirs.extend(dependency.cpp_info.libdirs)
            libraries.extend(dependency.cpp_info.libs)
            system_libraries.extend(dependency.cpp_info.system_libs)

        include_dirs = self._unique(include_dirs)
        lib_dirs = self._unique(lib_dirs)
        libraries = self._unique(libraries)
        system_libraries = self._unique(system_libraries + ["m", "pthread", "dl"])

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c", "clang") if compiler_executables else "clang"
        command = ['"{}"'.format(cc), '"{}"'.format(os.path.join(self.source_folder, "test.c"))]
        command.extend(["-I\"{}\"".format(path) for path in include_dirs])
        command.extend(["-L\"{}\"".format(path) for path in lib_dirs])
        command.extend(["-Wl,-rpath,{}".format(path) for path in lib_dirs])
        command.extend(["-Wl,-rpath-link,{}".format(path) for path in lib_dirs])
        command.extend(["-l{}".format(name) for name in libraries])
        command.extend(["-l{}".format(name) for name in system_libraries])
        command.extend(["-std=c11", "-O2", "-o", '"{}"'.format(self._test_binary)])
        with self._writable_tmp_environment().vars(self).apply():
            self.run(" ".join(command))
            self._sign_test_binary()

    @property
    def _test_binary(self):
        return os.path.join(self.build_folder, "test_libspatialite")

    @staticmethod
    def _unique(values):
        result = []
        for value in values:
            if value not in result:
                result.append(value)
        return result

    def _writable_tmp_environment(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment = Environment()
        environment.define("TMPDIR", tmpdir)
        environment.define("TMPPREFIX", tmpdir)
        return environment

    def _sign_test_binary(self):
        if str(self.settings.os) != "OHOS":
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanInvalidConfiguration("OHOS consumer execution requires signing tools")
        self.run('"{}" --remove-section .codesign "{}"'.format(objcopy, self._test_binary))
        self.run('"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, self._test_binary, self._test_binary))

    def test(self):
        if cross_building(self):
            self.output.info("Cross build: consumer compile/link passed; target execution is separate")
            return
        with self._writable_tmp_environment().vars(self).apply():
            self.run('"{}"'.format(self._test_binary), env="conanrun")
