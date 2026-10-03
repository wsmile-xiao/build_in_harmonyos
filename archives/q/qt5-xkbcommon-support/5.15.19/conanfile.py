#!/usr/bin/env python3
"""Conan recipe for qt5-xkbcommon-support 5.15.19 on HarmonyOS PC (arm64).

Why this package exists
-----------------------
The published OHOS Qt5 packages (qt/5.15.19.1 and qt5-qtbase/5.15.2.2) were
configured with ``-no-xkbcommon``, so the Qt module ``QtXkbCommonSupport`` was
never built: both package trees carry the syncqt'd header skeleton but ship
**no** ``libQt5XkbCommonSupport.a``, **no** ``Qt5XkbCommonSupportConfig.cmake``
and **no** ``mkspecs/modules/qt_lib_xkbcommon_support_private.pri``.

Qt5 consumers that hard-require that module cannot build without it:

  * kwayland5/5.116.0  -> ``find_package(Qt5XkbCommonSupport REQUIRED)`` and
    ``target_link_libraries(... Qt::XkbCommonSupportPrivate)``
  * qt5-qtwayland      -> qmake ``qtConfig(xkbcommon) { QT_FOR_PRIVATE +=
    xkbcommon_support-private }``

Rebuilding the whole of Qt5 just to flip one option costs ~1 h of CI budget per
run, so this package builds *only* the two translation units of that module out
of the official Qt 5.15.19 qtbase archive and installs them in normal Qt5 module
layout.  This is the same module-split pattern the registry already uses for
``qtbase-gui/6.11.1`` and ``qtbase-sql-dbus/6.11.1``.

What it installs
----------------
  * ``lib/libQt5XkbCommonSupport.a``  (static, matching upstream
    ``xkbcommon.pro``: ``CONFIG += static internal_module``)
  * ``include/QtXkbCommonSupport/5.15.19/QtXkbCommonSupport/private/qxkbcommon_p.h``
    plus the short forwarding header
    ``include/QtXkbCommonSupport/private/qxkbcommon_p.h``
  * native CMake package config
    ``lib/cmake/Qt5XkbCommonSupport/Qt5XkbCommonSupportConfig.cmake``
    exporting the imported target ``Qt5::XkbCommonSupportPrivate``
  * ``mkspecs/modules/qt_lib_xkbcommon_support_private.pri`` following the exact
    variable shape of the real ``qt_lib_*_support_private.pri`` files shipped by
    qt/5.15.19.1 (so qmake consumers resolve ``xkbcommon_support-private``)

OHOS-specific notes
-------------------
  * ``-fPIC`` is mandatory: this static archive is linked into shared libraries
    (libKF5WaylandClient.so), and an OHOS aarch64 link of a non-PIC object fails
    with ``relocation R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC``
    (the same failure mode recorded for zlib/1.3.1 -> zlib/1.3.1.1).
  * ``-ftemplate-depth=1024`` mirrors upstream's clang workaround: the
    ``KeyTbl`` in qxkbcommon.cpp expands past the old 256-level default.
  * No ELF signing pass is needed here: the package ships only a static archive
    and headers; the executables are produced by the consumers.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.layout import basic_layout

REQUIRED_CPPSTD = "17"
QT_VERSION = "5.15.19"
MODULE_DIR = os.path.join("src", "platformsupport", "input", "xkbcommon")


class Qt5XkbCommonSupportConan(ConanFile):
    name = "qt5-xkbcommon-support"
    version = QT_VERSION
    description = ("Qt5 QtXkbCommonSupport module (libQt5XkbCommonSupport.a + "
                   "Qt5::XkbCommonSupportPrivate + qmake module pri) for HarmonyOS PC")
    license = "LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only"
    homepage = "https://code.qt.io/cgit/qt/qtbase.git/tree/src/platformsupport/input/xkbcommon"
    url = ""

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src", build_folder="build")

    def validate(self):
        # R32: never compare settings.os with == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                f"{self.name} in this archive is a HarmonyOS PC adaptation"
            )
        cppstd = self.settings.get_safe("compiler.cppstd")
        if cppstd is not None and str(cppstd).replace("gnu", "") < REQUIRED_CPPSTD:
            raise ConanInvalidConfiguration(
                f"{self.name} requires compiler.cppstd >= {REQUIRED_CPPSTD}"
            )

    def requirements(self):
        # The module is compiled against Qt's private headers, so the Qt headers
        # must reach our consumers too (transitive_headers) and the Qt shared
        # libraries must stay on their link/loader path (transitive_libs).
        self.requires(f"qt/{QT_VERSION}.1", transitive_headers=True, transitive_libs=True)
        # <xkbcommon/xkbcommon.h> is included by qxkbcommon_p.h, which is a
        # public (installed) header of this package -> the include path and the
        # library must be transitive.
        self.requires("libxkbcommon/1.6.0", transitive_headers=True, transitive_libs=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── helpers ────────────────────────────────────────────────────────────

    @property
    def _module_source(self):
        return os.path.join(self.source_folder, MODULE_DIR)

    def _tool(self, key, candidates):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        if compilers.get(key):
            return compilers[key]
        for candidate in candidates:
            found = shutil.which(candidate)
            if found:
                return found
        return candidates[-1]

    def _cxx(self):
        return self._tool("cpp", ["clang++", "aarch64-unknown-linux-ohos-clang++", "c++"])

    def _ar(self):
        return self._tool("ar", ["llvm-ar", "ar"])

    def _cppstd_flag(self):
        cppstd = str(self.settings.get_safe("compiler.cppstd") or REQUIRED_CPPSTD)
        cppstd = cppstd.replace("gnu", "")
        return f"-std=c++{cppstd}"

    def _qt_package_folder(self):
        return self.dependencies["qt"].package_folder

    def _xkbcommon_package_folder(self):
        return self.dependencies["libxkbcommon"].package_folder

    def _include_dirs(self, qt_folder, xkb_folder):
        """Include roots required to compile qxkbcommon.cpp.

        qxkbcommon.cpp pulls QtCore/QtGui public headers, the Qt *private*
        headers (<private/qmakearray_p.h>, <QtCore/private/qstringiterator_p.h>,
        QtGui/private/qguiapplication_p.h) and the QPA headers (<qpa/...>).
        Qt5 lays those out under include/<Module>/<ver>/<Module>/{private,qpa}.
        """
        qt_inc = os.path.join(qt_folder, "include")
        dirs = [qt_inc]
        for module in ("QtCore", "QtGui"):
            dirs.append(os.path.join(qt_inc, module))
            versioned = os.path.join(qt_inc, module, QT_VERSION)
            dirs.append(versioned)
            dirs.append(os.path.join(versioned, module))
            dirs.append(os.path.join(versioned, module, "private"))
            dirs.append(os.path.join(versioned, module, "qpa"))
        dirs.append(os.path.join(xkb_folder, "include"))
        # Qt's private headers (qthread_p.h, pulled in through
        # qguiapplication_p.h) include "qplatformdefs.h", which Qt keeps in the
        # mkspecs directory of the active platform spec, not in include/. The
        # OHOS Qt5 package ships both harmonyos-clang and linux-clang specs.
        mkspecs = os.path.join(qt_folder, "mkspecs")
        for spec in ("harmonyos-clang", "linux-clang"):
            candidate = os.path.join(mkspecs, spec)
            if os.path.isdir(candidate):
                dirs.append(candidate)
                break
        # Keep only directories that really exist: a bogus -I is harmless for
        # clang but pollutes the exported interface of the CMake target.
        return [d for d in dirs if os.path.isdir(d)]

    def _compile_flags(self, qt_folder, xkb_folder):
        flags = [
            "-fPIC",
            self._cppstd_flag(),
            "-O2",
            "-DQT_NO_CAST_FROM_ASCII",
            # qxkbcommon.cpp::KeyTbl exceeds the legacy 256-level template
            # expansion limit of older clang (upstream adds this for clang too).
            "-ftemplate-depth=1024",
            "-Wall",
        ]
        for inc in self._include_dirs(qt_folder, xkb_folder):
            flags.append(f"-I{inc}")
        return flags

    # ── build ──────────────────────────────────────────────────────────────

    def build(self):
        module_src = self._module_source
        if not os.path.isdir(module_src):
            raise ConanInvalidConfiguration(
                f"Qt xkbcommon module sources are missing at {module_src}"
            )

        qt_folder = self._qt_package_folder()
        xkb_folder = self._xkbcommon_package_folder()
        cxx = self._cxx()
        ar = self._ar()
        flags = " ".join(self._compile_flags(qt_folder, xkb_folder))

        objects = []
        for source in ("qxkbcommon.cpp", "qxkbcommon_3rdparty.cpp"):
            src = os.path.join(module_src, source)
            obj = os.path.join(self.build_folder, source[:-4] + ".o")
            self.output.info(f"compiling {source}")
            self.run(f'"{cxx}" {flags} -c "{src}" -o "{obj}"')
            objects.append(obj)

        lib_dir = os.path.join(self.build_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        archive = os.path.join(lib_dir, "libQt5XkbCommonSupport.a")
        self.run(f'"{ar}" rcs "{archive}" ' + " ".join(f'"{o}"' for o in objects))
        if not os.path.isfile(archive) or os.path.getsize(archive) == 0:
            raise ConanInvalidConfiguration("libQt5XkbCommonSupport.a was not produced")

    # ── package ────────────────────────────────────────────────────────────

    def _write_cmake_config(self, cmake_dir, qt_folder, xkb_folder):
        include_dirs = self._include_dirs(qt_folder, xkb_folder)
        include_dirs.append(os.path.join(self.package_folder, "include", "QtXkbCommonSupport", QT_VERSION))
        xkb_lib = os.path.join(xkb_folder, "lib", "libxkbcommon.so")
        lib_path = os.path.join(self.package_folder, "lib", "libQt5XkbCommonSupport.a")

        # Emit a real CMake list variable. Splatting a quoted string into
        # INTERFACE_INCLUDE_DIRECTORIES produces ""a" "b"" and CMake rejects it
        # with "set_target_properties called with incorrect number of arguments".
        includes_block = "\n".join(f'    "{d}"' for d in include_dirs)
        body = f'''# Qt5XkbCommonSupportConfig.cmake — HarmonyOS PC adaptation
#
# Generated by the qt5-xkbcommon-support/5.15.19 Conan recipe. It provides the
# imported target Qt5::XkbCommonSupportPrivate, which is the target Qt5
# consumers (kwayland5, qtwayland) link against. The include roots below are
# resolved from the conan packages this module was compiled against, because a
# support module borrows Qt's private headers and QPA headers.

set(_Qt5XkbCommonSupport_INCLUDE_DIRS
{includes_block}
)

if(NOT TARGET Qt5::XkbCommonSupportPrivate)
    add_library(Qt5::XkbCommonSupportPrivate STATIC IMPORTED)

    set_target_properties(Qt5::XkbCommonSupportPrivate PROPERTIES
        IMPORTED_LOCATION "{lib_path}"
        INTERFACE_INCLUDE_DIRECTORIES "${{_Qt5XkbCommonSupport_INCLUDE_DIRS}}"
        INTERFACE_LINK_LIBRARIES "{xkb_lib}"
    )
endif()

set(Qt5XkbCommonSupport_FOUND TRUE)
set(QT_XKBCOMMONSUPPORT_LIBRARIES Qt5::XkbCommonSupportPrivate)
set(QT_XKBCOMMONSUPPORT_INCLUDE_DIRS "${{_Qt5XkbCommonSupport_INCLUDE_DIRS}}")
'''
        with open(os.path.join(cmake_dir, "Qt5XkbCommonSupportConfig.cmake"),
                  "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)

        version_body = f'''set(PACKAGE_VERSION "{QT_VERSION}")

if("${{PACKAGE_FIND_VERSION}}" VERSION_GREATER "${{PACKAGE_VERSION}}")
    set(PACKAGE_VERSION_COMPATIBLE FALSE)
else()
    set(PACKAGE_VERSION_COMPATIBLE TRUE)
    if("${{PACKAGE_FIND_VERSION}}" VERSION_EQUAL "${{PACKAGE_VERSION}}")
        set(PACKAGE_VERSION_EXACT TRUE)
    endif()
endif()
'''
        with open(os.path.join(cmake_dir, "Qt5XkbCommonSupportConfigVersion.cmake"),
                  "w", encoding="utf-8", newline="\n") as handle:
            handle.write(version_body)

    def _write_qmake_pri(self, mkspecs_dir):
        # Variable shape copied from the real support-module pris shipped by
        # qt/5.15.19.1 (mkspecs/modules/qt_lib_*_support_private.pri). The
        # include/lib paths are absolute inside this package: QT_MODULE_LIB_BASE
        # would point at Qt's own libdir, where our archive does not live.
        includes = " ".join([
            os.path.join(self.package_folder, "include", "QtXkbCommonSupport"),
            os.path.join(self.package_folder, "include", "QtXkbCommonSupport", QT_VERSION),
            os.path.join(self.package_folder, "include", "QtXkbCommonSupport", QT_VERSION, "QtXkbCommonSupport"),
        ])
        body = f'''QT.xkbcommon_support_private.VERSION = {QT_VERSION}
QT.xkbcommon_support_private.name = QtXkbCommonSupport
QT.xkbcommon_support_private.module = Qt5XkbCommonSupport
QT.xkbcommon_support_private.libs = {os.path.join(self.package_folder, "lib")}
QT.xkbcommon_support_private.includes = {includes}
QT.xkbcommon_support_private.frameworks =
QT.xkbcommon_support_private.bins =
QT.xkbcommon_support_private.depends = core_private gui_private
QT.xkbcommon_support_private.uses =
QT.xkbcommon_support_private.module_config = v2 staticlib internal_module
QT.xkbcommon_support_private.DEFINES = QT_NO_CAST_FROM_ASCII
QT.xkbcommon_support_private.enabled_features = xkbcommon
QT.xkbcommon_support_private.disabled_features =
QT_CONFIG += xkbcommon
QT_MODULES += xkbcommon_support
'''
        with open(os.path.join(mkspecs_dir, "qt_lib_xkbcommon_support_private.pri"),
                  "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)

    def package(self):
        qt_folder = self._qt_package_folder()
        xkb_folder = self._xkbcommon_package_folder()

        # 1. static archive
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        shutil.copy2(os.path.join(self.build_folder, "lib", "libQt5XkbCommonSupport.a"),
                     os.path.join(lib_dir, "libQt5XkbCommonSupport.a"))

        # 2. headers, in Qt5 module layout + the short include form consumers use
        header_src = os.path.join(self._module_source, "qxkbcommon_p.h")
        versioned_header_dir = os.path.join(
            self.package_folder, "include", "QtXkbCommonSupport", QT_VERSION,
            "QtXkbCommonSupport", "private")
        short_header_dir = os.path.join(
            self.package_folder, "include", "QtXkbCommonSupport", "private")
        for target_dir in (versioned_header_dir, short_header_dir):
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(header_src, os.path.join(target_dir, "qxkbcommon_p.h"))

        # 3. native CMake package config exporting Qt5::XkbCommonSupportPrivate
        cmake_dir = os.path.join(lib_dir, "cmake", "Qt5XkbCommonSupport")
        os.makedirs(cmake_dir, exist_ok=True)
        self._write_cmake_config(cmake_dir, qt_folder, xkb_folder)

        # 4. qmake module pri (consumed via QMAKE_MODULE_PATH + QT_FOR_PRIVATE)
        mkspecs_dir = os.path.join(self.package_folder, "mkspecs", "modules")
        os.makedirs(mkspecs_dir, exist_ok=True)
        self._write_qmake_pri(mkspecs_dir)

    def package_info(self):
        # Hand the native Qt5XkbCommonSupportConfig.cmake to CMake consumers via
        # builddirs, and prevent CMakeDeps from emitting a competing generated
        # config (same approach as qt/5.15.19.1 and qt5-qtbase/5.15.2.2).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]

        self.cpp_info.libs = ["Qt5XkbCommonSupport"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = [
            os.path.join("include", "QtXkbCommonSupport"),
            os.path.join("include", "QtXkbCommonSupport", QT_VERSION),
        ]
        # Absolute include roots for Qt's private headers are injected by the
        # hand-written CMake config; consumers that use qmake get them from the
        # module pri. Nothing else is exported here on purpose: libxkbcommon is
        # a package requirement and travels with it.
