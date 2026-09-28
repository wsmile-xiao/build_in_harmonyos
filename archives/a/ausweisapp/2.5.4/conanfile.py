#!/usr/bin/env python3
"""Conan recipe for AusweisApp2 2.5.4 (Qt6 CMake GUI application)."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class AusweisappConan(ConanFile):
    name = "ausweisapp"
    version = "2.5.4"
    description = "AusweisApp2 - German eID client (Qt6)"
    license = "EUPL-1.2"
    homepage = "https://www.ausweisapp.bund.de/"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 base with OpenSSL support (harmonyos SSL variant). Force the
        # whole dependency graph onto qtbase/6.11.1.1.1 so Qt modules built
        # against the plain 6.11.1 base are resolved against the SSL variant.
        self.requires(
            "qtbase/6.11.1.1.1",
            override=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        # Qt modules
        self.requires("qtdeclarative/6.11.1", transitive_headers=True, transitive_libs=True)
        # qtwebsockets SSL variant: plain qtwebsockets/6.11.1 (built against the
        # non-SSL qtbase) does not export QWebSocket's SSL API
        # (sslConfiguration/ignoreSslErrors/setSslConfiguration/
        # preSharedKeyAuthenticationRequired/sslErrors), which AusweisApp's
        # ConnectRequest/RemoteWebSocketServerImpl link against.  Build against
        # qtwebsockets/6.11.1.1.1 (same source archive, SSL qtbase contract).
        self.requires("qtwebsockets/6.11.1.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("qtsvg/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qttools/6.11.1", transitive_headers=True, transitive_libs=True)
        # Qt StateMachine / Scxml modules (standalone since Qt 6.11)
        self.requires("qtscxml/6.11.1", transitive_headers=True, transitive_libs=True)
        # Crypto. Must match the openssl version qtbase/6.11.1.1.1 (the SSL
        # variant) was built against (openssl/3.5.6.1); a different revision
        # (e.g. 3.5.6.1.1) creates a version conflict in the dependency graph.
        self.requires("openssl/3.5.6.1", transitive_headers=True, transitive_libs=True)
        # eID / network dependencies
        self.requires("llhttp/9.3.1")
        self.requires("pcsc-lite/2.4.0")
        self.requires("libudev-zero/1.0.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ausweisapp supports Linux and OHOS")

    def configure(self):
        # Upstream requires at least C++20 (cmake/CompilerFlags.cmake).
        if self.settings.compiler.get_safe("cppstd") and str(
            self.settings.compiler.cppstd
        ) not in ("20", "gnu20", "23", "gnu23"):
            self.settings.compiler.cppstd = "20"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Upstream FindPCSC.cmake relies on pkg-config (cmake_pkg_config /
        # pkg_check_modules), which is unreliable for the OHOS toolchain.
        # Rewrite it so the recipe-provided PCSC_INCLUDE_DIR / PCSC_LIBRARY
        # variables create PkgConfig::PCSC directly (a git patch file is not
        # applied because the OHOS patch utility cannot parse it).
        find_pcsc = os.path.join(self.source_folder, "cmake", "FindPCSC.cmake")
        if os.path.isfile(find_pcsc):
            with open(find_pcsc, "w", encoding="utf-8") as f:
                f.write(
                    "if(DEFINED PCSC_INCLUDE_DIR AND DEFINED PCSC_LIBRARY)\n"
                    "\t# HarmonyOS cross-compile: the Conan recipe passes the\n"
                    "\t# pcsc-lite package paths directly (pkg-config unreliable).\n"
                    "\tadd_library(PkgConfig::PCSC INTERFACE IMPORTED)\n"
                    "\tset_target_properties(PkgConfig::PCSC PROPERTIES\n"
                    '\t\tINTERFACE_INCLUDE_DIRECTORIES "${PCSC_INCLUDE_DIR}"\n'
                    '\t\tINTERFACE_LINK_LIBRARIES "${PCSC_LIBRARY}")\n'
                    '\tset(PCSC_LIBRARIES "${PCSC_LIBRARY}")\n'
                    "elseif(UNIX AND NOT APPLE AND NOT CYGWIN)\n"
                    '\tif(CMAKE_VERSION VERSION_LESS "4.1.1")\n'
                    "\t\tfind_package(PkgConfig REQUIRED)\n"
                    "\t\tpkg_check_modules(PCSC REQUIRED IMPORTED_TARGET libpcsclite)\n"
                    "\telse()\n"
                    "\t\tcmake_pkg_config(IMPORT libpcsclite REQUIRED NAME PCSC)\n"
                    "\t\tget_target_property(PCSC_LIBRARIES PkgConfig::PCSC INTERFACE_LINK_LIBRARIES)\n"
                    "\tendif()\n"
                    "\n"
                    "else()\n"
                    "\tadd_library(PkgConfig::PCSC INTERFACE IMPORTED)\n"
                    "\n"
                    "\tif(MINGW OR CYGWIN)\n"
                    "\t\tset(PCSC_LIBRARIES -lwinscard)\n"
                    "\n"
                    "\telseif(MSVC OR CMAKE_CXX_SIMULATE_ID STREQUAL \"MSVC\")\n"
                    "\t\tset(PCSC_LIBRARIES winscard.lib)\n"
                    "\n"
                    "\telseif(APPLE)\n"
                    "\t\tfind_library(PCSC_LIBRARIES PCSC)\n"
                    '\t\tset_target_properties(PkgConfig::PCSC PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "${PCSC_LIBRARIES}/Headers/")\n'
                    "\tendif()\n"
                    "\n"
                    '\tset_target_properties(PkgConfig::PCSC PROPERTIES INTERFACE_LINK_LIBRARIES "${PCSC_LIBRARIES}")\n'
                    "endif()\n"
                    "\n"
                    "include(FindPackageHandleStandardArgs)\n"
                    "find_package_handle_standard_args(PCSC DEFAULT_MSG PCSC_LIBRARIES)\n"
                    "mark_as_advanced(PCSC_LIBRARIES)\n"
                )
        # Upstream cmake/Libraries.cmake only calls find_package(PCSC) from the
        # MINGW / MSVC / MAC / UNIX branches. CMake does not define UNIX for
        # CMAKE_SYSTEM_NAME=HarmonyOS, so on OHOS find_package(PCSC) never runs,
        # the rewritten FindPCSC.cmake above is never loaded, and the
        # PkgConfig::PCSC target is missing when src/card/pcsc links it.
        # Extend the UNIX branch condition to HarmonyOS/OHOS so the PCSC
        # module is loaded and creates PkgConfig::PCSC from the toolchain
        # variables (the inner LINUX/BSD udev detection stays untouched).
        libs_cmake = os.path.join(self.source_folder, "cmake", "Libraries.cmake")
        if os.path.isfile(libs_cmake):
            with open(libs_cmake, "r", encoding="utf-8") as f:
                libs_text = f.read()
            if libs_text.count("elseif(UNIX)") == 1 and "STREQUAL \"OHOS\"" not in libs_text:
                libs_text = libs_text.replace(
                    "elseif(UNIX)",
                    'elseif(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "OHOS" '
                    'OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")',
                )
                with open(libs_cmake, "w", encoding="utf-8") as f:
                    f.write(libs_text)
        # The OpenSSL compatibility probe (try_run of cmake/tests/openssl.cpp)
        # compares QSslSocket::sslLibraryVersionString() with the compile-time
        # OpenSSL_version(OPENSSL_VERSION). The OHOS openssl package is built
        # with no-shared (static .a only), so QtNetwork's dynamic OpenSSL
        # symbol loader cannot resolve a runtime OpenSSL library and the probe
        # always fails (returns 1 for the version check, 2 for the RSA-PSK
        # cipher check) even though Qt and AusweisApp link the very same
        # openssl package (the Conan graph rules out any ABI mismatch). Skip
        # the probe on OHOS/HarmonyOS.
        if os.path.isfile(libs_cmake):
            with open(libs_cmake, "r", encoding="utf-8") as f:
                libs_text = f.read()
            old_probe_cond = "if(LINUX OR BSD)\n\ttry_run(testResult compileResult"
            new_probe_cond = (
                'if((LINUX OR BSD) AND NOT CMAKE_SYSTEM_NAME STREQUAL "OHOS" '
                'AND NOT CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")\n'
                "\ttry_run(testResult compileResult"
            )
            if libs_text.count(old_probe_cond) == 1:
                libs_text = libs_text.replace(old_probe_cond, new_probe_cond)
                with open(libs_cmake, "w", encoding="utf-8") as f:
                    f.write(libs_text)
        # Upstream PcscReader.cpp includes <reader.h> on pcsclite to get
        # CM_IOCTL_GET_FEATURE_REQUEST. On OHOS the userdata filesystem is
        # case-insensitive, so <reader.h> can resolve to the project's own
        # src/card/base/Reader.h instead of the pcsc-lite header, leaving the
        # ioctl macro undefined. pcsclite defines SCARD_CTL_CODE(3400) as
        # 0x42000000 + 3400 (same value the macOS branch hardcodes), so drop
        # the ambiguous include and define the constant directly.
        pcsc_reader = os.path.join(
            self.source_folder, "src", "card", "pcsc", "PcscReader.cpp"
        )
        if os.path.isfile(pcsc_reader):
            with open(pcsc_reader, "r", encoding="utf-8") as f:
                pcsc_reader_lines = f.read().split("\n")
            start = next(
                (i for i, line in enumerate(pcsc_reader_lines)
                 if "PCSCLITE_VERSION_NUMBER" in line),
                None,
            )
            if start is not None:
                end = next(
                    (i for i in range(start, len(pcsc_reader_lines))
                     if pcsc_reader_lines[i].strip() == "#endif"),
                    start,
                )
                replacement = [
                    "#elif defined(Q_OS_WIN)",
                    "//  PC/SC Part 10 v2.02.09 November 2012 - 2.2 GET_FEATURE_REQUEST",
                    "\t#define CM_IOCTL_GET_FEATURE_REQUEST SCARD_CTL_CODE(3400)",
                    "#else",
                    "//  pcsclite / OHOS: SCARD_CTL_CODE(3400) == 0x42000000 + 3400.",
                    "//  The upstream `#include <reader.h>` is omitted because the",
                    "//  case-insensitive OHOS filesystem may resolve it to the",
                    "//  project's own Reader.h; define the ioctl value directly.",
                    "\t#define CM_IOCTL_GET_FEATURE_REQUEST (0x42000000 + 3400)",
                    "#endif",
                ]
                pcsc_reader_lines[start : end + 1] = replacement
                with open(pcsc_reader, "w", encoding="utf-8") as f:
                    f.write("\n".join(pcsc_reader_lines))
        # The dev plugin (built because the recipe forces DESKTOP=ON) uses
        # std::ranges::for_each, which the OHOS clang/libc++ toolchain does not
        # provide; replace it with an equivalent range-for loop.
        dev_plugin = os.path.join(
            self.source_folder, "src", "ui", "dev", "UiPluginDev.cpp"
        )
        if os.path.isfile(dev_plugin):
            with open(dev_plugin, "r", encoding="utf-8") as f:
                dev_plugin_lines = f.read().split("\n")
            start = next(
                (i for i, line in enumerate(dev_plugin_lines)
                 if "std::ranges::for_each(platformFiles" in line),
                None,
            )
            if start is not None:
                end = next(
                    (i for i in range(start, len(dev_plugin_lines))
                     if "});" in dev_plugin_lines[i]),
                    start,
                )
                dev_plugin_lines[start : end + 1] = [
                    "\tfor (QString& s : platformFiles)",
                    "\t{",
                    "\t\ts.prepend(QStringLiteral(\"/\"));",
                    "\t\ts.prepend(selector);",
                    "\t}",
                ]
                with open(dev_plugin, "w", encoding="utf-8") as f:
                    f.write("\n".join(dev_plugin_lines))

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        # qtscxml uses cmake_find_mode=none and ships the upstream Qt6StateMachine /
        # Qt6Scxml config files in its own lib/cmake; expose them explicitly so
        # find_package(Qt6 COMPONENTS StateMachine) resolves on OHOS.
        qtscxml_pkg = self.dependencies["qtscxml"].package_folder
        tc.variables["Qt6StateMachine_DIR"] = os.path.join(
            qtscxml_pkg, "lib", "cmake", "Qt6StateMachine"
        )
        tc.variables["Qt6Scxml_DIR"] = os.path.join(
            qtscxml_pkg, "lib", "cmake", "Qt6Scxml"
        )
        # llhttp is consumed via find_package(llhttp); point CMake at the
        # llhttp-config.cmake shipped in its own lib/cmake/llhttp (the
        # upstream CMakeDeps integration is not used for this dependency).
        llhttp_pkg = self.dependencies["llhttp"].package_folder
        tc.variables["llhttp_DIR"] = os.path.join(
            llhttp_pkg, "lib", "cmake", "llhttp"
        )
        # Expose every Qt component config dir shipped by the conan packages
        # (Qt6Svg, Qt6WebSockets, Qt6Qml, Qt6Quick, Qt6LinguistTools, ...).
        # Qt6Config resolves components via <Component>_DIR, and CMAKE_PREFIX_PATH
        # aggregation is not reliable for Qt6's per-component lookup, so set each
        # directory explicitly.
        for dep_name in (
            "qtbase", "qtdeclarative", "qtwebsockets", "qtsvg",
            "qttools", "qtscxml", "qtshadertools",
        ):
            try:
                pkg = self.dependencies[dep_name].package_folder
            except KeyError:
                continue
            if not pkg:
                continue
            cmake_dir = os.path.join(pkg, "lib", "cmake")
            if not os.path.isdir(cmake_dir):
                continue
            for entry in sorted(os.listdir(cmake_dir)):
                cfg_dir = os.path.join(cmake_dir, entry)
                if os.path.isdir(cfg_dir) and os.path.isfile(
                    os.path.join(cfg_dir, f"{entry}Config.cmake")
                ):
                    tc.variables[f"{entry}_DIR"] = cfg_dir
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        if self.settings.os == "OHOS":
            tc.variables["QT_QMAKE_TARGET_MKSPEC"] = "harmonyos-clang"
            # CMake does not recognize HarmonyOS, so LINUX/DESKTOP stay
            # unset upstream and the card drivers module is skipped; force
            # the desktop reader-detector path (ReaderDetector.h etc.).
            tc.variables["DESKTOP"] = "ON"
            # Helper.cmake only ever *sets* LINUX (never unsets) and uses it
            # to pick platform source files (e.g. SignalHandler_bsd_linux_osx.cpp
            # vs the Windows one). Without UNIX being defined for the unknown
            # HarmonyOS system, every *_linux file is dropped and the app fails
            # to link (undefined SignalHandler::initUnix / ...). Pretending to
            # be Linux reproduces the upstream desktop source selection exactly.
            tc.variables["LINUX"] = "ON"
        # Upstream FindPCSC.cmake (patched) consumes PCSC_INCLUDE_DIR /
        # PCSC_LIBRARY directly on HarmonyOS, bypassing the pkg-config /
        # cmake_pkg_config path that is unreliable for the OHOS toolchain.
        pcsc_pkg = self.dependencies["pcsc-lite"].package_folder
        # pcsc-lite installs winscard.h under include/PCSC/ and its own
        # pkg-config exports `Cflags: -I${includedir}/PCSC`; the upstream
        # PcscUtils.h does `#include <winscard.h>`, so the include dir must
        # point at the PCSC/ subdirectory (not the bare include/ root).
        tc.variables["PCSC_INCLUDE_DIR"] = os.path.join(
            pcsc_pkg, "include", "PCSC"
        ).replace("\\", "/")
        tc.variables["PCSC_LIBRARY"] = os.path.join(
            pcsc_pkg, "lib", "libpcsclite.so"
        ).replace("\\", "/")
        tc.generate()
        VirtualRunEnv(self).generate()

    def _ctest_executable(self):
        for candidate in (
            os.environ.get("CTEST"),
            "/data/service/hnp/bin/ctest",
            "/data/service/hnp/cmake.org/cmake_4.1.2/bin/ctest",
        ):
            if (
                candidate
                and os.path.isfile(candidate)
                and os.access(candidate, os.X_OK)
            ):
                return candidate
        raise ConanInvalidConfiguration("ctest executable was not found")

    def build(self):
        apply_conandata_patches(self)
        # The OHOS SDK lld links against libxml2.so.16 (knowledge E120/E132).
        # CI workers carry an ambient LD_LIBRARY_PATH (e.g. ~/usr/local/lib)
        # that can shadow the SDK's ABI-matched libxml2.so.16, making lld
        # fail at the final link with 'Error loading shared library
        # libxml2.so.16 ... symbol not found'. Prepend the SDK llvm/lib that
        # actually contains libxml2.so.16 so the correct one is found first
        # (same approach as the abseil/abr2gbr recipes).
        build_env = Environment()
        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c") or "clang"
        cc_real = os.path.realpath(cc)
        sdk_lib_path = ""
        for candidate in (
            os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib"),
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
        ):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                sdk_lib_path = candidate
                break
        if sdk_lib_path:
            build_env.prepend_path("LD_LIBRARY_PATH", sdk_lib_path)
        # The upstream cmake/Libraries.cmake OpenSSL compatibility test
        # (try_run of cmake/tests/openssl.cpp) links libQt6Network.so /
        # libQt6Core.so and *executes* the probe during configure. Those Qt
        # shared libraries live in the qtbase package, so without qtbase/lib
        # on LD_LIBRARY_PATH the probe dies at load time with
        # 'Error loading shared library libQt6Network.so.6' and the configure
        # step fails with 'Your OpenSSL library looks incompatible'.
        for dep_name in (
            "qtbase", "qtdeclarative", "qtwebsockets", "qtsvg",
            "qttools", "qtscxml", "qtshadertools",
        ):
            try:
                dep_lib = os.path.join(
                    self.dependencies[dep_name].package_folder, "lib"
                )
            except KeyError:
                continue
            if os.path.isdir(dep_lib):
                build_env.append_path("LD_LIBRARY_PATH", dep_lib)
        with build_env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            # The sandbox enforces a process/thread limit: with an unbounded
            # '--parallel' CMake uses every CPU core and the make job chain
            # (make[1] -> make[2] -> /bin/sh -> compiler) multiplies the
            # process count, so fork fails with EAGAIN ('/bin/sh: Resource
            # temporarily unavailable', Error 127). AusweisApp generates
            # thousands of QML/resource targets for every platform, so cap
            # the parallelism explicitly.
            # Run the build under build_env's environment (no env="conanrun"):
            # lld needs the SDK llvm/lib prepended on LD_LIBRARY_PATH, and
            # the link line references every dependency .so by absolute path,
            # so the runtime paths from VirtualRunEnv are not needed here
            # (ctest below still runs with the Conan runtime environment).
            self.run(
                "cmake --build . --parallel 4",
                cwd=self.build_folder,
            )
        if can_run(self):
            self.output.info(
                "Running configured upstream AusweisApp2 tests "
                "with the Conan runtime environment"
            )
            test_env = Environment()
            test_env.define("QT_QPA_PLATFORM", "offscreen")
            with test_env.vars(self).apply():
                ctest = self._ctest_executable()
                self.run(
                    f'"{ctest}" --test-dir "{self.build_folder}" '
                    "--output-on-failure -j1",
                    env="conanrun",
                )
        else:
            self.output.info(
                "Cross-building: upstream ausweisapp tests require "
                "a runnable target"
            )

    def package(self):
        # The AusweisApp binary is built into the build folder; the upstream
        # install target also copies translations and resources.
        cmake = CMake(self)
        cmake.install()
        # Fallback: package the bare executable if the install target did not
        # produce a usable layout.
        bin_dir = os.path.join(self.build_folder, "src")
        if not os.path.isdir(os.path.join(self.package_folder, "bin")):
            copy(
                self,
                "AusweisApp",
                src=bin_dir,
                dst=os.path.join(self.package_folder, "bin"),
                keep_path=False,
            )

    def package_info(self):
        # Application package: expose the binary directory for consumers.
        self.cpp_info.bindirs = ["bin"]
