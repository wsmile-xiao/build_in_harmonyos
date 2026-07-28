#!/usr/bin/env python3
"""Conan recipe for the maintained MP4v2 2.1.3 release on OpenHarmony."""

import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, get


class Mp4v2Conan(ConanFile):
    name = "mp4v2"
    version = "2.1.3"
    package_type = "library"
    license = "MPL-1.1"
    homepage = "https://mp4v2.org/"
    description = "A C++ library for reading and writing MP4 files"

    exports_sources = "patches/*"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED"] = self.options.shared
        toolchain.variables["BUILD_UTILS"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Mirror the 28 standardUsage.exp assertions from the upstream DejaGnu suite.
        if can_run(self):
            self.output.info("Running 28 upstream standardUsage.exp assertions")
            for tool in ("mp4art", "mp4file", "mp4subtitle", "mp4track"):
                self._test_standard_usage(os.path.join(self.build_folder, tool))
            self.output.info("Upstream standardUsage.exp assertions passed")
        else:
            self.output.info(
                "Skipping upstream standardUsage.exp assertions: target binaries cannot run on this build machine"
            )

    def _test_standard_usage(self, tool):
        environment = os.environ.copy()
        library_path = {
            "Macos": "DYLD_LIBRARY_PATH",
            "Windows": "PATH",
        }.get(str(self.settings.os), "LD_LIBRARY_PATH")
        environment[library_path] = self.build_folder + os.pathsep + environment.get(library_path, "")
        cases = (
            ((), 1, (r"^Usage: \S+", r"^Try.*-h.*--help")),
            (("-h",), 0, (r"^Usage: \S+", r"\s+--help", r"\s+--version")),
            (("--help",), 0, (r"^Usage: \S+", r"\s+--help", r"\s+--version", r"^VERBOSE LEVELS")),
            (("--version",), 0, (r"^\S+\s-\s\S+",)),
            (("--versionx",), 0, (r"^utility:\s+\S+", r"^product:\s+\S+", r"^version:\s+\S+")),
            (("-*",), 1, (r"^invalid",)),
            (("--bogusLongOption",), 1, (r"^unrecognized",)),
        )

        for arguments, expected_returncode, patterns in cases:
            completed = subprocess.run(
                [tool, *arguments],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
                env=environment,
            )
            if completed.returncode != expected_returncode:
                raise ConanException(
                    "{} {} returned {}, expected {}".format(
                        os.path.basename(tool), " ".join(arguments),
                        completed.returncode, expected_returncode,
                    )
                )
            for pattern in patterns:
                if not re.search(pattern, completed.stdout, re.MULTILINE):
                    raise ConanException(
                        "{} {} did not match {}".format(
                            os.path.basename(tool), " ".join(arguments), pattern
                        )
                    )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["mp4v2"]
        self.cpp_info.bindirs = ["bin"]
