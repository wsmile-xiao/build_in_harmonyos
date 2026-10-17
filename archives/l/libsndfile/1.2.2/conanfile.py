#!/usr/bin/env python3
"""Conan recipe for libsndfile 1.2.2."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibsndfileConan(ConanFile):
    _upstream_tests = (
        "test_main",
        "sfversion",
        "error_test",
        "ulaw_test",
        "alaw_test",
        "command_test",
        "checksum_test",
        "headerless_test",
        "rdwr_test",
        "format_check_test",
        "channel_test",
        "virtual_io_test",
    )
    _upstream_test_regex = "^(" + "|".join(_upstream_tests) + ")$"

    name = "libsndfile"
    version = "1.2.2"
    description = "C library for reading and writing sampled audio files"
    license = "LGPL-2.1-or-later"
    homepage = "https://libsndfile.github.io/libsndfile/"
    url = "https://github.com/libsndfile/libsndfile"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_PROGRAMS"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_TESTING"] = not bool(self.options.shared)
        tc.variables["BUILD_REGTEST"] = False
        tc.variables["ENABLE_EXTERNAL_LIBS"] = False
        tc.variables["ENABLE_MPEG"] = False
        tc.variables["ENABLE_EXPERIMENTAL"] = False
        tc.variables["INSTALL_MANPAGES"] = False
        tc.generate()

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"Missing upstream test executable: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".libsndfile-signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not self.options.shared and can_run(self):
            if str(self.settings.os) == "OHOS":
                for test_name in self._upstream_tests:
                    self._sign_ohos_elf(os.path.join(self.build_folder, test_name))
            self.run(
                f'ctest --output-on-failure -j 1 -R "{self._upstream_test_regex}"',
                cwd=self.build_folder,
                env=["conanbuild", "conanrun"],
            )
        elif not self.options.shared:
            self.output.warning("Cannot run the selected upstream CTest subset")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["sndfile"]
        self.cpp_info.set_property("cmake_file_name", "SndFile")
        self.cpp_info.set_property("cmake_target_name", "SndFile::sndfile")
        self.cpp_info.set_property("pkg_config_name", "sndfile")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
