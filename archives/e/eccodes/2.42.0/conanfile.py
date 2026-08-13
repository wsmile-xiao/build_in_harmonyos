#!/usr/bin/env python3
"""Conan recipe for ECMWF ecCodes 2.42.0."""

import os
import posixpath
import shutil
import tarfile
from pathlib import PurePosixPath

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, download, export_conandata_patches


class EccodesConan(ConanFile):
    name = "eccodes"
    version = "2.42.0"
    description = "ECMWF GRIB and BUFR encoding/decoding library"
    license = "Apache-2.0"
    homepage = "https://confluence.ecmwf.int/display/ECC/ecCodes+Home"
    url = "https://confluence.ecmwf.int/display/ECC/ecCodes+Home"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_upstream_tests": False,
    }

    def layout(self):
        cmake_layout(self, src_folder=".")

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("eccodes/2.42.0 recipe currently supports Linux and OHOS")
        if not self.options.shared:
            raise ConanInvalidConfiguration("eccodes/2.42.0 first-pass package builds the shared library only")
        if self.options.shared:
            self.options.rm_safe("fPIC")

    @staticmethod
    def _archive_relative_path(member_name, archive_root):
        normalized = posixpath.normpath(member_name)
        if normalized == archive_root:
            return None
        prefix = archive_root + "/"
        if not normalized.startswith(prefix):
            raise ConanInvalidConfiguration(
                "ecCodes source archive contains a member outside its source root: {!r}".format(member_name)
            )
        relative = PurePosixPath(normalized[len(prefix):])
        if relative.is_absolute() or ".." in relative.parts:
            raise ConanInvalidConfiguration(
                "ecCodes source archive contains an unsafe member path: {!r}".format(member_name)
            )
        return relative

    def _materialize_ohos_source_archive(self, archive_path):
        """Extract the fixed source archive without creating unsupported symlinks."""
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            names = [posixpath.normpath(member.name) for member in members if member.name]
            roots = {name.split("/", 1)[0] for name in names}
            if len(roots) != 1:
                raise ConanInvalidConfiguration(
                    "ecCodes source archive must contain exactly one source root"
                )
            archive_root = roots.pop()

            for member in members:
                self._archive_relative_path(member.name, archive_root)
                if not (member.isdir() or member.isreg() or member.issym()):
                    raise ConanInvalidConfiguration(
                        "ecCodes source archive contains an unsupported member type: {!r}".format(member.name)
                    )

            def destination(relative):
                return os.path.join(self.source_folder, *relative.parts)

            for member in members:
                relative = self._archive_relative_path(member.name, archive_root)
                if relative is not None and member.isdir():
                    path = destination(relative)
                    os.makedirs(path, exist_ok=True)
                    os.chmod(path, member.mode & 0o777)

            for member in members:
                relative = self._archive_relative_path(member.name, archive_root)
                if relative is None or not member.isreg():
                    continue
                path = destination(relative)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise ConanInvalidConfiguration(
                        "ecCodes source archive member cannot be read: {!r}".format(member.name)
                    )
                with source, open(path, "wb") as output:
                    shutil.copyfileobj(source, output)
                os.chmod(path, member.mode & 0o777)

            for member in members:
                relative = self._archive_relative_path(member.name, archive_root)
                if relative is None or not member.issym():
                    continue
                target_name = posixpath.normpath(
                    posixpath.join(posixpath.dirname(member.name), member.linkname)
                )
                target_relative = self._archive_relative_path(target_name, archive_root)
                if target_relative is None:
                    raise ConanInvalidConfiguration(
                        "ecCodes source archive symlink targets its source root: {!r}".format(member.name)
                    )
                source_path = destination(target_relative)
                target_path = destination(relative)
                if os.path.isdir(source_path):
                    shutil.copytree(source_path, target_path)
                elif os.path.isfile(source_path):
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    shutil.copy2(source_path, target_path)
                else:
                    raise ConanInvalidConfiguration(
                        "ecCodes source archive symlink target is unavailable: {!r}".format(member.name)
                    )

    def _materialize_ohos_bufr_filter(self, directory):
        """Replace the unsupported /bin/sh compatibility wrapper with its tool."""
        source = os.path.join(directory, "codes_bufr_filter")
        destination = os.path.join(directory, "bufr_filter")
        if not os.path.isfile(source):
            raise ConanInvalidConfiguration("ecCodes BUFR filter tool was not built: {!r}".format(source))
        shutil.copy2(source, destination)

    def source(self):
        sources = self.conan_data["sources"]
        archive_name = sources["filename"]
        archive_path = os.path.join(self.source_folder, archive_name)
        download(self, **sources)
        try:
            self._materialize_ohos_source_archive(archive_path)
        finally:
            if os.path.exists(archive_path):
                os.remove(archive_path)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["ENABLE_AEC"] = "OFF"
        tc.variables["ENABLE_JPG"] = "OFF"
        tc.variables["ENABLE_JPG_LIBJASPER"] = "OFF"
        tc.variables["ENABLE_JPG_LIBOPENJPEG"] = "OFF"
        tc.variables["ENABLE_PNG"] = "OFF"
        tc.variables["ENABLE_NETCDF"] = "OFF"
        tc.variables["ENABLE_FORTRAN"] = "OFF"
        tc.variables["ENABLE_GEOGRAPHY"] = "OFF"
        tc.variables["ENABLE_ECKIT_GEO"] = "OFF"
        tc.variables["ENABLE_MEMFS"] = "OFF"
        tc.variables["ENABLE_EXAMPLES"] = "OFF"
        tc.variables["ENABLE_BUILD_TOOLS"] = (
            "ON" if self.options.with_upstream_tests else "OFF"
        )
        tc.variables["ENABLE_TESTS"] = "ON" if self.options.with_upstream_tests else "OFF"
        tc.variables["ENABLE_EXTRA_TESTS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "ON" if self.options.with_upstream_tests else "OFF"
        tc.variables["ENABLE_INSTALL_ECCODES_DEFINITIONS"] = "ON"
        tc.variables["ENABLE_INSTALL_ECCODES_SAMPLES"] = "ON"
        tc.variables["ENABLE_ECCODES_THREADS"] = "OFF"
        tc.variables["ENABLE_ECCODES_OMP_THREADS"] = "OFF"
        tc.variables["DISABLE_OS_CHECK"] = "ON"
        tc.variables["IEEE_BE"] = "0"
        tc.variables["IEEE_LE"] = "1"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.variables["ECCODES_OHOS_MATERIALIZE_BUILD_DATA"] = "ON"
            tc.variables["ECCODES_OHOS_RUN_TEST_SCRIPTS_WITH_BASH"] = "ON"
            tc.variables["ECCODES_TESTING_BASH"] = "/data/service/hnp/bin/bash"
        tc.generate()

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.settings.os == "OHOS" and self.options.with_upstream_tests:
            self._materialize_ohos_bufr_filter(os.path.join(self.build_folder, "bin"))
        if self.options.with_upstream_tests and can_run(self):
            if self.settings.os == "OHOS":
                previous_pwd = os.environ.get("PWD")
                os.environ["PWD"] = os.path.join(self.build_folder, "tests")
                try:
                    cmake.test()
                finally:
                    if previous_pwd is None:
                        os.environ.pop("PWD", None)
                    else:
                        os.environ["PWD"] = previous_pwd
            else:
                cmake.test()

    def package(self):
        CMake(self).install()
        if self.settings.os == "OHOS" and self.options.with_upstream_tests:
            self._materialize_ohos_bufr_filter(os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["eccodes"]
        self.cpp_info.set_property("cmake_file_name", "eccodes")
        self.cpp_info.set_property("cmake_target_name", "eccodes::eccodes")
        self.cpp_info.set_property("pkg_config_name", "eccodes")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

        definitions = os.path.join(self.package_folder, "share", "eccodes", "definitions")
        samples = os.path.join(self.package_folder, "share", "eccodes", "samples")
        self.runenv_info.define_path("ECCODES_DEFINITION_PATH", definitions)
        self.runenv_info.define_path("ECCODES_SAMPLES_PATH", samples)
