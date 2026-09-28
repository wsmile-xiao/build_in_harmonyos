#!/usr/bin/env python3
"""Conan recipe for libkolabxml 1.2.1 on HarmonyOS PC.

libkolabxml is the Kolab XML Format library used by KDE PIM
(serialization/deserialization of Kolab v3 XML: events, contacts, notes,
todos, journals, configurations, freebusy, files).

OHOS-specific adaptations:
  - XSD toolchain (CodeSynthesis XSD 4.0.0): the xsdcxx code generator and
    the xsdbin schema compiler are host tools that cannot run on the
    cross-compile CI workers. The C++/Tree bindings are pre-generated
    offline with ``xsdcxx cxx-tree --std c++11`` (patches/bindings) and the
    compiled grammar array is pre-generated with xsdbin
    (patches/kolabformat-xcal-schema.cxx). The header-only libxsd runtime
    is shipped in patches/libxsd. CMake picks them up when xsdcxx is not
    found (patches 0001/0002).
  - std::auto_ptr -> std::unique_ptr: the 2014-era sources rely on
    std::auto_ptr (removed in C++17). All occurrences are replaced with
    std::unique_ptr plus explicit std::move at ownership-transfer call
    sites (patches 0003-0006).
  - boost::thread_specific_ptr -> C++11 thread_local: the boost/1.90.0
    conan package ships no compiled boost_thread library; thread_local
    provides the same thread-local storage semantics (patches 0007/0008).
  - boost::thread -> std::thread in the upstream conversiontest
    (patch 0009), same reason as above.
  - UUID: boost >= 1.43 provides header-only boost::uuid, the ossp-uuid
    system library is not required.
  - Upstream tests are built and executed locally (-o build_tests=True:
    BUILD_TESTS=ON + QT5_BUILD=TRUE with qt5/5.15.19 + ecm/6.20.0) — five
    test executables, 84 test functions, all passing (see notes.md and
    reports/upstream-tests-evidence.txt). The default build_tests=False
    keeps qt5 out of the CI dependency graph: the qt5/5.15.19 prebuilt in
    the ohpcd registry is keyed to zlib/1.3.1 while libcurl needs
    zlib/1.3.1.1, and force-overriding zlib changes the qt5 package id
    (full Qt source build that the CI sandbox cannot fork).

Dependencies (default): xerces-c/3.2.5, boost/1.90.0, libcurl/8.5.0
(zlib/1.3.1.1 via libcurl). With -o build_tests=True additionally
qt5/5.15.19 + ecm/6.20.0 + zlib/1.3.1.1 force override.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, copy


class LibkolabxmlConan(ConanFile):
    name = "libkolabxml"
    version = "1.2.1"
    description = "Kolab XML Format library (KDE PIM): serialization of Kolab v3 XML"
    license = "LGPL-3.0-only"  # COPYING.lgplv3 (dual apachev2/lgplv3 per COPYING)
    homepage = "https://gitlab.matrix.org/mirror/libkolabxml"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "build_tests": [True, False],
    }
    # CI workers build with the default options: the upstream Qt5Test-based
    # tests need qt5/5.15.19 whose prebuilt binary in the ohpcd registry is
    # keyed to zlib/1.3.1, conflicting with libcurl's zlib/1.3.1.1 (the
    # force-override would change the qt5 package id and trigger a full Qt
    # source build that the CI sandbox cannot fork). The 84 upstream test
    # functions were executed locally (see notes.md and reports/) and the
    # conan test_package round-trip always runs.
    default_options = {
        "shared": True,
        "build_tests": False,
    }

    def export_sources(self):
        # Patches (declared in conandata.yml) + pre-generated XSD bindings,
        # pre-compiled schema array and the header-only libxsd runtime.
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        self.requires("xerces-c/3.2.5")
        self.requires("boost/1.90.0", transitive_headers=True)
        self.requires("libcurl/8.5.0")
        # qt5 is only needed to build/execute the upstream tests locally
        if self.options.build_tests:
            self.requires("qt5/5.15.19")
            # ECM is an arch-independent CMake module collection; declared as
            # a host requirement so CMakeDeps exposes ECMConfig.cmake to
            # find_package(ECM ... NO_MODULE) in tests/CMakeLists.txt.
            self.requires("ecm/6.20.0")
            # Unify zlib across the local test graph: qt5 declares zlib/1.3.1,
            # libcurl needs zlib/1.3.1.1 (local builds only — the override
            # changes the qt5 package id, so it must never hit the CI graph).
            self.requires("zlib/1.3.1.1", force=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x needs this for the 2.8.5-era cmake_minimum_required
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # libxsd C++11 mode: auto_ptr -> unique_ptr (see xsd/cxx/config.hxx)
        # XSD_CXX11_TEMPLATE_ALIAS/NULLPTR are normally derived from
        # __GNUC__ >= 4.7; clang-on-OHOS masquerades as GCC 4.2, so define
        # them explicitly.
        tc.variables["CMAKE_CXX_FLAGS"] = (
            "-DXSD_CXX11 -DXSD_CXX11_TEMPLATE_ALIAS -DXSD_CXX11_NULLPTR"
        )
        tc.variables["BUILD_TESTS"] = "ON" if self.options.build_tests else "OFF"
        tc.variables["BUILD_UTILS"] = "OFF"
        tc.variables["QT5_BUILD"] = "ON" if self.options.build_tests else "OFF"
        tc.generate()
        # Generate CMakeDeps files for all requirements (ECM/Boost/CURL/ZLIB
        # config files consumed by the upstream CMake find_package calls).
        deps = CMakeDeps(self)
        deps.generate()

    def _qt5_prefix_path(self):
        # qt5/5.15.19 ships upstream Qt5 cmake config files in lib/cmake
        # (Qt5CoreConfig.cmake etc.) that CMakeDeps does not generate from
        # component properties. Return the directory for -DCMAKE_PREFIX_PATH.
        if not self.options.build_tests:
            return None
        qt5 = self.dependencies.get("qt5")
        if not qt5:
            return None
        qt5_cmake = os.path.join(qt5.package_folder, "lib", "cmake")
        return qt5_cmake if os.path.isdir(qt5_cmake) else None

    def build(self):
        # The pre-generated XSD bindings, the pre-compiled schema array and
        # the header-only libxsd runtime are exported next to the patches
        # (flattened into the source folder root by exports_sources) and
        # copied into the source tree, where the patched CMakeLists picks
        # them up at ${CMAKE_SOURCE_DIR}/{bindings,libxsd,...}.
        src_patches = os.path.join(self.source_folder, "patches")
        for entry in ("bindings", "libxsd"):
            src = os.path.join(src_patches, entry)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=os.path.join(self.source_folder, entry))
        for entry in ("kolabformat-xcal-schema.cxx", "kolabformat-xcal-schema.hxx"):
            src = os.path.join(src_patches, entry)
            if os.path.isfile(src):
                copy(self, entry, src=src_patches, dst=self.source_folder)

        apply_conandata_patches(self)
        cmake = CMake(self)
        qt5_prefix = self._qt5_prefix_path()
        if qt5_prefix:
            self._fix_qt5_mkspecs_symlink(qt5_prefix)
            # Passed on the command line (after the toolchain include) so it
            # is available to find_package(Qt5Core/Qt5Test) without
            # overriding the CMAKE_PREFIX_PATH entries conan_toolchain
            # prepends for the CMakeDeps generators folder.
            cmake.configure(cli_args=[f"-DCMAKE_PREFIX_PATH={qt5_prefix}"])
        else:
            cmake.configure()
        cmake.build()

    def _fix_qt5_mkspecs_symlink(self, qt5_lib_cmake):
        # qt5/5.15.19's Qt5CoreConfigExtrasMkspecDir.cmake references the
        # build-time "../b/mkspecs" path relative to the package folder.
        # Create a b/mkspecs symlink next to the package dir so
        # find_package(Qt5Core) succeeds on clean CI workers too.
        pkg_dir = os.path.dirname(os.path.dirname(qt5_lib_cmake))  # <pkg>/lib/cmake -> <pkg>
        base = os.path.dirname(pkg_dir)
        mkspecs_src = os.path.join(pkg_dir, "mkspecs")
        b_dir = os.path.join(base, "b")
        link = os.path.join(b_dir, "mkspecs")
        if os.path.isdir(mkspecs_src) and not os.path.exists(link):
            try:
                os.makedirs(b_dir, exist_ok=True)
                os.symlink(mkspecs_src, link)
                self.output.info(f"created qt5 mkspecs symlink: {link}")
            except OSError as e:
                self.output.warning(f"could not create qt5 mkspecs symlink: {e}")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["kolabxml"]
        self.cpp_info.set_property("cmake_file_name", "Libkolabxml")
        self.cpp_info.set_property("cmake_target_name", "Libkolabxml::Libkolabxml")
        # xerces-c/boost/curl are static/private deps of the shared library;
        # they are resolved via the conan runfiles/LD_LIBRARY_PATH.
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread"]
