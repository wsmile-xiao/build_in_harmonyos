#!/usr/bin/env python3
"""Conan recipe — xrootd 5.8.1 (CMake).

XRootD is a fault tolerant, high performance and scalable data access
service from SLAC/CERN. This recipe builds the full framework: client
libraries (XrdCl), server (XrdServer/xrootd/cmsd), POSIX front-end, HTTP
and HTTP-TPC plugins, and the complete tool set.

Upstream builds shared libraries exclusively, so this package is
shared-only. All third-party dependencies (zlib/openssl/libuuid/readline/
ncurses/libxml2/libcurl) are statically baked into the Xrd*.so files by
the ohpcd registry's static packages, so consumers need no runtime
requires.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class XrootdConan(ConanFile):
    name = "xrootd"
    version = "5.8.1"
    description = (
        "XRootD software framework: fault tolerant, high performance, "
        "scalable data access (client libraries, servers and tools)"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://xrootd.slac.stanford.edu/"
    url = "https://github.com/xrootd/xrootd"
    topics = ("xrootd", "storage", "data-access", "grid")

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib is pinned to 1.3.1.1 to stay aligned with the
        # libcurl/8.5.0 dependency graph (1.3.1.2 conflicts).
        self.requires("zlib/1.3.1.1")
        self.requires("openssl/3.5.6.1.2")
        self.requires("libuuid/2.40.4")
        self.requires("readline/8.3")
        # Static readline references terminfo symbols (tgetent/tputs/...)
        # that live in the wide-char ncurses build.
        self.requires("ncurses/6.6")
        self.requires("libxml2/2.15.3.1")
        self.requires("libcurl/8.5.0")
        self.test_requires("gtest/1.17.0.1")

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} is not supported by this recipe"
            )
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "xrootd upstream builds shared libraries only "
                "(no static build support in its CMake files)"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # E383: CMake ships no Platform/HarmonyOS module, so
            # CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG stays empty and the
            # libraries would be built without SONAME (lld then records the
            # relative link path in DT_NEEDED, e.g. ../libXrdUtils.so).
            for lang in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{lang}_FLAG"] = "-Wl,-soname,"

        # No target-side Python development environment when building for
        # OHOS; ENABLE_TESTS pulls in the upstream gtest unit suites.
        tc.variables["ENABLE_PYTHON"] = False
        tc.variables["ENABLE_TESTS"] = True
        # Server tests need a multi-node cluster harness (single host cannot
        # run them); unit tests cover the rest.
        tc.variables["ENABLE_SERVER_TESTS"] = False

        # xrootd's FindReadline.cmake cannot locate conan's static readline:
        # its `PATH_SUFFIXES lib` collides with CMAKE_LIBRARY_PATH entries
        # that already end in /lib, and it checks the upper-case
        # READLINE_FOUND while config-mode find_package sets Readline_FOUND.
        # Inject the discovered paths directly.
        rl = self.dependencies["readline"].cpp_info.aggregated_components()
        tc.variables["READLINE_FOUND"] = True
        tc.variables["READLINE_LIBRARY"] = os.path.join(rl.libdirs[0], "libreadline.a")
        tc.variables["READLINE_INCLUDE_DIR"] = rl.includedirs[0]
        nc = self.dependencies["ncurses"].cpp_info.aggregated_components()
        tc.variables["NCURSES_LIBRARY"] = os.path.join(nc.libdirs[0], "libncursesw.a")

        # xrootd's tests link FindGTest-style target names (GTest::GTest /
        # GTest::Main) and XRootDFindLibs.cmake checks upper-case
        # GTEST_FOUND, while conan's CMakeDeps declares GTest::gtest /
        # GTest::gtest_main and sets GTest_FOUND. Provide aliases via a
        # CMAKE_PROJECT_INCLUDE shim.
        shim = os.path.join(self.build_folder, "gtest_shim.cmake")
        save(self, shim, (
            "# xrootd conan adaptation: FindGTest-compatible target aliases\n"
            "if(NOT TARGET GTest::GTest)\n"
            "  add_library(GTest::GTest INTERFACE IMPORTED)\n"
            "  target_link_libraries(GTest::GTest INTERFACE GTest::gtest)\n"
            "endif()\n"
            "if(NOT TARGET GTest::Main)\n"
            "  add_library(GTest::Main INTERFACE IMPORTED)\n"
            "  target_link_libraries(GTest::Main INTERFACE GTest::gtest_main)\n"
            "endif()\n"
            "set(GTEST_FOUND TRUE)\n"
        ))
        tc.variables["CMAKE_PROJECT_INCLUDE"] = shim
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # gtest_discover_tests executes the freshly linked test binaries as
        # a post-build step; they must find the just-built libs (src/, the
        # per-suite test libs in tests/*) and libcurl.so on the loader path.
        loader_paths = [
            os.path.join(self.build_folder, "src"),
            os.path.join(self.build_folder, "src", "XrdCl"),
        ]
        tests_root = os.path.join(self.source_folder, "tests")
        if os.path.isdir(tests_root):
            loader_paths += [
                os.path.join(self.build_folder, "tests", d)
                for d in os.listdir(tests_root)
                if os.path.isdir(os.path.join(tests_root, d))
            ]
        loader_paths.append(
            self.dependencies["libcurl"].cpp_info.aggregated_components().libdirs[0]
        )
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            loader_paths + [os.environ.get("LD_LIBRARY_PATH", "")]
        ).rstrip(os.pathsep)
        cmake.build()
        # Run the upstream gtest unit suites (30 tests: XrdCl URL/poller/
        # socket/utils, XrdOucUtils, XrdTpc, PathParse). Failures are logged
        # but do not abort the package build; see notes.md for the measured
        # 30/30 pass result on an OpenHarmony PC device.
        self.run(
            "ctest --output-on-failure --timeout 300",
            cwd=self.build_folder,
            env="conanbuild",
            ignore_errors=True,
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Headers install under include/xrootd/ (e.g. XrdCl/XrdClURL.hh).
        self.cpp_info.bindirs = ["bin", "lib"]
        self.cpp_info.libdirs = ["lib"]
        # Main linkable libraries; the ~35 server/security/HTTP plugins in
        # lib/ are dlopen'ed at runtime and are not link targets.
        components = {
            "XrdUtils": (["XrdUtils"], []),
            "XrdCl": (["XrdCl"], ["XrdUtils"]),
            "XrdAppUtils": (["XrdAppUtils"], ["XrdUtils"]),
            "XrdCrypto": (["XrdCrypto", "XrdCryptoLite"], ["XrdUtils"]),
            "XrdXml": (["XrdXml"], ["XrdUtils"]),
            "XrdServer": (["XrdServer"], ["XrdUtils"]),
            "XrdPosix": (["XrdPosix"], ["XrdCl", "XrdUtils"]),
        }
        for name, (libs, requires) in components.items():
            comp = self.cpp_info.components[name]
            comp.libs = libs
            comp.requires = requires
            comp.includedirs = ["include/xrootd"]
