#!/usr/bin/env python3
"""Conan recipe for qtxdg (libqtxdg) 3.12.0 on OpenHarmony PC.

libqtxdg is the Qt5 implementation of the freedesktop.org XDG specifications
maintained by the LXQt project.  It provides the ``Qt5Xdg`` and
``Qt5XdgIconLoader`` libraries plus the ``Qt5XdgIconPlugin`` icon-engine
plugin consumed by ``find_package(Qt5Xdg 3.3.1 REQUIRED)`` (the first
unsatisfied dependency of kylin-calendar/5.0.0.0).

OHOS adaptation summary (see notes.md for the full story):

* The upstream build system hard-requires the ``lxqt-build-tools`` CMake
  helper package, which is not published in the ohpcd registry.  Because a
  recipe PR may only touch its own archive, ``lxqt-build-tools`` 0.13.0 is
  bundled (downloaded from its official upstream release) and configured /
  installed into the build folder before libqtxdg itself is configured.
* Qt5 is consumed through Conan's ``CMakeDeps`` targets.  The native Qt5
  umbrella configs shipped inside ``qt5-qtbase`` are not relocatable (they
  bake the build-machine mkspecs path), so a small generated CMake shim
  supplies the handful of variables / macros that the native configs would
  otherwise provide (moc/qdbusxml2cpp locations, private include dirs,
  ``qt5_add_dbus_interface``).
* ``zlib`` and ``glib`` are only published as non-PIC static archives on
  OpenHarmony, so the two libraries are built STATIC (same rationale as the
  quazip recipe).  glib's transitive static archives (libffi / proxy-libintl
  / gmodule / pcre2-8 / zlib) are injected into the ``Qt5Xdg`` link
  interface so downstream consumers resolve them.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, mkdir)
from conan.tools.gnu import PkgConfigDeps


class QtxdgConan(ConanFile):
    name = "qtxdg"
    version = "3.12.0"
    description = "Qt5 implementation of the freedesktop.org XDG specifications (libqtxdg)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/lxqt/libqtxdg"
    url = "https://github.com/lxqt/libqtxdg"

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"with_tests": [True, False]}
    default_options = {"with_tests": True}

    # ---------------------------------------------------------------- helpers
    @property
    def _lxqt_build_tools_prefix(self):
        return os.path.join(self.build_folder, "lxqt-build-tools-prefix")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    # ------------------------------------------------------------ dependency
    def requirements(self):
        # qt5-qtbase/5.15.2.2 = Qt5 with Widgets/Xml/DBus components.
        self.requires("qt5-qtbase/5.15.2.2")
        # Qt5Svg provider that already depends on qt5-qtbase/5.15.2.2
        # (qt5-qtsvg/5.15.2.1 pins qt5-qtbase/5.15.2 and would need an
        # override, which makes CMakeDeps drop the Qt5 include directories).
        self.requires("qt5-qtsvgv/5.15.2.2")
        # glib/2.88.0 pins zlib/1.3.1 -> matches qt5-qtbase/5.15.2.2.
        self.requires("glib/2.88.0")

    # ---------------------------------------------------------------- sources
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # --------------------------------------------------------------- generate
    def generate(self):
        deps = CMakeDeps(self)
        # The Conan toolchain sets CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON, so a
        # generated glib-config.cmake would shadow lxqt-build-tools'
        # FindGLIB.cmake.  Upstream CMakeLists.txt consumes the *uppercase*
        # GLIB_INCLUDE_DIRS / GLIB_LIBRARIES variables that only FindGLIB
        # defines, so suppress the Conan config for glib and let module mode
        # resolve it (the test_package generates its own glib config).
        deps.set_property("glib", "cmake_find_mode", "none")
        deps.generate()

        pkgdeps = PkgConfigDeps(self)
        pkgdeps.generate()
        self._write_gio_unix_pc()

        shim = self._write_qt5_shim()

        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # CMakeDeps configs + the bundled lxqt-build-tools install prefix.
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(
            [self.generators_folder, self._lxqt_build_tools_prefix])

        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        tc.variables["BUILD_TESTS"] = "ON" if self.options.with_tests else "OFF"
        # Keep the shipped default-apps configs inside the package prefix
        # (/etc/xdg is read-only on OHOS).
        tc.variables["QTXDG_INSTALL_DEFAPPS_CONFIG"] = "ON"
        tc.variables["QTXDG_DEFAPPS_CONF_INSTALL_DIR"] = "share/qt5xdg"
        # Skip the qmake query for the plugin dir (hermetic install path).
        tc.variables["QTXDGX_ICONENGINEPLUGIN_INSTALL_PATH"] = "plugins/iconengines"
        # glib's transitive static archives, consumed by the Qt5Xdg link
        # interface (see patches/0002).
        tc.variables["QTXDGX_GLIB_STATIC_DEPS"] = ";".join(self._glib_static_deps())

        qtbase = self.dependencies["qt5-qtbase"].package_folder
        tc.cache_variables["CMAKE_AUTOMOC_EXECUTABLE"] = os.path.join(qtbase, "bin", "moc")
        tc.cache_variables["CMAKE_AUTORCC_EXECUTABLE"] = os.path.join(qtbase, "bin", "rcc")
        tc.cache_variables["CMAKE_AUTOUIC_EXECUTABLE"] = os.path.join(qtbase, "bin", "uic")
        tc.variables["CMAKE_PROJECT_INCLUDE"] = shim
        tc.generate()

    def _write_gio_unix_pc(self):
        """Provide a ``gio-unix-2.0`` pkg-config file for lxqt-build-tools'
        FindGLIB.cmake.

        The glib Conan package exposes no ``gio-unix`` component, so
        PkgConfigDeps emits no ``gio-unix-2.0.pc``; FindGLIB then fails to
        locate ``gio/gdesktopappinfo.h`` and ``find_package(GLIB REQUIRED)``
        aborts.  The header *is* shipped at ``include/gio-unix-2.0/gio/``.
        """
        glib_pkg = self.dependencies["glib"].package_folder
        content = (
            "prefix={0}\n"
            "includedir=${{prefix}}/include\n"
            "Name: gio-unix-2.0\n"
            "Description: GIO unix-specific interfaces (Conan wrapper)\n"
            "Version: 2.88.0\n"
            "Requires: gio-2.0\n"
            "Cflags: -I${{includedir}}\n"
        ).format(glib_pkg)
        path = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _write_qt5_shim(self):
        """Generate the CMake shim that restores the Qt5 plumbing which
        Conan's CMakeDeps output does not provide."""
        qtbase = self.dependencies["qt5-qtbase"].package_folder

        def version_dir(module):
            base = os.path.join(qtbase, "include", module)
            if os.path.isdir(base):
                for name in sorted(os.listdir(base)):
                    if name[:1].isdigit() and os.path.isdir(os.path.join(base, name)):
                        return name
            return None

        priv = {}
        for module in ("QtCore", "QtGui"):
            ver = version_dir(module)
            dirs = []
            if ver:
                dirs = [os.path.join(qtbase, "include", module, ver),
                        os.path.join(qtbase, "include", module, ver, module)]
            priv[module] = dirs
        # native Qt5GuiConfig appends the QtCore private dirs to Qt5Gui too
        gui_private = priv["QtGui"] + priv["QtCore"]

        mkspec_dir = os.path.join(qtbase, "mkspecs", "linux-clang")
        if not os.path.isdir(mkspec_dir):
            candidates = sorted(glob.glob(os.path.join(qtbase, "mkspecs", "linux-*")))
            mkspec_dir = candidates[0] if candidates else ""

        def q(paths):
            return " ".join('"{}"'.format(p) for p in paths)

        lines = [
            "# Generated by qtxdg conanfile.py - supplies the Qt5 CMake helpers",
            "# that Conan's CMakeDeps generator does not emit.",
            "set(QT_DEFAULT_MAJOR_VERSION 5)",
            "set(QT_VERSION_MAJOR 5)",
            'set(Qt5Core_MOC_EXECUTABLE "{}")'.format(os.path.join(qtbase, "bin", "moc")),
            'set(Qt5Core_RCC_EXECUTABLE "{}")'.format(os.path.join(qtbase, "bin", "rcc")),
            'set(Qt5DBus_QDBUSXML2CPP_EXECUTABLE "{}")'.format(
                os.path.join(qtbase, "bin", "qdbusxml2cpp")),
            "set(Qt5Core_PRIVATE_INCLUDE_DIRS {})".format(q(priv["QtCore"])),
            "set(Qt5Gui_PRIVATE_INCLUDE_DIRS {})".format(q(gui_private)),
        ]
        if mkspec_dir:
            lines.append('include_directories("{}")'.format(mkspec_dir))
        # Real Qt macros needed for QT5_ADD_DBUS_INTERFACE / qt5_generate_moc.
        lines.append('include("{}")'.format(
            os.path.join(qtbase, "lib", "cmake", "Qt5Core", "Qt5CoreMacros.cmake")))
        lines.append('include("{}")'.format(
            os.path.join(qtbase, "lib", "cmake", "Qt5DBus", "Qt5DBusMacros.cmake")))
        # Neutralise the non-PIC static zlib target: OpenHarmony zlib ships a
        # non-PIC libz.a which cannot be linked into the shared icon-engine
        # module.  zlib_FOUND short-circuits CMakeDeps' find_dependency(zlib).
        lines += [
            "if(NOT TARGET zlib::zlib)",
            "  add_library(zlib::zlib INTERFACE IMPORTED)",
            "endif()",
            "set(zlib_FOUND TRUE)",
            "",
        ]
        path = os.path.join(self.generators_folder, "qtxdg_qt5_compat.cmake")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
        return path

    def _find_static_archive(self, filename, dep_names):
        for name in dep_names:
            dep = self.dependencies.get(name)
            if not dep or not dep.package_folder:
                continue
            libdirs = list(dep.cpp_info.libdirs) or ["lib"]
            for libdir in libdirs:
                cand = os.path.join(dep.package_folder, libdir, filename)
                if os.path.isfile(cand):
                    return cand
        return None

    def _glib_static_deps(self):
        """glib's transitive static archives (glib is static-only here)."""
        wanted = [
            ("libffi.a", ("glib", "libffi")),
            ("libgmodule-2.0.a", ("glib",)),
            ("libintl.a", ("glib", "proxy-libintl")),
            ("libpcre2-8.a", ("pcre2",)),
            ("libz.a", ("zlib",)),
        ]
        found = []
        for filename, deps in wanted:
            path = self._find_static_archive(filename, deps)
            if path and path not in found:
                found.append(path)
        return found

    # ------------------------------------------------------------ build tools
    def _build_lxqt_build_tools(self):
        """Download, configure and install the bundled lxqt-build-tools."""
        src = os.path.join(self.build_folder, "lxqt-build-tools-src")
        prefix = self._lxqt_build_tools_prefix
        mkdir(self, src)
        get(self, **self.conan_data["lxqt_build_tools"], strip_root=True, destination=src)

        # lxqt-build-tools' FindInstallConfigPath.cmake unconditionally calls
        # find_package(Qt5Core REQUIRED).  LXQT_ETC_XDG_DIR is provided on the
        # command line, so only a stub config is needed to satisfy the call.
        stub = os.path.join(self.build_folder, "qt5core-stub", "lib", "cmake", "Qt5Core")
        mkdir(self, stub)
        with open(os.path.join(stub, "Qt5CoreConfig.cmake"), "w", encoding="utf-8") as handle:
            handle.write('set(Qt5Core_FOUND TRUE)\nset(Qt5Core_VERSION_STRING "5.15.2")\n')

        cmake = shutil.which("cmake") or "cmake"
        jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)
        build_dir = os.path.join(self.build_folder, "lxqt-build-tools-build")
        self.run(
            '"{cmake}" -S "{src}" -B "{build}" '
            '-DCMAKE_INSTALL_PREFIX="{prefix}" '
            '-DLXQT_ETC_XDG_DIR=/etc/xdg '
            '-DQt5Core_DIR="{stub}" '
            '-DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
            '-DCMAKE_BUILD_TYPE=Release'.format(
                cmake=cmake, src=src, build=build_dir, prefix=prefix, stub=stub),
        )
        self.run('"{cmake}" --install "{build}"'.format(cmake=cmake, build=build_dir))

    # ------------------------------------------------------------------ build
    def _build_env(self):
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        qtbase = self.dependencies["qt5-qtbase"].package_folder
        env.prepend_path("PATH", os.path.join(qtbase, "bin"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase, "lib"))
        return env

    def build(self):
        apply_conandata_patches(self)
        self._build_lxqt_build_tools()

        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

        if self.options.with_tests:
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream QtTest suite (registered with ctest)."""
        ctest = shutil.which("ctest") or "ctest"
        env = Environment()
        for dep in self.dependencies.values():
            if dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        # The upstream test writes into the system temp dir; /tmp is read-only
        # on OHOS, so point it at a writable location under the build folder.
        tmp = os.path.join(self.build_folder, "test-tmp")
        mkdir(self, tmp)
        env.define("TMPDIR", tmp)
        env.define("HOME", tmp)
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            self.run('"{ctest}" --output-on-failure'.format(ctest=ctest),
                     cwd=self.build_folder)

    # ---------------------------------------------------------------- package
    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "Digia-Qt-LGPL-Exception-1.1",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Consumed by `find_package(Qt5Xdg ...)`; the exported CMake target is
        # named Qt5Xdg (no namespace), matching upstream's qt5xdg-config.cmake.
        self.cpp_info.set_property("cmake_file_name", "Qt5Xdg")
        self.cpp_info.set_property("cmake_target_name", "Qt5Xdg")
        self.cpp_info.set_property("pkg_config_name", "Qt5Xdg")

        self.cpp_info.libs = ["Qt5Xdg", "Qt5XdgIconLoader"]
        self.cpp_info.includedirs = ["include", "include/qt5xdg", "include/qt5xdgiconloader"]
        self.cpp_info.libdirs = ["lib"]

        # Static archive -> the whole dependency chain must travel with it.
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtbase::Qt5Gui",
            "qt5-qtbase::Qt5Widgets",
            "qt5-qtbase::Qt5Xml",
            "qt5-qtbase::Qt5DBus",
            "qt5-qtsvgv::Qt5Svg",
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
        ]
