#!/usr/bin/env python3
"""Conan recipe — osm2pgrouting 3.0.0 (CMake, CLI tool).

osm2pgrouting imports an OpenStreetMap ``.osm`` file into a PostgreSQL/PostGIS
database, turning ways/relations into a routing topology. Build system: CMake.
Produces the single executable ``bin/osm2pgrouting`` plus the routing
configuration XML files under ``share/osm2pgrouting``.

Dependencies (all published in the ohpcd registry):
  * libpq/18.1      — pulled in explicitly; libpqxx/8.0.1 requires it anyway
  * libpqxx/8.0.1   — the C++ PostgreSQL client (`pqxx::connection`)
  * expat/2.8.2.1   — the XML SAX parser used for both the config and the data
  * boost/1.84.0    — `boost::program_options` drives the CLI

``cmake/FindOsmium.cmake`` is shipped by upstream but nothing in
``src/``/``include/`` includes libosmium; the real osmium import lives in
``tools/osmium``, a separate helper that the top-level CMakeLists does not
build. So libosmium is deliberately *not* a requirement here.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Osm2pgroutingConan(ConanFile):
    name = "osm2pgrouting"
    version = "3.0.0"
    description = "Import OpenStreetMap data into a PostgreSQL/PostGIS database as a routing topology"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/pgRouting/osm2pgrouting"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpq/18.1")
        self.requires("libpqxx/8.0.1")
        self.requires("expat/2.8.2.1")
        self.requires("boost/1.84.0")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"osm2pgrouting recipe supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # R32: settings.os judgement must include OHOS.
        if str(self.settings.os) == "OHOS":
            # CMake 4.1 on the OHOS worker ships Platform/OHOS.cmake; make the
            # toolchain explicit instead of relying on uname detection (same
            # approach as mp-units / libpqxx in this repository).
            toolchain.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            toolchain.blocks["generic_system"].values["cmake_system_processor"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # The shared OHOS profile pins compiler.cppstd=17, which would put
        # -std=gnu++17 on every compile line. libpqxx 8.x is a C++20 library
        # (upstream requirements.json) and its headers use concepts and
        # std::format, so the standard must be raised for the whole target.
        # A cache variable is not enough here: CMakeLists.txt assigns
        # CMAKE_CXX_STANDARD itself (patched to 20), and cache_variables lose
        # that shadowing fight, so patch the cppstd block the same way the
        # libpqxx recipe does.
        toolchain.blocks["cppstd"].values["cppstd"] = "20"
        toolchain.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        # `make install` equivalent: puts the binary in bin/ and COPYING,
        # README.md and the four mapconfig*.xml files in share/osm2pgrouting.
        cmake.install()

    def package_info(self):
        # Standalone CLI tool: the executable is the payload, no library is
        # exported (R38).
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "osm2pgrouting")
        self.cpp_info.set_property("cmake_target_name", "osm2pgrouting::osm2pgrouting")
        self.cpp_info.set_property("pkg_config_name", "osm2pgrouting")
