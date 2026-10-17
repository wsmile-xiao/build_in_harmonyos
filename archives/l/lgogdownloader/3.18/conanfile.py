#!/usr/bin/env python3
"""Conan recipe — lgogdownloader 3.18 (CMake, C++ command line tool).

LGOGDownloader is an unofficial GOG.com downloader that speaks the GOG Galaxy
API. Upstream builds with CMake and links Boost (filesystem/regex/
program_options/date_time/iostreams), libcurl, jsoncpp, tinyxml2, rhash,
libtidy and zlib.

OpenHarmony port notes:
  * Upstream discovers its dependencies with the in-tree Find*.cmake modules,
    which rely on pkg-config and export the legacy FOO_INCLUDE_DIRS /
    FOO_LIBRARIES variables. On OHOS the libraries are consumed from the Conan
    registry and their CMakeDeps config packages only export imported targets,
    so patches/0001-CMakeLists.txt.patch links those targets directly
    (Boost::*, CURL::libcurl, JsonCpp::JsonCpp, tinyxml2::tinyxml2,
    rhash::rhash, Threads::Threads, ZLIB::ZLIB, Tidy::Tidy).
  * boost/1.85.0 is the component-complete published Boost whose
    Boost.Iostreams is compiled with the zlib filter. The 1.90/1.91 packages
    explicitly set BOOST_IOSTREAMS_ENABLE_ZLIB=False, so they cannot satisfy
    the gzip/zlib stream filters the downloader depends on.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LgogdownloaderConan(ConanFile):
    name = "lgogdownloader"
    version = "3.18"
    description = "Unofficial GOG.com downloader (GOG Galaxy API client)"
    license = "WTFPL"
    homepage = "https://github.com/Sude-/lgogdownloader"
    url = "https://github.com/Sude-/lgogdownloader"
    topics = ("gog", "downloader", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Boost.Iostreams provides the gzip/zlib stream filters used by the
        # downloader, therefore the zlib-enabled boost/1.85.0 is required.
        self.requires("boost/1.85.0")
        self.requires("curl/8.15.0.1")
        self.requires("jsoncpp/1.9.8.1")
        self.requires("tinyxml2/11.0.0")
        self.requires("rhash/1.4.6")
        self.requires("tidy-html5/5.8.0")
        # boost/1.85.0 is built against zlib/1.3.1 while curl pulls
        # zlib/1.3.1.1. The zlib ABI is stable, so unify the graph on the
        # revision already required by curl instead of rebuilding either.
        self.requires("zlib/1.3.1.1", override=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lgogdownloader is only supported on Linux and OHOS, "
                f"got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # The Qt WebEngine browser-login GUI is unavailable on OHOS; upstream
        # defaults to the CLI-only build, which also keeps the closure small.
        tc.variables["USE_QT_GUI"] = False
        tc.generate()

        # Required to execute the freshly built binary against the shared
        # Conan dependencies (curl/jsoncpp/tinyxml2/tidy/zlib) in build().
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_check()

    def _run_upstream_check(self):
        """Upstream's only automated check: the GitHub Actions "linux"
        workflow builds the project and runs `./lgogdownloader --help`."""
        if not can_run(self):
            self.output.info(
                "cross-building: lgogdownloader built, upstream smoke test not run"
            )
            return
        binary = os.path.join(self.build_folder, "lgogdownloader")
        self.run(f'"{binary}" --version', env="conanrun")
        self.run(f'"{binary}" --help', env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
