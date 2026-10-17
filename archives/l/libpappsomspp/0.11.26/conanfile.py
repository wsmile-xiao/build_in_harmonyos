#!/usr/bin/env python3
"""Conan recipe — libpappsomspp 0.11.26 (PAPPSO mass spectrometry C++ core).

PAPPSOms++ is the PAPPSO mass-spectrometry foundation library used by
X!Tandem Pipeline, MineXpert2 and MassChroQ (forgemia.inra.fr/pappso/
pappsomspp, upstream tag upstream/0.11.26). Upstream task #13377.

Chain position (this is the 4th and final piece):
  liblzf 3.6 → libodsstream 0.9.18 → libpwizlite 3.0.14 → libpappsomspp.

OHOS adaptations (see notes.md for the full audit trail):
  - core layer built in FULL; gui layer EXCLUDED (patch 0001): the gui
    needs QCustomPlotQt6 which has no package in the ohpcd registry
    (broken chain) — same core-only port pattern as pimcommon 25.12.3.
  - Qt6 components come from three registry packages:
    qtbase/6.11.1 (Core/Gui/Widgets/Xml/Concurrent + Core5Compat from
    qt5compat), qtbase-sql-dbus/6.11.1 (Qt6::Sql for the timsdata Bruker
    vendor module — akonadi precedent), qtdeclarative/6.11.1 (Qt6::Qml
    for the embedded JS engine in core/js_qml — akonadi/actiona
    precedent), qtsvg/6.11.1 (Qt6::Svg, core icon resources).
  - boost/1.84.0 (thread/chrono symbols resolved through libpwizlite's
    vendored objects; iostreams/filesystem archives from the boost
    package itself).
  - Upstream tests: -DMAKE_TESTS=1 registers the Catch2 binary
    catch2-only-tests (41 test source files, 111 TEST_CASEs — see
    test_package/MANIFEST.yml for the per-file breakdown) + the memory
    binary catch2-only-memory. Catch2 3.16.0 from the registry.
  - zlib/1.3.1 non-PIC → static delivery (same as the whole chain).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibpappsomsppConan(ConanFile):
    name = "libpappsomspp"
    version = "0.11.26"
    description = "PAPPSO mass spectrometry C++ foundation library (core)"
    license = "GPL-3.0-or-later"
    homepage = "https://forgemia.inra.fr/pappso/pappsomspp"
    url = "https://forgemia.inra.fr/pappso/pappsomspp"

    package_type = "library"
    topics = ("mass-spectrometry", "proteomics", "pappso", "xtandem", "mzml")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_tests": True,
    }

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 line
        self.requires("qtbase/6.11.1")
        self.requires("qt5compat/6.11.1")
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtsvg/6.11.1")
        # chain prerequisites (published by PRs #11880/#11883/#11887)
        self.requires("liblzf/3.6")
        self.requires("libodsstream/0.9.18")
        self.requires("libpwizlite/3.0.14")
        # others
        self.requires("boost/1.84.0")
        self.requires("zlib/1.3.1")
        self.requires("zstd/1.5.7")
        self.requires("sqlite3/3.53.4")

    def build_requirements(self):
        if self.options.with_tests:
            self.tool_requires("catch2/3.16.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        src = self.conan_data["sources"][self.version]
        get(self, **src, strip_root=True)

    def generate(self):
        # libodsstream headers are consumed as <odsstream/xxx.h> but the
        # package installs them flat under include/odsstream (its own
        # INTERFACE include); add the package include root as a global
        # -isystem so pappsomspp sources resolve the prefix form.
        ods = self.dependencies.get("libodsstream")
        if ods:
            existing = self.conf.get("tools.build:cxxflags")
            flags = list(existing) if isinstance(existing, list) else (
                [existing] if existing else []
            )
            flags.append("-isystem " + os.path.join(ods.package_folder, "include"))
            self.conf.define("tools.build:cxxflags", flags)

        deps = CMakeDeps(self)
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.set_property("zstd", "cmake_file_name", "Zstd")
        deps.set_property("zstd", "cmake_target_name", "Zstd::Zstd")
        deps.set_property("sqlite3", "cmake_file_name", "SQLite3")
        deps.set_property("sqlite3", "cmake_target_name", "SQLite3::SQLite3")
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["MAKE_TESTS"] = "ON" if self.options.with_tests else "OFF"
        # gui layer excluded (QCustomPlotQt6 unavailable) — see patch 0001.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_PLATFORM_USES_PATH_WHEN_NO_SONAME"] = "1"

        # Qt component packages: wire their cmake dirs (qtbase & friends
        # use cmake_find_mode=none; akonadi/actiona precedent).
        lines = []
        qtpkgs = []
        for name in ("qtbase", "qt5compat", "qtbase-sql-dbus",
                     "qtdeclarative", "qtsvg"):
            dep = self.dependencies.get(name)
            if dep and dep.package_folder:
                qtpkgs.append(dep.package_folder)
        for pkg in qtpkgs:
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
        if qtpkgs:
            lines.append(
                "set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH \"" +
                ";".join(f"{p}/lib/cmake" for p in qtpkgs) + "\")"
            )
        # libodsstream ships the vendored-Qt6 QuaZip config under its
        # lib/cmake/QuaZip-Qt6 — put the package's lib/cmake on the prefix
        # path so find_package(QuaZip-Qt6 CONFIG) resolves.
        ods = self.dependencies.get("libodsstream")
        if ods and ods.package_folder:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{os.path.join(ods.package_folder, "lib", "cmake")}")'
            )
        catch2 = self.dependencies.build.get("catch2")
        if catch2:
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{catch2.package_folder}")')
        # The prerequisite chain packages ship their own configs
        # (PwizLite/OdsStream/liblzf conan CMakeDeps configs land in the
        # generators folder).
        lines.insert(0, f'list(PREPEND CMAKE_PREFIX_PATH "{self.generators_folder}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        cmake = CMake(self)
        with runtime_env.vars(self).apply():
            cmake.configure()
            cmake.build()
            if self.options.with_tests:
                # ctest needs the dependency lib dirs at runtime (Qt .so);
                # wrap with the runtime env (libodsstream precedent).
                with runtime_env.vars(self).apply():
                    self.run(
                        "ctest --test-dir '" + self.build_folder + "' --output-on-failure"
                    )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "PappsoMSpp")
        self.cpp_info.set_property("cmake_target_name", "PappsoMSpp::Core")
        self.cpp_info.libs = ["pappsomspp-core"]
        self.cpp_info.requires = [
            "qtbase::qtbase", "qt5compat::qt5compat",
            "qtbase-sql-dbus::qtbase-sql-dbus", "qtdeclarative::qtdeclarative",
            "qtsvg::qtsvg", "liblzf::liblzf", "libodsstream::libodsstream",
            "libpwizlite::libpwizlite", "boost::boost", "zlib::zlib",
            "zstd::zstd", "sqlite3::sqlite3",
        ]
