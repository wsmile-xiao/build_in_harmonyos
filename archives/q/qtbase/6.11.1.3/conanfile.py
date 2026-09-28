#!/usr/bin/env python3
"""Conan recipe for Qt Base 6.11.1 with Wayland on HarmonyOS PC."""

import errno
import glob
import hashlib
import io
import json
import os
import posixpath
import re
import shlex
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    check_sha256,
    unzip,
    load,
    save,
)


class QtbaseConan(ConanFile):
    name = "qtbase"
    version = "6.11.1.3"
    description = (
        "Qt Base with Wayland client, SQL/SQLite, PrintSupport/CUPS, "
        "fontconfig and system-library integrations for HarmonyOS PC"
    )
    license = "BSD-3-Clause AND LGPL-3.0-only AND GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-6/qtbase-index.html"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "probes/*", "licenses/*", "resources/*", "conan-cmake/*"
    options = {
        "shared": [True, False],
        "full_tests": [True, False],
    }
    default_options = {
        "shared": True,
        "full_tests": False,
    }

    _base_test_targets = (
        "tst_qcolor",
        "tst_qhostaddress",
        "tst_qsizepolicy",
        "tst_qwidget",
        "tst_qimage",
        "tst_qpainter",
        "tst_qdom",
    )
    _wayland_test_targets = (
        "tst_client",
        "tst_clientextension",
        "tst_wayland_cursor",
        "tst_datadevicev1",
        "tst_client_fullscreenshellv1",
        "tst_inputcontext",
        "tst_multithreaded",
        "tst_nooutput",
        "tst_output",
        "tst_primaryselectionv1",
        "tst_wl_reconnect",
        "tst_scaling",
        "tst_seat",
        "tst_seatv4",
        "tst_seatv7",
        "tst_surface",
        "tst_tabletv2",
        "tst_wlconnect",
        "tst_xdgdecorationv1",
        "tst_xdgoutput",
        "tst_xdgshell",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("dbus/1.14.10")
        self.requires("libxkbcommon/1.6.0", transitive_headers=True, transitive_libs=True)
        # cups/2.4.19 pins openssl/3.5.6; force the graph onto this package's
        # 3.5.6.1 without modifying the published cups recipe.
        self.requires("openssl/3.5.6.1", override=True, force=True)
        self.requires("wayland/1.22.0", transitive_headers=True, transitive_libs=True)
        self.requires("wayland-protocols/1.36")
        # 6.11.1.3: SQL plugin, print support and font discovery backends.
        self.requires("sqlite/3.53.3")
        self.requires("cups/2.4.19", transitive_headers=True, transitive_libs=True)
        self.requires("fontconfig/2.18.3", transitive_headers=True, transitive_libs=True)
        # fontconfig/2.18.3 pins freetype/2.14.3; align with it.
        self.requires("freetype/2.14.3", transitive_headers=True, transitive_libs=True)
        self.requires("harfbuzz/14.4.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libpng/1.6.58.3")
        self.requires("libjpeg/10")
        # Qt6Core links ZSTD when its zstd feature is enabled; declare the
        # Conan package so Qt's WrapZSTD probe resolves the Conan zstd instead
        # of a host-provided libzstd, and consumers get an explicit dependency.
        self.requires("zstd/1.5.7.1", transitive_headers=True, transitive_libs=True)
        self.requires("pcre2/10.48")
        # cups/2.4.19 pins zlib/1.3.1.1; force the graph onto 1.3.2 without
        # modifying the published cups recipe.
        self.requires("zlib/1.3.2", override=True, force=True)
        self.requires("double-conversion/3.4.0")

    def build_requirements(self):
        # Qt's protocol macros execute wayland-scanner while building.
        # Use the host package as a build-context tool source; Conan resolves
        # its executable from the build context without duplicating host libs.
        self.tool_requires("wayland/1.22.0")

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "qtbase/6.11.1.3 in this recipe is a HarmonyOS PC adaptation"
            )
        if cross_building(self):
            raise ConanInvalidConfiguration(
                "This recipe builds Qt tools natively; use matching OHOS "
                "aarch64 host and build profiles"
            )
        if str(self.settings.arch) != "armv8" or not self.options.shared:
            raise ConanInvalidConfiguration(
                "This adaptation supports shared Qt libraries on OHOS armv8"
            )

    def package_id(self):
        # Test intensity does not change the installed Qt ABI or contents.
        self.info.options.rm_safe("full_tests")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        archive = os.environ.get("QTBASE_SOURCE_ARCHIVE")
        if archive:
            check_sha256(self, archive, self.conan_data["sources"]["sha256"])
            unzip(self, archive, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        archive_dir = os.environ.get("QTBASE_DATA_ARCHIVE_DIR")
        for name, specification in self.conan_data["data_sources"].items():
            destination = os.path.join(self.source_folder, "qtbase-data", name)
            if archive_dir:
                archive = os.path.join(archive_dir, specification["url"].rsplit("/", 1)[-1])
                check_sha256(self, archive, specification["sha256"])
                unzip(self, archive, destination=destination,
                      strip_root=specification["strip_root"],
                      excludes=specification.get("excludes"))
            else:
                get(self, destination=destination, **specification)

    @staticmethod
    def _portable_path(path):
        return str(path).replace("\\", "/")

    @staticmethod
    def _required_file(path, description):
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                f"Missing {description}: {path}"
            )
        return path

    def _dependency_library(self, dependency, library):
        libdir = os.path.join(dependency.package_folder, "lib")
        candidates = [
            os.path.join(libdir, f"lib{library}.so"),
            os.path.join(libdir, f"lib{library}.a"),
        ]
        candidates.extend(sorted(glob.glob(
            os.path.join(libdir, f"lib{library}.so.*")
        )))
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            f"Dependency {dependency.ref} does not provide lib{library}"
        )

    def _write_wayland_config(self, wayland, include_dir, libraries):
        version = str(wayland.ref.version)
        include_dir = self._portable_path(include_dir)
        libraries = {
            component: self._portable_path(path)
            for component, path in libraries.items()
        }
        content = f'''# Conan wayland bridge: component targets over the single aggregate package.
set(Wayland_VERSION "{version}")
set(Wayland_FOUND TRUE)
foreach(_tgt IN ITEMS Client Server Cursor Egl)
    if(NOT TARGET Wayland::${{_tgt}})
        add_library(Wayland::${{_tgt}} INTERFACE IMPORTED)
    endif()
    set(Wayland_${{_tgt}}_FOUND TRUE)
endforeach()
set_target_properties(Wayland::Client PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "{include_dir}"
    INTERFACE_LINK_LIBRARIES "{libraries['Client']}")
set_target_properties(Wayland::Server PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "{include_dir}"
    INTERFACE_LINK_LIBRARIES "{libraries['Server']}")
set_target_properties(Wayland::Cursor PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "{include_dir}"
    INTERFACE_LINK_LIBRARIES "{libraries['Cursor']}")
set_target_properties(Wayland::Egl PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "{include_dir}"
    INTERFACE_LINK_LIBRARIES "{libraries['Egl']}")
'''
        save(
            self,
            os.path.join(self.generators_folder, "WaylandConfig.cmake"),
            content,
        )
        version_content = f'''set(PACKAGE_VERSION "{version}")
if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)
    set(PACKAGE_VERSION_COMPATIBLE FALSE)
else()
    set(PACKAGE_VERSION_COMPATIBLE TRUE)
    if(PACKAGE_FIND_VERSION VERSION_EQUAL PACKAGE_VERSION)
        set(PACKAGE_VERSION_EXACT TRUE)
    endif()
endif()
'''
        save(
            self,
            os.path.join(self.generators_folder, "WaylandConfigVersion.cmake"),
            version_content,
        )

    def _relocated_pkgconfig_dir(self):
        output_dir = os.path.join(
            self.generators_folder, "qtbase-pkgconfig"
        )
        specs = (
            ("wayland", "lib/pkgconfig/wayland-client.pc"),
            ("wayland", "lib/pkgconfig/wayland-server.pc"),
            ("wayland", "lib/pkgconfig/wayland-cursor.pc"),
            ("wayland", "lib/pkgconfig/wayland-egl.pc"),
            ("wayland", "lib/pkgconfig/wayland-scanner.pc"),
            ("libxkbcommon", "lib/pkgconfig/xkbcommon.pc"),
            ("wayland-protocols", "share/pkgconfig/wayland-protocols.pc"),
            # 6.11.1.3: system-library integrations probed via pkg-config.
            ("cups", "lib/pkgconfig/libcups2.pc"),
            ("fontconfig", "lib/pkgconfig/fontconfig.pc"),
            ("freetype", "lib/pkgconfig/freetype2.pc"),
            ("harfbuzz", "lib/pkgconfig/harfbuzz.pc"),
            ("libpng", "lib/pkgconfig/libpng.pc"),
            ("libjpeg", "lib/pkgconfig/libjpeg.pc"),
            ("pcre2", "lib/pkgconfig/libpcre2-16.pc"),
            ("pcre2", "lib/pkgconfig/libpcre2-32.pc"),
            ("zlib", "lib/pkgconfig/zlib.pc"),
            ("double-conversion", "lib/pkgconfig/double-conversion.pc"),
            ("sqlite", "lib/pkgconfig/sqlite3.pc"),
            ("zstd", "lib/pkgconfig/libzstd.pc"),
        )
        for dependency_name, relative_path in specs:
            dependency = self.dependencies.host[dependency_name]
            source = os.path.join(
                dependency.package_folder, *relative_path.split("/")
            )
            if not os.path.isfile(source):
                # Optional bridge entries (e.g. libjpeg has no .pc in some
                # versions) are skipped; CMake config discovery still runs.
                continue
            content = load(self, source)
            prefix = self._portable_path(dependency.package_folder)
            content, replacements = re.subn(
                r"(?m)^prefix=.*$", f"prefix={prefix}", content
            )
            if replacements == 0:
                content = f"prefix={prefix}\n{content}"
            # Some shipped .pc files (e.g. freetype2.pc in the published
            # freetype recipe) hard-code absolute libdir/includedir instead of
            # deriving them from ${prefix}; rewriting prefix alone would leave
            # dead paths like //include behind, which break Qt's WrapSystem*
            # probes (Build #56677: "//include/freetype2"). Rewrite any
            # absolute-only libdir/includedir onto the package prefix as well.
            content = re.sub(
                r"(?m)^(libdir|includedir)=/(?!/)(.*)$",
                rf"\1={prefix}/\2",
                content,
            )
            content = content.replace(f"libdir=//lib", f"libdir={prefix}/lib")
            content = content.replace(
                f"includedir=//include", f"includedir={prefix}/include"
            )
            content = content.replace(f"exec_prefix=/\n", f"exec_prefix={prefix}\n")
            # Rewrite flag values that embedded the dead absolute paths too
            # (e.g. freetype2.pc's "Libs: -L//lib").
            content = content.replace("-L//lib", f"-L{prefix}/lib")
            content = content.replace("-I//include", f"-I{prefix}/include")
            save(self, os.path.join(output_dir, os.path.basename(source)), content)
        return output_dir

    def _configure_wayland_dependencies(self, tc):
        wayland = self.dependencies.host["wayland"]
        xkbcommon = self.dependencies.host["libxkbcommon"]
        protocols = self.dependencies.host["wayland-protocols"]
        scanner_package = self.dependencies.build["wayland"]

        wayland_include = self._required_file(
            os.path.join(wayland.package_folder, "include", "wayland-client.h"),
            "Wayland client header",
        )
        wayland_include = os.path.dirname(wayland_include)
        component_libraries = {
            "Client": "wayland-client",
            "Server": "wayland-server",
            "Cursor": "wayland-cursor",
            "Egl": "wayland-egl",
        }
        resolved_libraries = {}
        for component, library in component_libraries.items():
            resolved_library = self._dependency_library(wayland, library)
            resolved_libraries[component] = resolved_library
            tc.cache_variables[f"Wayland_{component}_INCLUDE_DIR"] = (
                wayland_include
            )
            tc.cache_variables[f"Wayland_{component}_LIBRARY"] = (
                resolved_library
            )
            tc.cache_variables[f"Wayland_{component}_VERSION"] = "1.22.0"
        tc.cache_variables["Wayland_VERSION"] = "1.22.0"
        self._write_wayland_config(
            wayland, wayland_include, resolved_libraries
        )

        scanner = self._required_file(
            os.path.join(scanner_package.package_folder, "bin", "wayland-scanner"),
            "build-context wayland-scanner",
        )
        if str(self.settings.os) == "OHOS":
            scanner = os.path.join(self.build_folder, "qtbase-runtime", "wayland-scanner")
        tc.cache_variables["WaylandScanner_EXECUTABLE"] = scanner

        xkb_include = self._required_file(
            os.path.join(
                xkbcommon.package_folder, "include", "xkbcommon", "xkbcommon.h"
            ),
            "xkbcommon header",
        )
        tc.cache_variables["XKB_INCLUDE_DIR"] = os.path.dirname(
            os.path.dirname(xkb_include)
        )
        tc.cache_variables["XKB_LIBRARY"] = self._dependency_library(
            xkbcommon, "xkbcommon"
        )

        protocols_dir = os.path.join(
            protocols.package_folder, "share", "wayland-protocols"
        )
        if not os.path.isdir(protocols_dir):
            raise ConanInvalidConfiguration(
                f"Missing Wayland protocols data: {protocols_dir}"
            )
        tc.cache_variables["CMAKE_PROGRAM_PATH"] = os.path.dirname(scanner)

        pkgconfig_dir = self._relocated_pkgconfig_dir()
        build_env = Environment()
        build_env.define("PKG_CONFIG_LIBDIR", pkgconfig_dir)
        build_env.define("PKG_CONFIG_PATH", pkgconfig_dir)
        build_env.define("PKG_CONFIG_SYSROOT_DIR", "")
        build_env.prepend_path("PATH", os.path.dirname(scanner))
        for dependency in self.dependencies.build.values():
            libdir = os.path.join(dependency.package_folder, "lib")
            if os.path.isdir(libdir):
                build_env.prepend_path("LD_LIBRARY_PATH", libdir)
        build_env.vars(self).save_script("qtbase_wayland_dependencies")

    def _configure_qt_feature_dependencies(self, tc):
        dbus = self.dependencies.host["dbus"]
        dbus_include = self._required_file(
            os.path.join(
                dbus.package_folder, "include", "dbus-1.0", "dbus", "dbus.h"
            ),
            "D-Bus public header",
        )
        tc.cache_variables["DBus1_INCLUDE_DIR"] = os.path.dirname(
            os.path.dirname(dbus_include)
        )
        tc.cache_variables["DBus1_LIBRARY"] = self._dependency_library(
            dbus, "dbus-1"
        )
        tc.cache_variables["DBus1_VERSION"] = "1.14.10"
        expat_library = self._dependency_library(
            self.dependencies.host["expat"], "expat"
        )
        # The published static DBus package has no DBus1Config.cmake. Qt's
        # linked backend also needs DBus's Expat and threading dependencies.
        save(self, os.path.join(self.generators_folder, "DBus1Config.cmake"),
             f'''include(CMakeFindDependencyMacro)
find_dependency(Threads)
set(DBus1_VERSION "1.14.10")
set(DBus1_INCLUDE_DIR "{self._portable_path(tc.cache_variables['DBus1_INCLUDE_DIR'])}")
set(DBus1_LIBRARY "{self._portable_path(tc.cache_variables['DBus1_LIBRARY'])}")
if(NOT TARGET dbus-1)
    add_library(dbus-1 INTERFACE IMPORTED)
    set_target_properties(dbus-1 PROPERTIES
        INTERFACE_INCLUDE_DIRECTORIES "${{DBus1_INCLUDE_DIR}}"
        INTERFACE_LINK_LIBRARIES "${{DBus1_LIBRARY}};{self._portable_path(expat_library)};Threads::Threads;${{CMAKE_DL_LIBS}}")
endif()
set(DBus1_FOUND TRUE)
''')
        save(self, os.path.join(self.generators_folder, "DBus1ConfigVersion.cmake"),
             '''set(PACKAGE_VERSION "1.14.10")
if(PACKAGE_FIND_VERSION VERSION_GREATER PACKAGE_VERSION)
    set(PACKAGE_VERSION_COMPATIBLE FALSE)
else()
    set(PACKAGE_VERSION_COMPATIBLE TRUE)
endif()
if(PACKAGE_FIND_VERSION VERSION_EQUAL PACKAGE_VERSION)
    set(PACKAGE_VERSION_EXACT TRUE)
endif()
''')

        openssl = self.dependencies.host["openssl"]
        openssl_header = self._required_file(
            os.path.join(openssl.package_folder, "include", "openssl", "ssl.h"),
            "OpenSSL public header",
        )
        openssl_include = os.path.dirname(os.path.dirname(openssl_header))
        crypto_library = self._dependency_library(openssl, "crypto")
        ssl_library = self._dependency_library(openssl, "ssl")
        tc.cache_variables.update(
            {
                "OPENSSL_ROOT_DIR": openssl.package_folder,
                "OPENSSL_INCLUDE_DIR": openssl_include,
                "OPENSSL_CRYPTO_LIBRARY": crypto_library,
                "OPENSSL_SSL_LIBRARY": ssl_library,
                "OPENSSL_LIBRARIES": f"{ssl_library};{crypto_library}",
            }
        )

        # Qt's printsupport references the Cups::Cups target
        # (qt_find_package(Cups PROVIDED_TARGETS Cups::Cups)), but the published
        # cups recipe exports the lowercase cups::cups target via CMakeDeps.
        # Bridge the naming so the CUPS backend resolves at configure time.
        cups = self.dependencies.host["cups"]
        cups_include = os.path.join(cups.package_folder, "usr", "include")
        # The published cups package ships static archives (libcups.a,
        # libcupsimage.a) whose hash.c/tls-openssl.c reference OpenSSL
        # symbols, so the bridge must carry the same transitive OpenSSL
        # libraries the cups recipe links (Build #56677: undefined EVP_sha256
        # when linking libcupsprintersupport.so).
        cups_lib_dir = self._dependency_library(cups, "cups")
        cups_image_library = self._dependency_library(cups, "cupsimage")
        # libcups.a's transcode.c also needs libiconv symbols.
        iconv_library = self._dependency_library(
            self.dependencies.host["libiconv"], "iconv"
        )
        cups_link_libraries = ";".join(
            self._portable_path(lib)
            for lib in (cups_image_library, cups_lib_dir,
                        ssl_library, crypto_library, iconv_library)
        )
        # Do not include the CMakeDeps cups-config.cmake here: its transitive
        # find_dependency(openssl) cannot resolve because the generated OpenSSL
        # configs are deliberately removed (Qt resolves OpenSSL via FindOpenSSL).
        # Define Cups::Cups directly against the cups libraries instead.
        save(self, os.path.join(self.generators_folder, "CupsConfig.cmake"),
             f'''set(Cups_VERSION "2.4.19")
set(Cups_INCLUDE_DIR "{self._portable_path(cups_include)}")
if(NOT TARGET Cups::Cups)
    add_library(Cups::Cups INTERFACE IMPORTED)
    set_target_properties(Cups::Cups PROPERTIES
        INTERFACE_INCLUDE_DIRECTORIES "${{Cups_INCLUDE_DIR}}"
        INTERFACE_LINK_LIBRARIES "{cups_link_libraries}")
endif()
set(Cups_FOUND TRUE)
''')
        save(self, os.path.join(self.generators_folder, "CupsConfigVersion.cmake"),
             '''set(PACKAGE_VERSION "2.4.19")
if(PACKAGE_FIND_VERSION VERSION_GREATER PACKAGE_VERSION)
    set(PACKAGE_VERSION_COMPATIBLE FALSE)
else()
    set(PACKAGE_VERSION_COMPATIBLE TRUE)
endif()
if(PACKAGE_FIND_VERSION VERSION_EQUAL PACKAGE_VERSION)
    set(PACKAGE_VERSION_EXACT TRUE)
endif()
''')

        # Qt's gui module references the Fontconfig::Fontconfig target
        # (qt_find_package(Fontconfig PROVIDED_TARGETS Fontconfig::Fontconfig)),
        # but the published fontconfig recipe exports the lowercase
        # fontconfig::fontconfig target via CMakeDeps. Bridge the naming the
        # same way as Cups::Cups above.
        fontconfig = self.dependencies.host["fontconfig"]
        fontconfig_include = os.path.join(fontconfig.package_folder, "include")
        fontconfig_library = self._dependency_library(fontconfig, "fontconfig")
        save(self, os.path.join(self.generators_folder, "FontconfigConfig.cmake"),
             f'''set(Fontconfig_VERSION "2.18.3")
set(Fontconfig_INCLUDE_DIR "{self._portable_path(fontconfig_include)}")
if(NOT TARGET Fontconfig::Fontconfig)
    add_library(Fontconfig::Fontconfig INTERFACE IMPORTED)
    set_target_properties(Fontconfig::Fontconfig PROPERTIES
        INTERFACE_INCLUDE_DIRECTORIES "${{Fontconfig_INCLUDE_DIR}}"
        INTERFACE_LINK_LIBRARIES "{self._portable_path(fontconfig_library)}")
endif()
set(Fontconfig_FOUND TRUE)
''')

        # The manual OPENSSL_* cache variables only take effect when CMake's
        # FindOpenSSL module runs. If a stray OpenSSLConfig.cmake exists in a
        # system prefix (OpenSSL_DIR), config-mode search hijacks the
        # resolution and QtNetwork links against the system libssl.so without
        # libcrypto (Build #56677: undefined EVP_KDF_fetch). Point OpenSSL_DIR
        # at a bridge config that imports the exact Conan static libraries.
        openssl_version = "3.5.6"
        save(self, os.path.join(self.generators_folder, "OpenSSLConfig.cmake"),
             f'''set(OPENSSL_VERSION_MAJOR "3")
set(OPENSSL_VERSION_MINOR "5")
set(OPENSSL_VERSION_PATCH "6")
set(OPENSSL_VERSION "{openssl_version}")
if(NOT TARGET OpenSSL::Crypto)
    add_library(OpenSSL::Crypto UNKNOWN IMPORTED)
    set_target_properties(OpenSSL::Crypto PROPERTIES
        IMPORTED_LOCATION "{self._portable_path(crypto_library)}"
        INTERFACE_INCLUDE_DIRECTORIES "{self._portable_path(openssl_include)}"
        INTERFACE_LINK_LIBRARIES "${{CMAKE_DL_LIBS}};Threads::Threads")
endif()
if(NOT TARGET OpenSSL::SSL)
    add_library(OpenSSL::SSL UNKNOWN IMPORTED)
    set_target_properties(OpenSSL::SSL PROPERTIES
        IMPORTED_LOCATION "{self._portable_path(ssl_library)}"
        INTERFACE_INCLUDE_DIRECTORIES "{self._portable_path(openssl_include)}"
        INTERFACE_LINK_LIBRARIES "OpenSSL::Crypto")
endif()
set(OPENSSL_FOUND TRUE)
''')
        tc.cache_variables["OpenSSL_DIR"] = self.generators_folder

    def _has_pthread_cancel(self):
        """Detect whether pthread cancellation APIs can be compiled and linked."""
        # HarmonyOS may expose linkable compatibility stubs without providing
        # usable pthread cancellation semantics. Disable that Qt code path
        # explicitly instead of treating a successful stub link as support.
        if str(self.settings.os) == "OHOS":
            return False
        test_code = (
            "#include <pthread.h>\n"
            "int main(void) {\n"
            "    int old_state;\n"
            "    return pthread_setcancelstate(PTHREAD_CANCEL_DISABLE, "
            "&old_state);\n"
            "}\n"
        )
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        # This probe controls a C++ compile definition, so test the same
        # compiler and flags that Qt will use for its C++ sources.
        configured_compiler = (
            compilers.get("cpp")
            or os.environ.get("CXX")
            or shutil.which("clang++")
            or shutil.which("c++")
        )
        if not configured_compiler:
            return False
        try:
            compiler_command = shlex.split(configured_compiler)
        except ValueError:
            return False
        if not compiler_command:
            return False
        compiler_flags = self.conf.get(
            "tools.build:cxxflags", default=[], check_type=list
        ) or []
        with tempfile.TemporaryDirectory(prefix="qt-pthread-check-") as temp_dir:
            source_path = os.path.join(temp_dir, "check.cpp")
            executable = os.path.join(temp_dir, "check")
            with open(source_path, "w", encoding="utf-8") as source_file:
                source_file.write(test_code)
            try:
                for link_flags in ([], ["-lpthread"]):
                    result = subprocess.run(
                        compiler_command
                        + compiler_flags
                        + [source_path]
                        + link_flags
                        + ["-o", executable],
                        capture_output=True,
                        timeout=30,
                    )
                    if result.returncode == 0:
                        return True
                return False
            except (OSError, subprocess.SubprocessError):
                return False

    def _ohos_sdk_llvm_libdir(self):
        """Locate the OHOS SDK's llvm/lib containing libxml2.so.16.

        CI #17494 / afdko CI-024: the OHOS SDK's lld is a dynamic ELF that
        NEEDED libxml2.so.16 with RUNPATH ``$ORIGIN/../lib``. On CI workers
        (USER=100) the musl dynamic linker fails to resolve lld's RUNPATH,
        and the conan-cache libxml2 (mode 0750, owner 20001006) is unreadable
        by the worker. The OHOS SDK ships its own world-readable
        libxml2.so.16 with full symbols in ``$SDK/llvm/lib``; we discover
        that directory from the active compiler and inject it into
        LD_LIBRARY_PATH so the cmake→clang→lld subprocess chain can load it.

        Returns the directory path, or ``""`` when not applicable.
        """
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        candidates = []
        if cxx:
            compiler = os.path.realpath(cxx)
            try:
                resource_dir = subprocess.check_output(
                    [cxx, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                    timeout=30,
                ).strip()
                # resource_dir = .../llvm/lib/clang/15.0.4
                candidates.append(
                    os.path.dirname(os.path.dirname(resource_dir))
                )
            except (OSError, subprocess.SubprocessError):
                pass
            # Fallback: .../llvm/bin/clang++ -> .../llvm/lib
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def _build_environment(self, sdk_llvm_lib):
        # conanbuild.sh is aggregated AFTER generate(). Modify the structured
        # environment before serialization, not the not-yet-existing launcher.
        build_env = VirtualBuildEnv(self)
        for dependency in self.dependencies.host.values():
            libdir = os.path.join(dependency.package_folder, "lib")
            if os.path.isdir(libdir):
                build_env.environment().prepend_path("LD_LIBRARY_PATH", libdir)
        if self.build_folder:
            build_env.environment().prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, "lib")
            )
            build_env.environment().prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, "qtbase-runtime")
            )
            build_env.environment().define_path("XKB_CONFIG_ROOT", os.path.join(
                self.build_folder, "qtbase-runtime", "xkb", "X11", "xkb"))
            build_env.environment().define_path("XCURSOR_PATH", os.path.join(
                self.build_folder, "qtbase-runtime", "cursors"))
            build_env.environment().define("XCURSOR_THEME", "Adwaita")
            build_env.environment().define_path("TZDIR", os.path.join(
                self.build_folder, "qtbase-runtime", "zoneinfo"))
            zone = self._system_timezone()
            if zone is not None:
                build_env.environment().define("TZ", zone)
        if sdk_llvm_lib:
            build_env.environment().prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return build_env

    def generate(self):
        # 6.11.1.3: emit CMakeDeps configs so Qt's WrapSystem* find_package
        # probes resolve the Conan system-library integrations.
        cmake_deps = CMakeDeps(self)
        cmake_deps.generate()
        # OpenSSL must keep resolving through CMake's built-in FindOpenSSL
        # module with the manual OPENSSL_* cache variables validated in
        # 6.11.1.2. The CMakeDeps-generated OpenSSL config neither carries
        # the version markers Qt's TEST_opensslv11/TEST_opensslv30 probes
        # rely on nor matches those variable names, so remove it before
        # CMake configure runs.
        for entry in os.listdir(self.generators_folder):
            if entry.startswith("OpenSSL") and entry.endswith(".cmake"):
                os.remove(os.path.join(self.generators_folder, entry))
        tc = CMakeToolchain(self)
        self._configure_native_tools(tc)
        self._check_dependency_layout()
        # CMake has no native HarmonyOS platform module. Keep the OHOS
        # compiler/SDK from the profile, but map CMake's platform rules to
        # Linux so Qt's UNIX and shared-library logic is selected.
        class OhosLinuxPlatformBlock(Block):
            template = """\
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_HOST_SYSTEM_NAME Linux)
# HarmonyOS PC builds and runs this aarch64 package on the same machine.
# Keep Linux platform rules but prevent Qt from demanding a separate host Qt.
set(CMAKE_CROSSCOMPILING FALSE)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_HOST_SYSTEM_PROCESSOR aarch64)
"""

            def context(self):
                return {}

        tc.blocks["user_toolchain"] = OhosLinuxPlatformBlock
        tc.cache_variables.update(
            {
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
                "QT_CONAN_DEPENDENCY_BRIDGE": "ON",
                "FEATURE_ipc_posix": "ON",
                # These APIs exist as unusable native stubs. Select Qt's
                # existing named-file and POSIX IPC implementations directly.
                "FEATURE_linkat": "OFF",
                "FEATURE_sysv_shm": "OFF",
                "FEATURE_sysv_sem": "OFF",
                "QT_NO_LIBRARY_SYMLINKS": "ON",
                # Installing rewrites each library's RUNPATH from the build
                # tree to $ORIGIN. With the Conan dependency RUNPATH entries
                # the rewrite's expectation check disagrees with the staged
                # path list (Build #56677 run13: "file RPATH_CHANGE could
                # not write new RPATH"), so set the install RPATH directly.
                # Installing rewrites each shared library's RUNPATH from the
                # build-tree paths to $ORIGIN via file(RPATH_CHANGE). That
                # rewrite aborts when the recorded link order differs from
                # the emitted RUNPATH (Build #56677), so build binaries with
                # $ORIGIN-relative build-tree RPATHs instead — test
                # executables still resolve libQt6*.so within the build tree,
                # and the upstream test runtime resolves the Conan dependency
                # libraries through the staged signed copies and
                # LD_LIBRARY_PATH.
                "CMAKE_BUILD_RPATH_USE_ORIGIN": "ON",
                "CMAKE_INSTALL_RPATH": "$ORIGIN",
                "CMAKE_INSTALL_RPATH_USE_LINK_PATH": "OFF",
                # Qt plugins are CMake MODULE libraries and qt_internal_add_plugin
                # never sets SOVERSION, so CMake does not emit a DT_SONAME for
                # them and Qt's exported plugin targets carry IMPORTED_NO_SONAME
                # TRUE (L5c). A CMAKE_SHARED_MODULE_SONAME_C_FLAG alone does not
                # help: CMake only applies it to MODULE targets that have the
                # SOVERSION property. The fix is a package() post-processing
                # step (_stamp_plugin_sonames) that gives every plugin a plain
                # SONAME matching its file name and rewrites the exported
                # IMPORTED_NO_SONAME to IMPORTED_SONAME (E537 pattern).
                "INSTALL_PUBLICBINDIR": "",
                "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
                "QT_BUILD_TESTS": "ON",
                "QT_BUILD_TESTS_BY_DEFAULT": (
                    "ON" if self.options.full_tests else "OFF"
                ),
                "QT_BUILD_EXAMPLES": "OFF",
                "QT_BUILD_EXAMPLES_BY_DEFAULT": "OFF",
                "FEATURE_gui": "ON",
                "FEATURE_network": "ON",
                "FEATURE_widgets": "ON",
                "FEATURE_graphicsview": "ON",
                "FEATURE_xml": "ON",
                "FEATURE_printsupport": "ON",
                "FEATURE_cups": "ON",
                "FEATURE_cupsjobactions": "OFF",
                "FEATURE_sql": "ON",
                "FEATURE_sqlite": "ON",
                "FEATURE_sqlite_plugin": "ON",
                "FEATURE_sqlite_system": "ON",
                "FEATURE_testlib": "ON",
                "FEATURE_dbus": "ON",
                "FEATURE_dbus_linked": "ON",
                "FEATURE_openssl": "ON",
                "INPUT_openssl": "linked",
                "FEATURE_openssl_linked": "ON",
                "FEATURE_openssl_runtime": "OFF",
                "FEATURE_pkg_config": "ON",
                "FEATURE_wayland": "ON",
                "FEATURE_wayland_client": "ON",
                "FEATURE_waylandscanner": "ON",
                "FEATURE_xkbcommon": "ON",
                "QT_QPA_PLATFORMS": "wayland;offscreen;minimal",
                "QT_QPA_DEFAULT_PLATFORM": "wayland",
                # Qt's public -no-opengl switch maps to INPUT_opengl=no.
                # FEATURE_opengl alone does not suppress the fatal OpenGL
                # functionality-test check in Qt 6.11's GUI configuration.
                "INPUT_opengl": "no",
                "FEATURE_opengl": "OFF",
                "FEATURE_opengles2": "OFF",
                "FEATURE_egl": "OFF",
                "FEATURE_eglfs": "OFF",
                "FEATURE_vulkan": "OFF",
                "FEATURE_xcb": "OFF",
                "FEATURE_xlib": "OFF",
                "FEATURE_linuxfb": "OFF",
                "FEATURE_vnc": "OFF",
                "FEATURE_evdev": "OFF",
                "FEATURE_libinput": "OFF",
                "FEATURE_mtdev": "OFF",
                "FEATURE_tslib": "OFF",
                "FEATURE_fontconfig": "ON",
                "FEATURE_system_fontconfig": "ON",
                "FEATURE_gtk3": "OFF",
                "FEATURE_accessibility_atspi_bridge": "OFF",
                "FEATURE_libudev": "OFF",
                "FEATURE_icu": "OFF",
                "FEATURE_system_zlib": "ON",
                "FEATURE_system_pcre2": "ON",
                "FEATURE_system_doubleconversion": "ON",
                "FEATURE_freetype": "ON",
                "FEATURE_system_freetype": "ON",
                "FEATURE_harfbuzz": "ON",
                "FEATURE_system_harfbuzz": "ON",
                "FEATURE_png": "ON",
                "FEATURE_system_png": "ON",
                "FEATURE_jpeg": "ON",
                "FEATURE_system_jpeg": "ON",
                # Keep optional GLib out of this deterministic dependency set.
                # The private PKG_CONFIG_LIBDIR generated above prevents stale
                # host metadata from influencing Qt's feature probes.
                "FEATURE_glib": "OFF",
            }
        )

        # 6.11.1.3: system-library integrations are enabled, so Qt must be
        # allowed to find the WrapSystem* packages that Conan provides via
        # the generated CMakeDeps configs and pkg-config bridge.
        # (6.11.1.2 disabled these probes to force Qt's bundled copies.)
        # OpenSSL keeps resolving through CMake's built-in FindOpenSSL with
        # the manual OPENSSL_* cache variables validated in 6.11.1.2; the
        # generated OpenSSL configs are removed in generate() above.

        # Append target-specific options instead of assigning
        # CMAKE_CXX_FLAGS, which would discard flags supplied by the
        # Conan profile, environment and compiler wrapper.
        if not self._has_pthread_cancel():
            tc.extra_cxxflags.append("-DQT_NO_PTHREAD_CANCEL")
            self.output.info(
                "pthread cancellation APIs unavailable; "
                "defining QT_NO_PTHREAD_CANCEL"
            )
        if str(self.settings.os) == "OHOS":
            # The OHOS Clang driver advertises the ARM crypto target feature,
            # but the platform arm_neon.h does not expose the AES intrinsics
            # used by Qt's optimized qHash implementation.
            tc.extra_cxxflags.append("-DQT_NO_ARM_AES_INTRINSICS")
            self.output.info(
                "ARM AES intrinsics unavailable; "
                "defining QT_NO_ARM_AES_INTRINSICS"
            )
        self._configure_wayland_dependencies(tc)
        self._configure_qt_feature_dependencies(tc)

        # CI #17494 / afdko CI-024: inject the OHOS SDK's world-readable
        # llvm/lib (containing libxml2.so.16 with full symbols) into
        # LD_LIBRARY_PATH, so the cmake→clang→lld subprocess chain can load
        # libxml2.so.16 on CI workers where lld's RUNPATH ($ORIGIN/../lib)
        # is not resolved by the musl dynamic linker and the conan-cache
        # libxml2 is unreadable by the worker (USER=100). Without this,
        # CMake's try-compile test fails with "Error loading shared library
        # libxml2.so.16" (Build #31406).
        sdk_llvm_lib = self._ohos_sdk_llvm_libdir()
        build_env = self._build_environment(sdk_llvm_lib)
        tc.presets_build_environment = build_env.environment()
        tc.generate()
        build_env.generate()
        if sdk_llvm_lib:
            self.output.info(
                f"Injected OHOS SDK llvm/lib into LD_LIBRARY_PATH: "
                f"{sdk_llvm_lib}"
            )

    def build(self):
        self._prepare_cursor_runtime()
        self._run_dependency_preflight()
        if self.conf.get("user.qtbase:preflight_only", default=False, check_type=bool):
            return
        query = os.path.join(self.build_folder, ".cmake", "api", "v1", "query", "cache-v2")
        save(self, query, "")
        cmake = CMake(self)
        cmake.configure()
        self._check_configured_features()
        keep_going = self._keep_going_args(cmake)
        cmake.build(build_tool_args=keep_going)
        self._materialize_library_aliases(os.path.join(self.build_folder, "lib"))
        build_error = None
        if not self.options.full_tests:
            try:
                cmake.build(target=list(self._base_test_targets + self._wayland_test_targets),
                            build_tool_args=keep_going)
            except ConanException as error:
                build_error = str(error)
        if can_run(self):
            self._run_upstream_groups(build_error)
        elif build_error:
            raise ConanInvalidConfiguration(build_error)

    @staticmethod
    def _keep_going_args(cmake):
        if "Ninja" in cmake._generator:
            return ["-k", "0"]
        return ["-k"] if "Makefiles" in cmake._generator else []

    def _configure_native_tools(self, tc):
        make = self.conf.get("tools.gnu:make_program", default=None) or os.environ.get("MAKE")
        if make and "Makefiles" in tc.generator:
            tc.cache_variables["CMAKE_MAKE_PROGRAM"] = self._portable_path(make)
        pkg_config = os.environ.get("PKG_CONFIG") or shutil.which("pkg-config")
        if pkg_config:
            tc.cache_variables["PKG_CONFIG_EXECUTABLE"] = self._portable_path(pkg_config)

    def _check_dependency_layout(self):
        headers = {
            "dbus": ("include/dbus-1.0/dbus/dbus.h", "include/dbus-1.0/dbus/dbus-arch-deps.h"),
            "wayland": ("include/wayland-client.h", "include/wayland-server.h",
                        "include/wayland-cursor.h", "include/wayland-egl.h"),
            "openssl": ("include/openssl/ssl.h", "include/openssl/crypto.h"),
            "libxkbcommon": ("include/xkbcommon/xkbcommon.h",),
            "expat": ("include/expat.h",),
            "wayland-protocols": ("share/wayland-protocols/stable/xdg-shell/xdg-shell.xml",),
        }
        missing = []
        for name, relatives in headers.items():
            dependency = self.dependencies.host[name]
            for relative in relatives:
                path = os.path.join(dependency.package_folder, *relative.split("/"))
                if not os.path.isfile(path):
                    missing.append(f"{name}: {relative}")
        if missing:
            raise ConanInvalidConfiguration("Incomplete dependency headers/data: " + "; ".join(missing))

    def _run_dependency_preflight(self):
        result = {"checks": []}
        cmake = self.conf.get("tools.cmake:cmake_program", default=None) or self._resolve_tool("CMAKE", "cmake")
        make = self.conf.get("tools.gnu:make_program", default=None) or self._resolve_tool("MAKE", "make")
        directory = os.path.join(self.build_folder, "dependency-probe-build")
        prefix = os.path.join(self.build_folder, "dependency-probe-install")
        scanner = (os.path.join(self.build_folder, "qtbase-runtime", "wayland-scanner")
                   if str(self.settings.os) == "OHOS" else
                   os.path.join(self.dependencies.build["wayland"].package_folder, "bin", "wayland-scanner"))

        def check(name, action):
            entry = {"name": name, "passed": False}
            result["checks"].append(entry)
            try:
                action()
                entry["passed"] = True
            except (ConanException, OSError) as error:
                entry["error"] = str(error)
                self.output.error(f"Dependency preflight {name}: {error}")
            save(self, os.path.join(self.build_folder, "dependency-probe.json"), json.dumps(result, indent=2))

        def shared_libraries():
            definitions = {}
            for name, key, libraries in (
                ("dbus", "DBUS", {"DBUS_LIBRARY": "dbus-1"}),
                ("expat", "EXPAT", {"EXPAT_LIBRARY": "expat"}),
                ("openssl", "OPENSSL", {"SSL_LIBRARY": "ssl", "CRYPTO_LIBRARY": "crypto"}),
                ("libxkbcommon", "XKB", {"XKB_LIBRARY": "xkbcommon"}),
                ("wayland", "WAYLAND", {"WAYLAND_CLIENT": "wayland-client", "WAYLAND_SERVER": "wayland-server",
                                         "WAYLAND_CURSOR": "wayland-cursor", "WAYLAND_EGL": "wayland-egl"}),
            ):
                dependency = self.dependencies.host[name]
                definitions[key + "_INCLUDE"] = os.path.join(dependency.package_folder, "include",
                                                               "dbus-1.0" if name == "dbus" else "")
                for variable, library in libraries.items():
                    definitions[variable] = self._dependency_library(dependency, library)
            command = [cmake, "-S", os.path.join(self.source_folder, "probes"), "-B", directory,
                       "-G", "Unix Makefiles", f"-DCMAKE_MAKE_PROGRAM={make}", "-DCMAKE_BUILD_TYPE=Release",
                       "-DCMAKE_TOOLCHAIN_FILE=" + os.path.join(self.generators_folder, "conan_toolchain.cmake")]
            command.extend(f"-D{key}={self._portable_path(value)}" for key, value in definitions.items())
            self.run(shlex.join(command))
            self.run(shlex.join([cmake, "--build", directory, "--parallel", "1", "--verbose"]))
            installed = [os.path.join(prefix, "lib", name) for name in
                         ("libqtbase_dependency_probe.so.1", "qtbase_dependency_consumer")]
            for path in installed:
                if os.path.lexists(path):
                    os.unlink(path)
            self.run(shlex.join([cmake, "--install", directory, "--prefix", prefix]))
            for path in installed:
                self._required_file(path, "dependency probe artifact")
            if str(self.settings.os) == "OHOS":
                self._sign_elf_files(installed)
            environment = Environment()
            environment.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
            with environment.vars(self).apply():
                self.run(shlex.join([installed[1]]))

        check("wayland-scanner-execution", lambda: self.run(shlex.join([scanner, "--version"])))
        check("shared-dependencies-install-sign-load", shared_libraries)
        if not all(entry["passed"] for entry in result["checks"]):
            raise ConanInvalidConfiguration("Dependency preflight failed; see dependency-probe.json")

    def _prepare_cursor_runtime(self):
        if str(self.settings.os) != "OHOS":
            return
        # The locked Wayland cursor binary was readable but rejected by the
        # device loader; a private copy re-signed by the native SDK loaded.
        # Preserve the dependency cache and keep the repaired runtime local.
        directory = os.path.join(self.build_folder, "qtbase-runtime")
        os.makedirs(directory, exist_ok=True)
        data_sources = os.path.join(self.source_folder, "qtbase-data")
        self._run_tool([sys.executable, os.path.join(self.source_folder, "probes", "prepare_runtime_data.py"),
                        "--sources", data_sources, "--destination", directory],
                       "prepare upstream keyboard and cursor data")
        metadata = os.path.join(data_sources, "tzdata")
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compilers.get("c") or self._resolve_tool("CC", "clang")
        compiler_command = shlex.split(compiler)
        compiler_command.extend(self.conf.get("tools.build:cflags", default=[], check_type=list) or [])
        self.run(shlex.join([sys.executable, os.path.join(self.source_folder, "probes", "prepare_timezone.py"),
                            "--code-dir", os.path.join(data_sources, "tzcode"),
                            "--metadata-dir", metadata,
                            "--compiler-json", json.dumps(compiler_command),
                            "--destination", os.path.join(directory, "zoneinfo")]))
        sources = {
            "libwayland-cursor.so.0": self._dependency_library(self.dependencies.host["wayland"], "wayland-cursor"),
            "wayland-scanner": os.path.join(self.dependencies.build["wayland"].package_folder, "bin", "wayland-scanner"),
        }
        targets, records = [], []
        for name, source in sources.items():
            target = os.path.join(directory, name)
            # A previously loaded signed ELF may reject in-place writes on
            # OHOS. Stage a new inode and replace it atomically for retries.
            with tempfile.TemporaryDirectory(prefix=".runtime-", dir=directory) as staging:
                copied = os.path.join(staging, name)
                shutil.copy2(source, copied)
                os.replace(copied, target)
            targets.append(target)
            with open(source, "rb") as stream:
                records.append({"name": name, "source": os.path.realpath(source),
                                "source_sha256": hashlib.sha256(stream.read()).hexdigest()})
        scanner = os.path.join(directory, "wayland-scanner")
        patchelf = self._resolve_tool("PATCHELF", "patchelf")
        needed = self._run_tool([patchelf, "--print-needed", scanner], "inspect scanner dependencies").splitlines()
        replacements = []
        for dependency in needed:
            if posixpath.isabs(dependency) and posixpath.basename(dependency) == "libexpat.so":
                self._run_tool([patchelf, "--replace-needed", dependency, "libexpat.so", scanner],
                               "relocate the scanner Expat dependency")
                replacements.append({"from": dependency, "to": "libexpat.so"})
        records[1]["needed_replacements"] = replacements
        self._sign_elf_files(targets)
        for record, target in zip(records, targets):
            with open(target, "rb") as stream:
                record["signed_sha256"] = hashlib.sha256(stream.read()).hexdigest()
        save(self, os.path.join(directory, "runtime-provenance.json"), json.dumps(records, indent=2))
        self.output.info("Prepared private re-signed Wayland cursor and scanner")

    def _run_upstream_groups(self, build_error=None):
        result = {"test_build_error": build_error, "groups": []}
        try:
            self._check_upstream_inventory()
        except ConanException as error:
            result["inventory_error"] = str(error)
        ctest = self._resolve_tool("CTEST", "ctest")
        wayland_pattern = "^({})$".format("|".join(self._wayland_test_targets))
        base_filter = ["-E", wayland_pattern] if self.options.full_tests else [
            "-R", "^({})$".format("|".join(self._base_test_targets))]
        groups = [("base", "full-upstream.xml" if self.options.full_tests else "base-upstream.xml", base_filter),
                  ("wayland", "wayland-upstream.xml", ["-R", wayland_pattern])]
        for name, report, selection in groups:
            try:
                directory, probes = self._test_runtime_directory()
            except ConanInvalidConfiguration as error:
                result["groups"].append({"name": name, "runtime_error": str(error)})
                continue
            with directory as runtime_dir:
                environment = Environment()
                environment.define("XDG_RUNTIME_DIR", runtime_dir)
                # Upstream mock compositors create a QTemporaryDir and then
                # replace XDG_RUNTIME_DIR themselves. Both must use this root.
                environment.define("TMPDIR", runtime_dir)
                if name == "base":
                    environment.define("QT_QPA_PLATFORM", "offscreen")
                else:
                    environment.unset("QT_QPA_PLATFORM")
                # musl's dynamic loader ignores DT_RUNPATH, and OHOS refuses
                # to mmap unsigned ELF files from the read-only Conan cache
                # (same failure family as E318/E486). Copy the shared-library
                # dependencies into the build lib directory and re-sign them
                # so the upstream tests can load libfontconfig.so.1 & co.
                # (Build #56677).
                self._stage_signed_test_libraries()
                # musl's dynamic loader ignores DT_RUNPATH, so the staged
                # copies must be reachable through LD_LIBRARY_PATH.
                environment.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(self.build_folder, "lib")
                )
                command = [ctest, "--output-on-failure", "--no-tests=error", "--timeout", "300",
                           "--output-junit", report, *selection]
                with environment.vars(self).apply():
                    code = self.run(shlex.join(command), cwd=self.build_folder, ignore_errors=True)
                result["groups"].append({"name": name, "exit_code": code, "junit": report,
                                         "runtime_dir": runtime_dir, "runtime_probes": probes})
        save(self, os.path.join(self.build_folder, "upstream-group-results.json"), json.dumps(result, indent=2))
        failures = [item["name"] for item in result["groups"] if item.get("exit_code") != 0]
        if build_error or result.get("inventory_error") or failures:
            raise ConanInvalidConfiguration("Upstream validation failed; see upstream-group-results.json and both JUnit reports")

    def _stage_signed_test_libraries(self):
        """Copy shared-library dependencies into the build lib dir, signed."""
        lib_dir = os.path.join(self.build_folder, "lib")
        staged = []
        for dependency in self.dependencies.host.values():
            dependency_lib = os.path.join(dependency.package_folder, "lib")
            if not os.path.isdir(dependency_lib):
                continue
            for entry in os.listdir(dependency_lib):
                if not entry.endswith(".so") and ".so." not in entry:
                    continue
                source = os.path.join(dependency_lib, entry)
                if not os.path.isfile(source) or os.path.islink(source):
                    continue
                target = os.path.join(lib_dir, entry)
                if not os.path.exists(target):
                    shutil.copy2(source, target)
                    staged.append(target)
                # The Conan cache ships the real file under its full version
                # name and symlinks the SONAME (libfontconfig.so.1 ->
                # libfontconfig.so.1.17.0). The staged copies must carry the
                # SONAME name too, because that is what NEEDED entries
                # reference and LD_LIBRARY_PATH resolution is literal.
                try:
                    soname = self._run_tool(
                        [self._resolve_tool("PATCHELF", "patchelf"),
                         "--print-soname", target],
                        f"read the SONAME of {entry}",
                    ).strip()
                except Exception:
                    soname = ""
                if soname and soname != entry:
                    soname_target = os.path.join(lib_dir, soname)
                    if not os.path.exists(soname_target):
                        shutil.copy2(source, soname_target)
                        staged.append(soname_target)
        if staged:
            self._sign_elf_files(staged)
            self.output.info(
                f"Staged and re-signed {len(staged)} dependency libraries "
                f"for the upstream test runtime"
            )

    def _test_runtime_directory(self):
        parents = [tempfile.gettempdir()]
        if str(self.settings.os) == "OHOS":
            parents.append("/data/storage/el2/base/cache")
        probes = []
        for parent in dict.fromkeys(parents):
            directory = None
            probe = {"parent": parent}
            try:
                directory = tempfile.TemporaryDirectory(prefix="qt-tests-", dir=parent)
                probe["runtime_dir"] = directory.name
                os.chmod(directory.name, 0o700)
                if os.name == "posix":
                    metadata = os.stat(directory.name)
                    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
                        raise OSError(errno.EACCES, "Runtime directory must be owned by this user with mode 0700")
                self._probe_wayland_socket(directory.name)
            except OSError as error:
                probe.update(passed=False, errno=error.errno, error=str(error))
                probes.append(probe)
                if directory is not None:
                    directory.cleanup()
            else:
                probe["passed"] = True
                probes.append(probe)
                self.output.info("Upstream test runtime: " + directory.name)
                return directory, probes
        raise ConanInvalidConfiguration("No usable upstream test socket directory: " + json.dumps(probes))

    @staticmethod
    def _probe_wayland_socket(directory):
        if not hasattr(socket, "AF_UNIX"):
            raise OSError(errno.EAFNOSUPPORT, "AF_UNIX sockets are required for Wayland tests")
        # Include the extra QTemporaryDir component used by Qt's test mains and
        # reserve enough socket-name space for wl_display_add_socket_auto().
        with tempfile.TemporaryDirectory(prefix="qt_temp-", dir=directory) as nested:
            address = os.path.join(nested, "wayland-31")
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                server.settimeout(5)
                server.bind(address)
                server.listen(1)
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.settimeout(5)
                    client.connect(address)
                    connection, _ = server.accept()
                    with connection:
                        connection.settimeout(5)
                        client.sendall(b"Q")
                        if connection.recv(1) != b"Q":
                            raise OSError(errno.EIO, "Upstream test socket probe data mismatch")

    @staticmethod
    def _system_timezone():
        # Honour an application-provided TZ; otherwise read the device setting.
        if "TZ" in os.environ:
            return os.environ["TZ"]
        param = shutil.which("param")
        if not param:
            return None
        try:
            result = subprocess.run([param, "get", "persist.time.timezone"],
                                    capture_output=True, text=True, timeout=5)
            zone = result.stdout.strip()
            return zone if result.returncode == 0 and re.fullmatch(r"[A-Za-z0-9_+./-]+", zone) else None
        except (OSError, subprocess.SubprocessError):
            return None

    def _check_configured_features(self):
        replies = glob.glob(os.path.join(self.build_folder, ".cmake", "api", "v1",
                                         "reply", "cache-v2-*.json"))
        if not replies:
            raise ConanInvalidConfiguration("Missing CMake cache file-api reply")
        reply = max(replies, key=os.path.getmtime)
        entries = json.loads(load(self, reply))["entries"]
        values = {entry["name"]: entry["value"] for entry in entries}
        required = ("gui", "widgets", "network", "xml", "dbus", "dbus_linked",
                    "openssl", "openssl_linked", "wayland", "wayland_client",
                    "waylandscanner", "xkbcommon", "wayland_client_xdg_shell")
        disabled = [name for name in required
                    if values.get("QT_FEATURE_" + name) not in ("ON", "TRUE", "1")]
        save(self, os.path.join(self.build_folder, "qtbase-features.json"),
             json.dumps({key: values.get("QT_FEATURE_" + key) for key in required}, indent=2))
        if disabled:
            raise ConanInvalidConfiguration("Required Qt features disabled: " + ", ".join(disabled))

    def _check_upstream_inventory(self):
        output = io.StringIO()
        ctest = self._resolve_tool("CTEST", "ctest")
        self.run(shlex.join([ctest, "--show-only=json-v1"]), cwd=self.build_folder, stdout=output)
        inventory = json.loads(output.getvalue())
        save(self, os.path.join(self.build_folder, "upstream-inventory.json"),
             json.dumps(inventory, indent=2))
        registered = {test["name"] for test in inventory["tests"]}
        missing = set(self._base_test_targets + self._wayland_test_targets) - registered
        if missing:
            raise ConanInvalidConfiguration("Upstream tests not registered: " + ", ".join(sorted(missing)))

    def _exclude_test_installation(self):
        # Qt excludes the testing directory's install rules with this existing
        # option. Full validation may have enabled them, including foreign-arch
        # ELF parser fixtures. Test intensity must not change the delivered Qt.
        cmake = self.conf.get("tools.cmake:cmake_program", default=None) or self._resolve_tool("CMAKE", "cmake")
        self.run(shlex.join([cmake, "-S", self.source_folder, "-B", self.build_folder,
                             "-DQT_BUILD_TESTS_BY_DEFAULT=OFF"]))

    def package(self):
        self._exclude_test_installation()
        cmake = CMake(self)
        cmake.install()
        bridge_dir = os.path.join(self.package_folder, "lib", "cmake", "Qt6")
        for name in ("Qt6WaylandClientConanDependencies.cmake", "Qt6GuiPrivateConanDependencies.cmake",
                     "Qt6WaylandScannerConanDependencies.cmake"):
            shutil.copy2(os.path.join(self.source_folder, "conan-cmake", name), os.path.join(bridge_dir, name))
        os.makedirs(os.path.join(bridge_dir, "conan"), exist_ok=True)
        shutil.copy2(os.path.join(self.source_folder, "conan-cmake", "FindXKB.cmake"),
                     os.path.join(bridge_dir, "conan", "FindXKB.cmake"))
        license_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(license_dir, exist_ok=True)
        for license_path in glob.glob(os.path.join(self.source_folder, "licenses", "*.txt")):
            shutil.copy2(license_path, license_dir)
        shutil.copytree(os.path.join(self.source_folder, "LICENSES"),
                        os.path.join(license_dir, "Qt"), dirs_exist_ok=True)
        for dependency in self.dependencies.host.values():
            dependency_name = str(dependency.ref.name)
            if not dependency.package_folder:
                continue
            candidate = os.path.join(dependency.package_folder, "licenses")
            if os.path.isdir(candidate):
                shutil.copytree(candidate, os.path.join(license_dir, dependency_name), dirs_exist_ok=True)
        cursor = os.path.join(self.build_folder, "qtbase-runtime", "libwayland-cursor.so.0")
        if str(self.settings.os) == "OHOS":
            self._required_file(cursor, "private signed Wayland cursor runtime")
            shutil.copy2(cursor, os.path.join(self.package_folder, "lib", "libwayland-cursor.so.0"))
            tools_dir = os.path.join(self.package_folder, "libexec")
            os.makedirs(tools_dir, exist_ok=True)
            shutil.copy2(os.path.join(self.build_folder, "qtbase-runtime", "wayland-scanner"), tools_dir)
            shutil.copy2(os.path.join(self.build_folder, "qtbase-runtime", "runtime-provenance.json"),
                         os.path.join(self.package_folder, "runtime-provenance.json"))
            license_dir = os.path.join(self.package_folder, "licenses")
            os.makedirs(license_dir, exist_ok=True)
            shutil.copy2(os.path.join(self.source_folder, "licenses", "wayland-cursor-LICENSE.txt"), license_dir)
            shutil.copytree(os.path.join(self.build_folder, "qtbase-runtime", "xkb", "X11"),
                            os.path.join(self.package_folder, "share", "X11"), dirs_exist_ok=True)
            shutil.copytree(os.path.join(self.build_folder, "qtbase-runtime", "xkb", "licenses"),
                            os.path.join(license_dir, "xkeyboard-config"), dirs_exist_ok=True)
            shutil.copytree(os.path.join(self.build_folder, "qtbase-runtime", "cursors", "Adwaita"),
                            os.path.join(self.package_folder, "share", "icons", "Adwaita"), dirs_exist_ok=True)
            shutil.copytree(os.path.join(self.build_folder, "qtbase-runtime", "cursors", "licenses"),
                            os.path.join(license_dir, "adwaita"), dirs_exist_ok=True)
            shutil.copy2(os.path.join(self.build_folder, "qtbase-runtime", "data-provenance.json"),
                         os.path.join(self.package_folder, "data-provenance.json"))
            shutil.copytree(os.path.join(self.build_folder, "qtbase-runtime", "zoneinfo"),
                            os.path.join(self.package_folder, "share", "zoneinfo"), dirs_exist_ok=True)
            shutil.copy2(os.path.join(self.build_folder, "qtbase-runtime", "zoneinfo", "LICENSE"),
                         os.path.join(license_dir, "tzdata-LICENSE"))
        self._materialize_library_aliases(os.path.join(self.package_folder, "lib"))
        self._relocate_absolute_needed(os.path.join(self.package_folder, "lib"))
        self._stamp_plugin_sonames()
        self._validate_wayland_package()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()
            provenance_file = os.path.join(self.package_folder, "runtime-provenance.json")
            provenance = json.loads(load(self, provenance_file))
            for record in provenance:
                subdir = "libexec" if record["name"] == "wayland-scanner" else "lib"
                with open(os.path.join(self.package_folder, subdir, record["name"]), "rb") as stream:
                    record["packaged_sha256"] = hashlib.sha256(stream.read()).hexdigest()
            save(self, provenance_file, json.dumps(provenance, indent=2))

    @staticmethod
    def _materialize_library_aliases(libdir):
        libraries = sorted(glob.glob(os.path.join(libdir, "libQt6*.so.6")))
        if not libraries:
            raise ConanInvalidConfiguration(f"Missing ABI-named Qt libraries: {libdir}")
        for source in libraries:
            if os.path.islink(source) or not os.path.isfile(source):
                raise ConanInvalidConfiguration(f"Expected a regular Qt ABI file: {source}")
            # Copy installed files only after CMake has adjusted their RPATH.
            # Both aliases remain usable by qmake, pkg-config and dlopen.
            for destination in (source[:-2], source + ".11.1"):
                with tempfile.TemporaryDirectory(prefix=".qt-alias-", dir=libdir) as temp:
                    copied = os.path.join(temp, "library")
                    shutil.copy2(source, copied)
                    os.replace(copied, destination)

    def _relocate_absolute_needed(self, libdir):
        """Rewrite absolute DT_NEEDED entries to SONAME basenames (L5b).

        Dependencies built without a DT_SONAME (double-conversion) force the
        linker to record the absolute Conan cache path in Qt's NEEDED table.
        Replace those with the SONAME name so the installed libraries stay
        relocatable; consumers resolve the name from the staged re-signed
        copies on LD_LIBRARY_PATH. Runs before _sign_installed_elfs so the
        final artifacts carry the relocated table.
        """
        patchelf = self._resolve_tool("PATCHELF", "patchelf")
        relocated = []
        for candidate in sorted(glob.glob(os.path.join(libdir, "lib*.so*"))):
            if os.path.islink(candidate) or not os.path.isfile(candidate):
                continue
            needed = self._run_tool(
                [patchelf, "--print-needed", candidate],
                f"list NEEDED entries of {posixpath.basename(candidate)}",
            ).splitlines()
            for entry in needed:
                if posixpath.isabs(entry):
                    replacement = posixpath.basename(entry)
                    self._run_tool(
                        [patchelf, "--replace-needed", entry, replacement, candidate],
                        f"relocate NEEDED {entry} in {posixpath.basename(candidate)}",
                    )
                    relocated.append(entry)
        if relocated:
            self.output.info(
                f"Relocated {len(relocated)} absolute NEEDED entries to SONAME references"
            )

    def _stamp_plugin_sonames(self):
        """Give Qt plugins a relocatable SONAME and fix exported targets (L5c).

        Qt plugins are CMake MODULE libraries; qt_internal_add_plugin never
        sets SOVERSION, so CMake emits no DT_SONAME for them and Qt's
        install(EXPORT) files carry IMPORTED_NO_SONAME TRUE — L5c rejects
        that. Give each plugin .so a plain SONAME matching its file name with
        patchelf, and rewrite the matching exported plugin target so the CMake
        metadata (IMPORTED_SONAME) and the installed ELF agree (E537
        link-time-SONAME pattern). Runs before _sign_installed_elfs so the
        rewritten files are re-signed.
        """
        patchelf = self._resolve_tool("PATCHELF", "patchelf")
        package_root = self.package_folder
        plugin_roots = ("plugins", "modules")
        soname_by_location = {}
        for root in plugin_roots:
            plugin_dir = os.path.join(package_root, root)
            if not os.path.isdir(plugin_dir):
                continue
            for dirpath, _, filenames in os.walk(plugin_dir):
                for filename in sorted(filenames):
                    if not (filename.endswith(".so") or ".so." in filename):
                        continue
                    path = os.path.join(dirpath, filename)
                    if os.path.islink(path) or not os.path.isfile(path):
                        continue
                    try:
                        current = self._run_tool(
                            [patchelf, "--print-soname", path],
                            f"read the SONAME of {filename}",
                        ).strip()
                    except ConanInvalidConfiguration:
                        current = ""
                    if current:
                        continue
                    self._run_tool(
                        [patchelf, "--set-soname", filename, path],
                        f"set the SONAME of plugin {filename}",
                    )
                    rel = os.path.relpath(path, package_root)
                    soname_by_location[rel] = filename
        if not soname_by_location:
            return
        cmake_root = os.path.join(package_root, "lib", "cmake")
        if not os.path.isdir(cmake_root):
            return
        for dirpath, _, filenames in os.walk(cmake_root):
            for filename in filenames:
                if not filename.endswith(".cmake"):
                    continue
                path = os.path.join(dirpath, filename)
                with open(path, "r", encoding="utf-8") as stream:
                    content = stream.read()
                if "IMPORTED_NO_SONAME" not in content:
                    continue
                changed = False
                for line in content.splitlines(keepends=True):
                    match = re.search(
                        r'IMPORTED_NO_SONAME(?:_\w+)?\s+"TRUE"', line
                    )
                    if not match:
                        continue
                    location_match = re.search(
                        r'IMPORTED_LOCATION(?:_\w+)?\s+"'
                        r'\$\{_IMPORT_PREFIX\}/([^"]+)"',
                        content,
                    )
                    location = location_match.group(1) if location_match else ""
                    soname = soname_by_location.get(location)
                    if not soname:
                        soname = os.path.basename(location or "")
                    if not soname:
                        continue
                    old = match.group(0)
                    config_suffix = re.search(
                        r"IMPORTED_NO_SONAME(_\w+)?", old
                    ).group(1) or ""
                    content = content.replace(
                        old,
                        f'IMPORTED_SONAME{config_suffix} "{soname}"',
                        1,
                    )
                    changed = True
                if changed:
                    with open(path, "w", encoding="utf-8") as stream:
                        stream.write(content)

    def _validate_wayland_package(self):
        required_artifacts = {
            "Qt6DBus library": ("lib/libQt6DBus.so*",),
            "Qt6WaylandClient library": ("lib/libQt6WaylandClient.so*",),
            "Qt6WaylandClient CMake config": (
                "lib/cmake/Qt6WaylandClient/*Config.cmake",
            ),
            "Qt6WaylandClientPrivate CMake config": (
                "lib/cmake/Qt6WaylandClientPrivate/*Config.cmake",
                "lib/cmake/Qt6WaylandClient/*Private*Config.cmake",
            ),
            "qtwaylandscanner": (
                "libexec/qtwaylandscanner",
                "bin/qtwaylandscanner",
            ),
            "Qt6WaylandScannerTools CMake config": (
                "lib/cmake/Qt6WaylandScannerTools/*Config.cmake",
            ),
            "Wayland QPA plugin": ("plugins/platforms/libqwayland.so",),
            "Wayland XDG shell plugin": ("plugins/wayland-shell-integration/libxdg-shell.so",),
            "Offscreen QPA plugin": ("plugins/platforms/libqoffscreen.so",),
            "OpenSSL TLS plugin": ("plugins/tls/libqopensslbackend.so",),
            "WaylandClient public headers": (
                "include/QtWaylandClient/QWaylandClientExtension",
            ),
            "WaylandClient private headers": (
                "include/QtWaylandClient/*/QtWaylandClient/private/"
                "qwaylandintegration_p.h",
            ),
        }
        missing = []
        for description, patterns in required_artifacts.items():
            matches = []
            for pattern in patterns:
                matches.extend(glob.glob(os.path.join(self.package_folder, pattern)))
            if not any(os.path.isfile(path) for path in matches):
                missing.append(description)
        if missing:
            raise ConanInvalidConfiguration(
                "Qt Wayland package is incomplete: " + ", ".join(missing)
            )

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF executables and shared objects."""
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):  # ET_EXEC, ET_DYN
                    binaries.append(candidate)
        self._sign_elf_files(binaries)

    def _sign_elf_files(self, binaries):
        if not binaries:
            return
        for candidate in binaries:
            self._validate_ohos_elf(candidate)
        environment = self._build_environment(self._ohos_sdk_llvm_libdir())
        with environment.vars().apply():
            self._resign_elf_files(binaries)

    def _validate_ohos_elf(self, candidate):
        with open(candidate, "rb") as stream:
            header = stream.read(20)
        if (self._elf_type(candidate) not in (2, 3) or len(header) < 20 or header[:6] != b"\x7fELF\x02\x01"
                or struct.unpack_from("<H", header, 18)[0] != 183):
            raise ConanInvalidConfiguration(f"Expected ELF64 AArch64 artifact: {candidate}")

    def _resign_elf_files(self, binaries):
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        f"remove the old code signature from {binary}",
                    )
                self._run_tool(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        unsigned,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ],
                    f"sign {binary}",
                )
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}"
                    )
                self._validate_ohos_elf(signed)
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}"
        )
        return any(
            ".codesign" in line.split()
            for line in section_table.splitlines()
        )

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result.stdout

    @staticmethod
    def _elf_type(path):
        """Return the ELF e_type value, or None for a non-ELF file."""
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"Unable to inspect installed file {path}: {error}"
            ) from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(
                f"Unsupported ELF byte order in installed file {path}"
            )
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        configured = os.environ.get(environment_variable)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if (
            not resolved
            and os.path.isfile(candidate)
            and os.access(candidate, os.X_OK)
        ):
            resolved = os.path.abspath(candidate)
        if (
            not resolved
            or not os.path.isfile(resolved)
            or not os.access(resolved, os.X_OK)
        ):
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set "
                f"{environment_variable} or add it to PATH"
            )
        return os.path.abspath(resolved)

    def package_info(self):
        # qmake and qtpaths are installed alongside the Qt libraries.
        self.cpp_info.bindirs = ["bin"]
        # Qt installs complete, relocatable Qt6Config.cmake files. Prevent
        # CMakeDeps from shadowing them with an incomplete generated config.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake"),
                                   os.path.join("lib", "cmake", "Qt6", "platforms")]
        # Consumers (the conan test package included) run with only the
        # package's own lib directory on LD_LIBRARY_PATH first, and the OHOS
        # loader refuses to map unsigned ELF files straight out of the
        # read-only Conan cache (E318/E486 family). Stage re-signed copies
        # of the shared-library dependencies next to the Qt libraries so
        # every consumer can resolve them.
        staged = []
        package_lib = os.path.join(self.package_folder, "lib")
        for dependency in self.dependencies.host.values():
            # Build-context requirements (e.g. the wayland scanner) have no
            # host package folder to stage from.
            if not dependency.package_folder:
                continue
            dependency_lib = os.path.join(dependency.package_folder, "lib")
            if not os.path.isdir(dependency_lib):
                continue
            for entry in os.listdir(dependency_lib):
                if not entry.endswith(".so") and ".so." not in entry:
                    continue
                source = os.path.join(dependency_lib, entry)
                if not os.path.isfile(source) or os.path.islink(source):
                    continue
                target = os.path.join(package_lib, entry)
                if not os.path.exists(target):
                    shutil.copy2(source, target)
                    staged.append(target)
                try:
                    soname = self._run_tool(
                        [self._resolve_tool("PATCHELF", "patchelf"),
                         "--print-soname", target],
                        f"read the SONAME of {entry}",
                    ).strip()
                except Exception:
                    soname = ""
                if not soname:
                    # Dependency libraries built without a DT_SONAME
                    # (double-conversion, stale expat cache) must carry one
                    # once staged into the package, or L5a rejects the
                    # unversioned real .so. Give the copy a plain SONAME
                    # matching its file name so NEEDED resolution stays
                    # literal, exactly like the SHARED-library flag does for
                    # Qt's own libraries (E330).
                    self._run_tool(
                        [self._resolve_tool("PATCHELF", "patchelf"),
                         "--set-soname", entry, target],
                        f"set the SONAME of {entry}",
                    )
                    soname = entry
                if soname and soname != entry:
                    soname_target = os.path.join(package_lib, soname)
                    if not os.path.exists(soname_target):
                        shutil.copy2(source, soname_target)
                        staged.append(soname_target)
        if staged:
            # _sign_elf_files touches self.build_folder via its build
            # environment, which package_info() must not access. Sign inline
            # with the raw tools instead.
            self._resign_elf_files(staged)
            self.output.info(
                f"Staged and re-signed {len(staged)} dependency libraries "
                f"inside the package for consumer runtimes"
            )
        self.runenv_info.define_path(
            "QT_PLUGIN_PATH", os.path.join(self.package_folder, "plugins")
        )
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        self.runenv_info.define_path("XKB_CONFIG_ROOT", os.path.join(self.package_folder, "share", "X11", "xkb"))
        self.runenv_info.define_path("XCURSOR_PATH", os.path.join(self.package_folder, "share", "icons"))
        self.runenv_info.define("XCURSOR_THEME", "Adwaita")
        if not os.environ.get("QT_QPA_FONTDIR") and os.path.isdir("/system/fonts"):
            self.runenv_info.define_path("QT_QPA_FONTDIR", "/system/fonts")
        self.runenv_info.define_path("TZDIR", os.path.join(self.package_folder, "share", "zoneinfo"))
        zone = self._system_timezone()
        if zone is not None:
            self.runenv_info.define("TZ", zone)
        # Consumers run moc and both Wayland scanners during their own builds.
        # Host-requires runenv is not inherited by Conan's VirtualBuildEnv.
        for dependency in self.dependencies.host.values():
            if dependency.package_folder:
                libdir = os.path.join(dependency.package_folder, "lib")
                if os.path.isdir(libdir):
                    self.buildenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
                    self.runenv_info.append_path("LD_LIBRARY_PATH", libdir)
        self.buildenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        sdk_llvm_lib = self._ohos_sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "libexec"))

        core = self.cpp_info.components["core"]
        core.libs = ["Qt6Core"]
        # Reference the direct requirements the Core module links so Conan's
        # package_info validation sees every direct dependency used. zlib (and
        # openssl) are override-only requirements, so they must not appear
        # here. zstd is linked into Qt6Core by the Qt zstd feature.
        core.requires = [
            "pcre2::pcre2", "double-conversion::double-conversion",
            "zstd::zstd"
        ]
        # CMakeToolchain aggregates component metadata; root builddirs alone
        # are omitted when the package defines components.
        core.builddirs = list(self.cpp_info.builddirs)
        core.set_property("cmake_target_name", "Qt6::Core")

        network = self.cpp_info.components["network"]
        network.libs = ["Qt6Network"]
        # OpenSSL resolves through the manual OPENSSL_* cache variables (its
        # conan requirement is an override for the graph, not a declared
        # component dependency), so the network component must not reference
        # openssl::ssl here — Conan 2 rejects requires to non-direct deps.
        network.requires = ["core"]
        network.set_property("cmake_target_name", "Qt6::Network")

        gui = self.cpp_info.components["gui"]
        gui.libs = ["Qt6Gui"]
        gui.requires = [
            "core", "fontconfig::fontconfig", "freetype::freetype",
            "harfbuzz::harfbuzz", "libpng::libpng", "libjpeg::libjpeg"
        ]
        gui.set_property("cmake_target_name", "Qt6::Gui")

        widgets = self.cpp_info.components["widgets"]
        widgets.libs = ["Qt6Widgets"]
        widgets.requires = ["core", "gui"]
        widgets.set_property("cmake_target_name", "Qt6::Widgets")

        xml = self.cpp_info.components["xml"]
        xml.libs = ["Qt6Xml"]
        xml.requires = ["core"]
        xml.set_property("cmake_target_name", "Qt6::Xml")

        dbus = self.cpp_info.components["dbus"]
        dbus.libs = ["Qt6DBus"]
        dbus.requires = ["core", "dbus::dbus"]
        dbus.set_property("cmake_target_name", "Qt6::DBus")

        wayland_client = self.cpp_info.components["wayland_client"]
        wayland_client.libs = ["Qt6WaylandClient"]
        wayland_client.requires = [
            "core", "gui", "wayland::wayland", "libxkbcommon::libxkbcommon",
            "wayland-protocols::wayland-protocols"
        ]
        wayland_client.set_property(
            "cmake_target_name", "Qt6::WaylandClient"
        )

        # 6.11.1.3: expose the SQL and PrintSupport modules. The SQLite
        # driver ships as a plugin loaded at runtime, so the SQL component
        # links only against Core; CUPS is linked into Qt6PrintSupport.
        sql = self.cpp_info.components["sql"]
        sql.libs = ["Qt6Sql"]
        # sqlite is a direct requirement and Qt6Sql declares its sqlite3
        # linkage in its CMake target; reference it so Conan's package_info
        # validation sees the direct dependency used.
        sql.requires = ["core", "sqlite::sqlite"]
        sql.set_property("cmake_target_name", "Qt6::Sql")

        printsupport = self.cpp_info.components["printsupport"]
        printsupport.libs = ["Qt6PrintSupport"]
        printsupport.requires = ["core", "gui", "widgets", "cups::cups"]
        printsupport.set_property("cmake_target_name", "Qt6::PrintSupport")
