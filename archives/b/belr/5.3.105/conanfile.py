#!/usr/bin/env python3
"""Conan recipe for belr 5.3.105 (Belledonne ABNF language recognition library).

belr is the ABNF grammar / parser library of the Belledonne stack: it builds a
Grammar object from an ABNF description and then parses protocol text (used by
belle-sip for SIP, by linphone for SDP/XML payloads, ...).

The only runtime dependency is bctoolbox (same 5.3 release train). The upstream
bcunit based tester is built and executed inside build(); upstream does not
register it with ctest, so the recipe runs the tester binary directly, which is
how the upstream CI validates the library as well.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir

required_conan_version = ">=2.0"


class BelrConan(ConanFile):
    name = "belr"
    version = "5.3.105"
    package_type = "library"
    description = "ABNF grammar based language recognition library (Belledonne Communications)"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.linphone.org/BC/public/belr"
    url = ("https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/"
           "tree/main/archives/b/belr/5.3.105")
    topics = ("abnf", "grammar", "parser", "sip", "belledonne")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_unit_tests": [True, False],
        "with_tools": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_unit_tests": True,
        # The package only delivers the library and its headers: upstream's CLI
        # tools (belr-parse / belr-compiler) would require a software level
        # commands.json declaration (R38), which is out of scope for a version
        # directory PR. The tools can still be built from upstream sources.
        "with_tools": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream: find_package(BCToolbox 5.3.0 REQUIRED OPTIONAL_COMPONENTS tester)
        self.requires("bctoolbox/5.3.115")
        # BCUnit is the test framework of the Belledonne stack, needed only when
        # the tester is built: build time only, never part of the consumer graph.
        self.test_requires("bcunit/5.3.113")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "Macos", "Windows"):
            raise ConanInvalidConfiguration(f"{self.name} not validated for {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # BCUnit's CMake project version is frozen at 3.0.2 while the Belledonne
        # release train is 5.3.x (same handling as the bctoolbox/5.3.115 recipe).
        deps.set_property("bcunit", "cmake_config_version_compat", "AnyNewerVersion")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["ENABLE_STRICT"] = False
        tc.cache_variables["ENABLE_UNIT_TESTS"] = bool(self.options.with_unit_tests)
        tc.cache_variables["ENABLE_TOOLS"] = bool(self.options.with_tools)
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.cache_variables["BCToolbox_DIR"] = os.path.join(
            self.dependencies["bctoolbox"].package_folder, "share", "BCToolbox", "cmake")
        if self.settings.os in ("Linux", "OHOS"):
            # E092: CMake has no Platform/HarmonyOS module.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_unit_tests and can_run(self):
            # Upstream registers no ctest target for its bcunit tester, so run the
            # tester binary itself (resource dir is compiled in through
            # BELR_LOCAL_RESOURCE_LOCATION, so the build folder works as cwd).
            self.run(os.path.join("tester", "belr-tester"), cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # The tester is a build time verification artifact, not a deliverable of
        # this library package (same handling as bctoolbox/5.3.115).
        rmdir(self, os.path.join(self.package_folder, "bin"))
        # belr's public headers include bctoolbox headers (belr/parser.h ->
        # bctoolbox/defs.h, belr/belr.h -> bctoolbox/...), but the published
        # bctoolbox/5.3.115 package does not export its include directory to
        # transitive consumers (CMakeDeps generates an empty
        # bctoolbox_INCLUDE_DIRS), so the headers are shipped alongside - the
        # same handling the bzrtp/5.3.105 package uses for the Belledonne stack.
        bctoolbox_include = os.path.join(
            self.dependencies["bctoolbox"].package_folder, "include", "bctoolbox")
        for pattern in ("*.h", "*.hh", "*.hpp"):
            copy(self, pattern, src=bctoolbox_include,
                 dst=os.path.join(self.package_folder, "include", "bctoolbox"))

    def package_info(self):
        self.cpp_info.libs = ["belr"]
        # Link requirement only: the bctoolbox headers needed by belr's public
        # API are shipped inside this package (see package() above).
        self.cpp_info.requires = ["bctoolbox::bctoolbox"]
        self.cpp_info.set_property("cmake_file_name", "Belr")
        self.cpp_info.set_property("cmake_target_name", "Belr::belr")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        if not self.options.shared:
            # belr is built from C++ sources; a C consumer of the static archive
            # also needs the C++ runtime (same reasoning as bctoolbox/5.3.115).
            self.cpp_info.system_libs.append("c++")
