#!/usr/bin/env python3
"""Conan recipe for libcsys 5.0.0 on HarmonyOS PC.

libcsys (CuboCore) is a small C++/Qt6 library that reports live system
resource information (CPU, memory, disks, network, storage, battery, power)
through the ``csys/*.h`` public headers and produces ``libcsys.so``.  It is a
plain Qt6 CMake consumer::

    find_package(Qt6Core REQUIRED)
    find_package(Qt6Network REQUIRED)
    find_package(Qt6DBus REQUIRED)
    target_link_libraries(csys Qt6::Core Qt6::DBus Qt6::Network)

OHOS-specific adaptations
-------------------------
* ``qtbase-sql-dbus/6.11.1`` is required instead of ``qtbase/6.11.1``: the
  latter is built with ``FEATURE_dbus=OFF`` and therefore cannot provide the
  Qt6DBus module that libcsys links against.  qtbase-sql-dbus ships the full
  Qt6 ``Qt6Config.cmake`` set and is packaged with ``cmake_find_mode=none``.
* Because that dependency exposes no CMakeDeps find-file, ``CMakeDeps`` never
  writes ``conan_cmakedeps_paths.cmake``; the ``generate()`` step therefore
  writes it by hand so the toolchain prepends qtbase's ``lib/cmake`` to
  ``CMAKE_PREFIX_PATH`` (the same technique used by kdbusaddons/6.14.0).
* CMake ships no ``Platform/HarmonyOS`` module, so ``UNIX`` and
  ``CMAKE_SHARED_LIBRARY_SONAME_*_FLAG`` stay unset and CMake would neither
  version the library nor emit ``-Wl,-soname``.  The flags are provided
  explicitly so the package contains the ``libcsys.so -> libcsys.so.5 ->
  libcsys.so.5.0.0`` chain with a real ``DT_SONAME`` (required by the CI L5
  SONAME gate).
* ``patches/0001-fix-runtime-crashes.patch`` fixes three upstream defects that
  are exposed on HarmonyOS: ``InfoManager::update()`` indexed an empty CPU
  frequency list (SIGSEGV because ``/proc/cpuinfo`` on OHOS has no ``cpu MHz``
  field), ``Power::~Power()`` used the inverted loop condition
  ``while (providers.empty())`` and called ``takeFirst()`` on an empty list
  (SIGSEGV whenever no systemd/ConsoleKit D-Bus provider is present), and
  ``SystemInfo::getHostname()`` passed the ``gethostname()`` return value (0 on
  success) to ``QString::fromLatin1`` as a length, always yielding "".
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibcsysConan(ConanFile):
    name = "libcsys"
    version = "5.0.0"
    description = "Library for getting system resource information in real time"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.com/cubocore/libcsys"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qtbase/6.11.1 is built with FEATURE_dbus=OFF and provides no Qt6DBus;
        # the qtbase-sql-dbus variant is the one that ships Qt6Core/Qt6DBus/
        # Qt6Network (and Qt6Test).
        self.requires("qtbase-sql-dbus/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # CMake has no Platform/HarmonyOS module: UNIX and the soname flags
        # stay unset, so CMake neither versions the shared library nor passes
        # -Wl,-soname.  Provide them explicitly to obtain the
        # libcsys.so -> libcsys.so.5 -> libcsys.so.5.0.0 chain + DT_SONAME.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        qtbase = self.dependencies.get("qtbase-sql-dbus")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase-sql-dbus sets cmake_find_mode=none, so CMakeDeps does not
            # emit conan_cmakedeps_paths.cmake and CMAKE_PREFIX_PATH would miss
            # qtbase's lib/cmake dir, breaking find_package(Qt6Core).  Write the
            # file by hand (same trick as kdbusaddons/6.14.0) so the toolchain
            # picks up the real Qt6Config.cmake chain.
            lines = [
                'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")',
            ]
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream ships no test suite: CMakeLists.txt has no enable_testing()/
        # add_test(), meson.build has no test() and there is no tests/ dir
        # (see test_package/MANIFEST.yml for the inventory evidence).  Run ctest
        # explicitly so the build log carries the ctest evidence required by CI
        # L1c.  ctest is invoked directly rather than through CMake.test()
        # because the upstream project registers no CTest test: there is no
        # "test" build target for CMake.test() to call.  With zero registered
        # tests ctest prints "No tests were found!!!" and exits 0.
        self.run("ctest --output-on-failure", cwd=self.build_folder,
                 ignore_errors=True)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Upstream installs only csys.pc + the csys/*.h headers, no CMake
        # config package.  Mirror qtbase-sql-dbus and disable CMakeDeps
        # generation; consumers use pkg-config or link the library directly.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.libs = ["csys"]
        self.cpp_info.includedirs = ["include"]
