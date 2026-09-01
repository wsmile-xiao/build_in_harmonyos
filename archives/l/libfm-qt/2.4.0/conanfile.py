#!/usr/bin/env python3
"""Conan recipe — libfm-qt 2.4.0.

libfm-qt is the Qt6 file management library used by pcmanfm-qt.
CMake-based, depends on Qt6, GLIB, MenuCache, lxqt-menu-data, etc.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout, CMakeDeps, CMakeToolchain
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file


class LibfmqtConan(ConanFile):
    name = "libfm-qt"
    version = "2.4.0"
    description = "libfm-qt 2.4.0"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/lxde/libfm-qt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # lxqt2-build-tools is a build-only dependency: it ships CMake
        # find-modules (builddirs) but NO libraries, and its recipe declares
        # cmake_find_mode="none" so CMakeDeps never creates its target. Treating
        # it as a normal link dependency makes CMakeDeps reference
        # lxqt2-build-tools::lxqt2-build-tools in libfm-qt_DEPS_TARGET, which
        # does not exist (CI): declare libs=False so it is not propagated as a
        # link dependency while builddirs stay available.
        self.requires("lxqt2-build-tools/2.4.0", libs=False)
        self.requires("glib/2.88.0")
        self.requires("menu-cache/1.1.0")
        self.requires("lxqt-menu-data/2.4.0.1")
        self.requires("libexif/0.6.26.1")
        self.requires("libxcb/1.17.0.1")
        # glib pulls zlib/1.3.1 whose libz.a is built WITHOUT -fPIC; linking it
        # into the shared libfm-qt6.so fails on AArch64 (R_AARCH64 relocation
        # against z_errmsg). zlib/1.3.2 is rebuilt with CFLAGS=-fPIC and is
        # already published, so override the transitive requirement.
        self.requires("zlib/1.3.2", override=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Upstream sources use #include <menu-cache/menu-cache.h> (subdirectory
        # layout), but the menu-cache package installs the header flat at
        # include/menu-cache.h. Patch the two including files to the flat path.
        for rel in ("src/appmenuview.h", "src/appmenuview_p.h"):
            replace_in_file(
                self,
                os.path.join(self.source_folder, rel),
                "#include <menu-cache/menu-cache.h>",
                "#include <menu-cache.h>",
            )
        # OHOS has no X11 (libX11 is not in the dependency graph), so the
        # X11-specific branch in fm_app_launch_context_get_display() can never
        # run. Drop the Xlib include and return nullptr as the non-X11 fallback
        # does. (QNativeInterface::QX11Application itself is forward-declared in
        # qtbase with 'typedef struct _XDisplay Display;' and compiles fine.)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "applaunchcontext.cpp"),
            "#include <QApplication>\n#include <X11/Xlib.h>",
            "#include <QApplication>",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "applaunchcontext.cpp"),
            "static char* fm_app_launch_context_get_display(GAppLaunchContext * /*context*/, GAppInfo * /*info*/, GList * /*files*/) {\n"
            "  if(auto x11NativeInterface = qApp->nativeInterface<QNativeInterface::QX11Application>()) {\n"
            "    Display* dpy = x11NativeInterface->display();\n"
            "    if(dpy) {\n"
            "      char* xstr = DisplayString(dpy);\n"
            "      return g_strdup(xstr);\n"
            "    }\n"
            "  }\n"
            "  return nullptr;\n"
            "}",
            "static char* fm_app_launch_context_get_display(GAppLaunchContext * /*context*/, GAppInfo * /*info*/, GList * /*files*/) {\n"
            "  // OHOS has no X11; no display string is available.\n"
            "  return nullptr;\n"
            "}",
        )
        # fontbutton.cpp includes <X11/X.h> but never uses any X11 symbol.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "fontbutton.cpp"),
            "#include <QFontDialog>\n#include <X11/X.h>",
            "#include <QFontDialog>",
        )
        # xdndworkaround.cpp is a pure X11/XCB workaround for Qt drag & drop
        # issues (XdndWorkaround). The OHOS qtbase is built without the xcb
        # platform plugin, so QNativeInterface::QX11Application does not exist
        # and this file cannot compile. Replace the implementation with a no-op
        # stub that keeps the class API used by folderview.cpp / libfmqt.cpp.
        stub = (
            "/*\n"
            " * Stub implementation of XdndWorkaround for OHOS.\n"
            " *\n"
            " * The original file is an X11 (XCB) specific workaround for Qt drag &\n"
            " * drop issues. On OHOS there is no X11 and the qtbase package is built\n"
            " * without the xcb platform plugin, so QNativeInterface::QX11Application\n"
            " * does not exist. All operations are no-ops which keeps the class API\n"
            " * usable by folderview.cpp / libfmqt.cpp.\n"
            " */\n"
            "#include \"xdndworkaround.h\"\n"
            "\n"
            "XdndWorkaround::XdndWorkaround() = default;\n"
            "XdndWorkaround::~XdndWorkaround() = default;\n"
            "\n"
            "bool XdndWorkaround::nativeEventFilter(const QByteArray&, void*, qintptr*) {\n"
            "    return false;\n"
            "}\n"
            "\n"
            "QByteArray XdndWorkaround::atomName(xcb_atom_t) {\n"
            "    return QByteArray();\n"
            "}\n"
            "\n"
            "xcb_atom_t XdndWorkaround::internAtom(const char*, int) {\n"
            "    return 0;\n"
            "}\n"
            "\n"
            "QByteArray XdndWorkaround::windowProperty(xcb_window_t, xcb_atom_t, xcb_atom_t, int) {\n"
            "    return QByteArray();\n"
            "}\n"
            "\n"
            "void XdndWorkaround::setWindowProperty(xcb_window_t, xcb_atom_t, xcb_atom_t, void*, int, int) {\n"
            "}\n"
        )
        with open(os.path.join(self.source_folder, "src", "xdndworkaround.cpp"), "w", encoding="utf-8") as f:
            f.write(stub)
        # NOTE: upstream relies on CMAKE_INCLUDE_CURRENT_DIR ON so that the
        # generate_export_header() output (fm-qt6_export.h, in the binary dir) is
        # found by the compiler. Do NOT disable it here. The earlier
        # INTERFACE_INCLUDE_DIRECTORIES "prefixed in the source directory" error
        # was actually caused by empty GLIB_* include vars (fixed by injecting
        # GLIB cache vars in generate()), not by CMAKE_INCLUDE_CURRENT_DIR.

    def generate(self):
        cmake_deps = CMakeDeps(self)
        if "qtbase" in self.dependencies.host:
            # qtbase has cmake_find_mode="none" (it supplies its own Qt6 cmake
            # files under lib/cmake). If CMakeDeps generates a qtbase config and
            # references find_dependency(qtbase) in libfm-qt-config.cmake, then
            # consumers' find_package(libfm-qt) fails because no qtbase config
            # exists. Mark it "none" so neither the config nor the
            # find_dependency() entry is emitted.
            cmake_deps.set_property("qtbase", "cmake_find_mode", "none")
        cmake_deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        if "qtbase" in self.dependencies.host:
            # qtbase recipe uses cmake_find_mode="none", so CMakeDeps does not
            # generate a config file for it. Point CMake at the Qt6 cmake config
            # files shipped inside the qtbase package itself. Individual
            # Qt6*_DIR variables are set (not CMAKE_PREFIX_PATH) so that Conan's
            # generated prefix path for the other dependencies is preserved.
            qtbase_cmake = os.path.join(
                self.dependencies.host["qtbase"].package_folder,
                "lib", "cmake"
            )
            if os.path.isdir(qtbase_cmake):
                tc.variables["Qt6_DIR"] = os.path.join(qtbase_cmake, "Qt6")
                tc.variables["Qt6Widgets_DIR"] = os.path.join(qtbase_cmake, "Qt6Widgets")
                tc.variables["Qt6Gui_DIR"] = os.path.join(qtbase_cmake, "Qt6Gui")
                tc.variables["Qt6GuiPrivate_DIR"] = os.path.join(qtbase_cmake, "Qt6GuiPrivate")
                # qtbase does not ship the Qt6LinguistTools module (no
                # lrelease/lupdate on OHOS). Generate a minimal stub config so
                # find_package(Qt6LinguistTools) and lxqt_translate_ts() succeed;
                # .ts translation compilation is skipped (same as lxqt-menu-data).
                self._generate_linguisttools_stub(tc, qtbase_cmake)
        # menu-cache / libexif ship no .pc file; lxqt2-build-tools'
        # FindMenuCache.cmake / FindExif.cmake resolve via pkg-config. Provide
        # .pc stubs and expose every host dependency's pkgconfig dir so those
        # find-modules succeed (XCB's builtin FindXCB also needs pkg-config).
        self._setup_pkgconfig(tc)
        tc.generate()

    def _write_pc(self, path, name, description, version, pkg_folder, libs, includes):
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                f"prefix={pkg_folder}\n"
                f"libdir=${{prefix}}/lib\n"
                f"includedir=${{prefix}}/include\n"
                f"\n"
                f"Name: {name}\n"
                f"Description: {description}\n"
                f"Version: {version}\n"
                f"Libs: -L${{libdir}} -l{libs}\n"
                f"Cflags: -I${{includedir}} -I{includes}\n"
            )

    def _setup_pkgconfig(self, tc):
        pkg_dir = os.path.join(self.generators_folder, "pkgconfig")
        os.makedirs(pkg_dir, exist_ok=True)
        if "menu-cache" in self.dependencies.host:
            mc = self.dependencies.host["menu-cache"].package_folder
            # FindMenuCache.cmake queries pkg-config for the module named
            # "libmenu-cache", so the .pc file must be libmenu-cache.pc with
            # Name: libmenu-cache (not "menu-cache") or pkg-config cannot find it.
            self._write_pc(
                os.path.join(pkg_dir, "libmenu-cache.pc"),
                "libmenu-cache", "LXDE menu cache library", "1.1.0",
                mc, "menu-cache", os.path.join(mc, "include"),
            )
            # NOTE: upstream sources use #include <menu-cache/menu-cache.h>
            # (subdirectory layout) but the menu-cache package installs the
            # header flat at include/menu-cache.h. We patch the two upstream
            # files in source() instead of staging a subdirectory here: a
            # staging include dir inside generators_folder would be a
            # build-prefixed path rejected by CMake 4.1 in the exported
            # INTERFACE_INCLUDE_DIRECTORIES.
        if "libexif" in self.dependencies.host:
            ex = self.dependencies.host["libexif"].package_folder
            self._write_pc(
                os.path.join(pkg_dir, "libexif.pc"),
                "libexif", "EXIF tag parsing library", "0.6.26",
                ex, "exif", os.path.join(ex, "include"),
            )
        if "glib" in self.dependencies.host:
            # The glib package ships .pc files with prefix=/ (they point at the
            # system root instead of the conan package folder), so FindGLIB.cmake
            # (pkg-config based) resolves empty GLIB_INCLUDE_DIRS / empty
            # GLIB_GIO_UNIX_INCLUDE_DIR. The empty strings in the upstream PUBLIC
            # target_include_directories are then interpreted as a relative path
            # (the source dir), which CMake 4.1 rejects in
            # INTERFACE_INCLUDE_DIRECTORIES during install(EXPORT). Pre-seed the
            # cache variables with the real glib package paths instead: find_path/
            # find_library keep pre-seeded cache values, so GLIB_INCLUDE_DIRS is
            # never empty and points at the actual package.
            g = self.dependencies.host["glib"].package_folder
            tc.cache_variables["GLIB_INCLUDE_DIR"] = os.path.join(g, "include", "glib-2.0")
            tc.cache_variables["GLIBCONFIG_INCLUDE_DIR"] = os.path.join(g, "lib", "glib-2.0", "include")
            tc.cache_variables["GLIB_GIO_UNIX_INCLUDE_DIR"] = os.path.join(g, "include", "gio-unix-2.0")
            tc.cache_variables["GLIB_LIBRARIES"] = os.path.join(g, "lib", "libglib-2.0.a")
            # gio's plugin loader (giomodule.c, g_module_*) needs libgmodule, and
            # its gzip decompressor (gzlibdecompressor.c, inflate*) needs zlib.
            # Upstream src/CMakeLists.txt links ${GLIB_GIO_LIBRARIES} only (not
            # ${GLIB_GMODULE_LIBRARIES}), so absorb both here, after libgio for
            # the static link order (dependents first, dependencies last).
            gio_libs = [
                os.path.join(g, "lib", "libgio-2.0.a"),
                os.path.join(g, "lib", "libgmodule-2.0.a"),
            ]
            if "zlib" in self.dependencies.host:
                gio_libs.append(
                    os.path.join(self.dependencies.host["zlib"].package_folder, "lib", "libz.a")
                )
            tc.cache_variables["GLIB_GIO_LIBRARIES"] = ";".join(gio_libs)
            # gobject's closure marshalling (gclosure.c) needs libffi symbols;
            # the glib package bundles libffi.a. Append it after libgobject.
            tc.cache_variables["GLIB_GOBJECT_LIBRARIES"] = os.path.join(g, "lib", "libgobject-2.0.a") + ";" + os.path.join(g, "lib", "libffi.a")
            tc.cache_variables["GLIB_GTHREAD_LIBRARIES"] = os.path.join(g, "lib", "libgthread-2.0.a")
            tc.cache_variables["GLIB_GMODULE_LIBRARIES"] = os.path.join(g, "lib", "libgmodule-2.0.a")
            # The upstream PUBLIC target_include_directories references
            # ${GLIB_INCLUDE_DIRS} (plural); find_package(GLIB) here resolves via
            # CMakeDeps config mode and never composes it. Inject the plural
            # variable directly so it is never empty. Include the glib top-level
            # include/ dir too: it holds libintl.h (the gettext proxy that maps
            # gettext -> g_libintl_gettext with an extern declaration). Without it
            # #include <libintl.h> from glib/gi18n.h falls back to the sysroot
            # header which has no gettext declaration (CI #35010:
            # "use of undeclared identifier 'gettext'" in mountoperation.cpp).
            glib_incs = ";".join([
                os.path.join(g, "include", "glib-2.0"),
                os.path.join(g, "lib", "glib-2.0", "include"),
                os.path.join(g, "include"),
            ])
            tc.variables["GLIB_INCLUDE_DIRS"] = glib_incs
            # _() expands to g_libintl_gettext(), which lives in libintl.a shipped
            # by the glib package. glib's regex engine (gregex.c) also needs
            # pcre2; append both so the static link resolves (dependents first,
            # dependencies last).
            glib_libs = [
                os.path.join(g, "lib", "libglib-2.0.a"),
                os.path.join(g, "lib", "libintl.a"),
            ]
            if "pcre2" in self.dependencies.host:
                glib_libs.append(
                    os.path.join(self.dependencies.host["pcre2"].package_folder, "lib", "libpcre2-8.a")
                )
            tc.cache_variables["GLIB_LIBRARIES"] = ";".join(glib_libs)
        # Directly mutate Conan's aggregated build environment so the value is
        # combined with what CMakeToolchain/CMakeDeps contribute (a separate
        # save_script('conanbuild') would overwrite their env and break cmake).
        self.buildenv.prepend_path("PKG_CONFIG_PATH", pkg_dir)
        # Also surface real .pc files shipped by other dependencies (glib,
        # libxcb, ...) so pkg-config based find-modules can resolve them.
        for dep in self.dependencies.host.values():
            for sub in ("lib", "share"):
                pc_sub = os.path.join(dep.package_folder, sub, "pkgconfig")
                if os.path.isdir(pc_sub):
                    self.buildenv.append_path("PKG_CONFIG_PATH", pc_sub)

    def _generate_linguisttools_stub(self, tc, qtbase_cmake):
        stub_dir = os.path.join(self.generators_folder, "Qt6LinguistTools")
        os.makedirs(stub_dir, exist_ok=True)
        config = os.path.join(stub_dir, "Qt6LinguistToolsConfig.cmake")
        if not os.path.exists(config):
            with open(config, "w", encoding="utf-8") as f:
                f.write(
                    "# Minimal Qt6LinguistTools stub for OHOS (qtbase has no\n"
                    "# LinguistTools/lrelease). Provides the package + no-op\n"
                    "# translation helpers so lxqt_translate_ts() is a no-op.\n"
                    "set(Qt6LinguistTools_FOUND TRUE)\n"
                    "set(Qt6LinguistTools_VERSION 6.11.1)\n"
                    "if(NOT TARGET Qt6::lrelease)\n"
                    "  add_executable(Qt6::lrelease IMPORTED)\n"
                    "  set_target_properties(Qt6::lrelease PROPERTIES "
                    "IMPORTED_LOCATION /bin/true)\n"
                    "endif()\n"
                    "if(NOT TARGET Qt6::lupdate)\n"
                    "  add_executable(Qt6::lupdate IMPORTED)\n"
                    "  set_target_properties(Qt6::lupdate PROPERTIES "
                    "IMPORTED_LOCATION /bin/true)\n"
                    "endif()\n"
                    "function(qt6_add_translation _qm)\n"
                    "  set(${_qm} \"\" PARENT_SCOPE)\n"
                    "endfunction()\n"
                    "function(qt6_create_translation _qm)\n"
                    "  set(${_qm} \"\" PARENT_SCOPE)\n"
                    "endfunction()\n"
                )
        version = os.path.join(stub_dir, "Qt6LinguistToolsConfigVersion.cmake")
        if not os.path.exists(version):
            with open(version, "w", encoding="utf-8") as f:
                f.write(
                    "set(PACKAGE_VERSION 6.11.1)\n"
                    "if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)\n"
                    "  set(PACKAGE_VERSION_COMPATIBLE FALSE)\n"
                    "else()\n"
                    "  set(PACKAGE_VERSION_COMPATIBLE TRUE)\n"
                    "  if(PACKAGE_FIND_VERSION STREQUAL PACKAGE_VERSION)\n"
                    "    set(PACKAGE_VERSION_EXACT TRUE)\n"
                    "  endif()\n"
                    "endif()\n"
                )
        tc.variables["Qt6LinguistTools_DIR"] = stub_dir

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["fm-qt6"]