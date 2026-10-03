#!/usr/bin/env python3
"""Conan recipe - mtxclient 0.10.1 (CMake).

mtxclient is the Matrix client-server API library used by the Nheko desktop
client. Adapted to HarmonyOS PC (aarch64, musl, clang 15, native build).

Build notes for OHOS:

* Native build (build == host == OHOS/aarch64). The Conan package dependency
  folders therefore live on the same machine that compiles, which is what makes
  the PkgConfigDeps route below sound; it would not be for a cross build.
* mtxclient probes four of its dependencies through pkg-config
  (``pkg_check_modules(re2)``, ``libevent_core``, ``libevent_pthreads``,
  ``libcurl``, ``coeurl>=0.3.0``) and the rest through ``find_package`` CONFIG.
  Both ``CMakeDeps`` and ``PkgConfigDeps`` are therefore generated: CMakeDeps
  provides ``OpenSSLConfig.cmake`` / ``olm-config.cmake`` /
  ``nlohmann_json-config.cmake``, PkgConfigDeps regenerates the ``.pc`` files
  whose ``prefix`` points at the real Conan package folders.
* The OHOS images do not ship a system pkg-config, so ``pkgconf`` is taken as a
  build tool and its executable is pinned via ``PKG_CONFIG_EXECUTABLE`` -- that
  is what makes ``find_package(PkgConfig REQUIRED)`` and every
  ``pkg_check_modules`` call resolvable on the device.
* ``toolchain.cmake`` in the upstream tree only sets ``CMAKE_CXX_STANDARD``,
  ``CMAKE_CXX_STANDARD_REQUIRED`` and ``CMAKE_POSITION_INDEPENDENT_CODE``; it
  does not set a compiler or system name, and Conan passes its own toolchain
  file through ``-DCMAKE_TOOLCHAIN_FILE=`` on the command line, which wins over
  the ``CACHE`` assignment in the project's ``CMakeLists.txt``. No patch needed.
* ``re2`` is a real link dependency (``lib/structs/pushrules.cpp`` uses
  ``re2::RE2`` for Matrix push-rule pattern matching); it is not dropped.
* Upstream splits its gtest suite into a network half (needs a live Synapse
  homeserver plus the ``.ci/synapse`` container) and an offline half
  (``suite: nonetwork`` in ``tests/meson.build``). Only the offline half can run
  in a package build; the six network binaries are built but not executed here.
* Two portability patches in ``patches/``: the olm package name is lowercased
  (``olm-config.cmake`` / ``olm::olm`` is what ConanDeps produces), and the
  fifteen test targets link the renamed ``GTest::gtest`` / ``GTest::gtest_main``
  because gtest 1.14 removed the capitalized ``GTest::GTest`` / ``GTest::Main``
  names that mtxclient 0.10.1 still uses. Both are documented in full in the
  patch headers.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)

# Upstream `tests/meson.build` marks these six binaries as `suite: network`;
# every other test target is `suite: nonetwork` and runs without a homeserver.
# ctest names come from the `add_test()` calls at the bottom of CMakeLists.txt.
NETWORK_TESTS = [
    "BasicConnectivity",
    "ClientAPI",
    "MediaAPI",
    "Encryption",
    "Devices",
    "Pushrules",
]


class MtxclientConan(ConanFile):
    name = "mtxclient"
    version = "0.10.1"
    description = ("Client API library for Matrix, used by the Nheko desktop "
                   "client")
    license = "MIT"
    homepage = "https://github.com/Nheko-Reborn/mtxclient"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("matrix", "client", "http", "e2ee", "olm")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    # Both generators are mandatory. CMakeDeps supplies the find_package CONFIG
    # files (OpenSSLConfig.cmake, olm-config.cmake, nlohmann_json-config.cmake,
    # spdlog-config.cmake, coeurl-config.cmake); PkgConfigDeps regenerates the
    # .pc files consumed by upstream's pkg_check_modules calls. Without this
    # attribute generate() emits only the Conan toolchain and configuration dies
    # at find_package(olm) with "Could not find a package configuration file".
    generators = "CMakeDeps", "PkgConfigDeps"
    options = {
        "shared": [True, False],
        "with_olm": [True, False],
    }
    default_options = {
        "shared": True,
        "with_olm": True,
    }

    def export_sources(self):
        export_conandata_patches(self)
        # ctest exclusion list, copied into the build tree by build().
        copy(self, "CTestCustom.cmake.in", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def requirements(self):
        # Public headers include <olm/olm.h>, <nlohmann/json_fwd.hpp> and
        # <coeurl/headers.hpp>, so all three are direct requirements.
        #
        # openssl/olm are also link-visible (OpenSSL::Crypto/SSL, Olm::Olm are
        # PUBLIC on the exported target); spdlog is linked PUBLIC by upstream.
        # libcurl/libevent/re2 are probed through pkg-config by CMakeLists.txt
        # itself, while coeurl is a public-header + public-link dependency.
        self.requires("openssl/3.5.6.1")
        if self.options.with_olm:
            self.requires("olm/3.2.16")
        self.requires("nlohmann_json/3.12.0")
        self.requires("coeurl/0.3.2")
        self.requires("re2/2024-04-01")
        self.requires("libcurl/8.5.0")
        self.requires("libevent/2.1.13")
        self.requires("spdlog/1.17.0")
        # spdlog 1.17.0 is compiled with SPDLOG_FMT_EXTERNAL and its static
        # archive carries inline spdlog templates with undefined fmt symbols;
        # the ohpcd spdlog package does not propagate fmt::fmt to consumers, so
        # declare the same version spdlog resolves to (same doctrine as coeurl).
        self.requires("fmt/12.2.0")

    def build_requirements(self):
        # Upstream builds its test suite unconditionally when BUILD_LIB_TESTS is
        # ON, and the portability patch makes those targets link GTest::gtest /
        # GTest::gtest_main.
        self.test_requires("gtest/1.17.0")
        # The OHOS rootfs/hnp tree has no pkg-config or pkgconf binary; the
        # upstream CMakeLists.txt needs five dependencies through
        # pkg_check_modules, so ship the implementation as a build tool.
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # mtxclient requires C++20: include/mtx/identifiers.hpp declares
        # `auto operator<=>(User const &other)` and returns std::strong_ordering,
        # which only parses as the three-way comparison operator under C++20.
        # The repo profile pins compiler.cppstd=17, and CMakeToolchain's
        # CppStdBlock emits that as a *normal* CMake variable
        # (`set(CMAKE_CXX_STANDARD 17)`), which a project-level cache variable
        # cannot override -- CMake's normal variable wins. Raising the setting
        # here is what actually makes the toolchain emit `-std=c++20`
        # (verified on device: C++17 build dies with
        # "'operator<=' cannot be the name of a variable or data member").
        self.settings.compiler.cppstd = "20"
        tc = CMakeToolchain(self)
        # Never use Hunter / FetchContent: every dependency is a Conan package.
        tc.cache_variables["HUNTER_ENABLED"] = False
        tc.cache_variables["USE_BUNDLED_OPENSSL"] = False
        tc.cache_variables["USE_BUNDLED_OLM"] = not self.options.with_olm
        tc.cache_variables["USE_BUNDLED_JSON"] = False
        tc.cache_variables["USE_BUNDLED_RE2"] = False
        tc.cache_variables["USE_BUNDLED_LIBEVENT"] = False
        tc.cache_variables["USE_BUNDLED_LIBCURL"] = False
        tc.cache_variables["USE_BUNDLED_SPDLOG"] = False
        tc.cache_variables["USE_BUNDLED_COEURL"] = False
        tc.cache_variables["USE_BUNDLED_GTEST"] = False
        tc.cache_variables["ASAN"] = False
        tc.cache_variables["COVERAGE"] = False
        tc.cache_variables["IWYU"] = False
        # examples/ is a set of standalone bots; not part of the library package.
        tc.cache_variables["BUILD_LIB_EXAMPLES"] = False
        # C++20 comes from raising compiler.cppstd above, which makes the Conan
        # toolchain itself emit `-std=c++20`; a cache variable here would only
        # trip CppStdBlock's variable watch without changing the outcome.
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.cache_variables["BUILD_LIB_TESTS"] = True
        # The upstream CMakeLists.txt has no GTest discovery and no test labels,
        # so the offline subset is selected at ctest time from NETWORK_TESTS.
        pkg_config = self._pkg_config_executable()
        if pkg_config:
            tc.cache_variables["PKG_CONFIG_EXECUTABLE"] = pkg_config
        # Point find_package(GTest) at the gtest package's own CMake config.
        # CMakeDeps only exposes `gtest::gtest` (the gtest recipe declares
        # cpp_info.libs = ["gtest"] and no cmake_target_name for gtest_main),
        # while the package ships GTestConfig.cmake exporting both
        # GTest::gtest and GTest::gtest_main -- the two targets the portability
        # patch in patches/0002 links. Same doctrine as abseil/20260526.
        gtest = self.dependencies.get("gtest")
        if gtest and gtest.package_folder:
            tc.variables["GTest_DIR"] = os.path.join(
                gtest.package_folder, "lib", "cmake", "GTest").replace("\\", "/")
        # The offline test subset is selected through the standard CMake
        # mechanism rather than ctest command-line flags: CMake.helper's
        # test() runs `cmake --build --target test`, which forwards no extra
        # options, so `ctest -E ...` cannot be passed through it. ctest reads
        # CTestCustom.cmake from the build directory, so build() copies
        # CTEST_CUSTOM_TESTS_IGNORE there; CTestCustom.cmake.in is the upstream
        # spelling of the same file and kept in sync for anyone building by hand.
        #
        # CMAKE_CTEST_COMMAND is pinned to the ctest next to cmake: the device
        # keeps cmake in $HOME/usr/local/bin, which is not on the default PATH
        # used by the generated Makefile's `test` target.
        cmake_dir = os.path.dirname(self.conf.get("tools.cmake:cmake_program",
                                                  default="") or "")
        ctest = shutil.which("ctest") or "ctest"
        if cmake_dir:
            ctest = os.path.join(cmake_dir, "ctest")
        tc.cache_variables["CMAKE_CTEST_COMMAND"] = ctest
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # ctest picks this up from the build directory; it carries the list of
        # network test cases that must not run without a Synapse homeserver.
        # The name must be exactly CTestCustom.cmake (the .in spelling of the
        # same content is the template form CTestCustom.cmake.in).
        copy(self, "CTestCustom.cmake.in",
             src=self.export_sources_folder,
             dst=self.build_folder,
             keep_path=False)
        _custom = os.path.join(self.build_folder, "CTestCustom.cmake.in")
        if os.path.exists(_custom):
            os.replace(_custom, os.path.join(self.build_folder,
                                             "CTestCustom.cmake"))
        cmake.build()
        # ── Upstream official tests ──
        # ctest is invoked explicitly with env="conanrun" rather than through
        # cmake.test(): the latter runs `cmake --build --target test`, which --
        # unlike cmake.build() -- applies no run environment, so the freshly
        # linked test binaries fail with
        #   "Error loading shared library libmatrix_client.so / libspdlog.so ..."
        # This is the repo-wide convention for ctest (see abseil, astc-encoder).
        # The six network cases are excluded through CTestCustom.cmake, which
        # ctest reads from the build directory; CMAKE_CTEST_COMMAND above pins
        # the ctest that sits next to this device's cmake.
        #
        # patches/0003 gives the library DT_SONAME libmatrix_client.so.0.10.1,
        # which is what the test binaries record in DT_NEEDED. CMake on OHOS
        # does not create the matching versioned name in the build tree (only
        # the plain libmatrix_client.so exists), so the loader cannot resolve
        # the dependency. Provide the alias here.
        _so = os.path.join(self.build_folder, "libmatrix_client.so")
        _soname = os.path.join(self.build_folder,
                               "libmatrix_client.so.%s" % self.version)
        if os.path.exists(_so) and not os.path.lexists(_soname):
            os.symlink("libmatrix_client.so", _soname)
            self.output.info("created build-tree soname alias %s"
                             % os.path.basename(_soname))
        if can_run(self):
            # conanrun covers the dependency libs, but not the shared library
            # this recipe just built, so add the build folder explicitly.
            run_env = Environment()
            run_env.prepend_path("LD_LIBRARY_PATH", self.build_folder)
            with run_env.vars(self).apply():
                self.run("ctest --output-on-failure", cwd=self.build_folder,
                         env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream installs the static/shared lib and the full public header
        # tree. patches/0003 gives the library DT_SONAME
        # libmatrix_client.so.<version>, but CMake on OHOS applies neither
        # VERSION nor SOVERSION: the install step writes only the plain
        # libmatrix_client.so and never the versioned name. The dynamic loader
        # resolves consumers' DT_NEEDED (which records the soname) by file name,
        # so the package must also contain a file under the soname -- otherwise
        # every consumer fails with
        #   "Error relocating ...: symbol not found" / error 127.
        # Ship both names as real files: CMake would normally do this with a
        # symlink, and HMDFS does not track symlinks reliably (E050).
        # E274 records the same missing-soname failure mode.
        lib = os.path.join(self.package_folder, "lib")
        plain = os.path.join(lib, "libmatrix_client.so")
        versioned = os.path.join(lib, "libmatrix_client.so.%s" % self.version)
        if os.path.exists(plain) and not os.path.lexists(versioned):
            shutil.copy2(plain, versioned)
            self.output.info("materialised soname file %s"
                             % os.path.basename(versioned))
        elif not os.path.exists(plain):
            self.output.info("no libmatrix_client.so produced (static build?)")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "MatrixClient")
        self.cpp_info.set_property("cmake_target_name", "MatrixClient::MatrixClient")
        self.cpp_info.set_property("pkg_config_name", "mtxclient")
        self.cpp_info.libs = ["matrix_client"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
        # Public headers reach olm, nlohmann/json, coeurl and (through coeurl)
        # spdlog/curl/event2, so declare the link-visible chain explicitly.
        self.cpp_info.requires = [
            "openssl::openssl",
            "nlohmann_json::nlohmann_json",
            "coeurl::coeurl",
            "re2::re2",
            "libevent::core",
            "libevent::pthreads",
            "libcurl::libcurl",
            "spdlog::spdlog",
            "fmt::fmt",
        ]
        if self.options.with_olm:
            self.cpp_info.requires.append("olm::olm")
        # The packaged spdlog is compiled with SPDLOG_FMT_EXTERNAL (fmt/12.2.0),
        # but its recipe does not re-declare that in cpp_info, so CMakeDeps hands
        # consumers an empty spdlog_DEFINITIONS. Any consumer that includes a
        # public mtxclient header reaches <spdlog/fmt/fmt.h>, which under the
        # default (bundled) configuration looks for
        # <spdlog/fmt/bundled/format.h> -- a header the package does not ship:
        #   fatal error: 'spdlog/fmt/bundled/format.h' file not found
        # Declare the same interface the packaged spdlog was built with, exactly
        # as the coeurl 0.3.2 recipe does.
        self.cpp_info.defines = [
            "SPDLOG_FMT_EXTERNAL",
            "SPDLOG_COMPILED_LIB",
            "SPDLOG_SHARED_LIB",
        ]
        # CMakeDeps (conan 2.29) emits no data for transitive dependencies, so
        # expose every dependency's include/lib dirs on this target too — the
        # same workaround the coeurl 0.3.2 recipe documents.
        for depname in (
            "openssl",
            "olm",
            "nlohmann_json",
            "coeurl",
            "re2",
            "libevent",
            "libcurl",
            "spdlog",
            "fmt",
        ):
            dep = self.dependencies.get(depname)
            if not dep or not dep.package_folder:
                continue
            inc = os.path.join(dep.package_folder, "include")
            if os.path.isdir(inc):
                self.cpp_info.includedirs.append(inc)
            lib = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib):
                self.cpp_info.libdirs.append(lib)
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", lib)
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))

    def _pkg_config_executable(self):
        """Absolute path of the pkg-config implementation to use.

        Preference order:
          1. pkgconf from the tool_requires package (the OHOS images ship no
             pkg-config at all, so this is the normal case on the device),
          2. a pkg-config / pkgconf already on PATH (worker with one installed).
        """
        tool = self.dependencies.build.get("pkgconf")
        if tool and tool.package_folder:
            for name in ("pkgconf", "pkg-config"):
                candidate = os.path.join(tool.package_folder, "bin", name)
                if os.path.exists(candidate):
                    return candidate
        return shutil.which("pkg-config") or shutil.which("pkgconf") or ""

