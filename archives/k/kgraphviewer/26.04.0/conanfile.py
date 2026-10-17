#!/usr/bin/env python3
"""Conan recipe for kgraphviewer 26.04.0 on HarmonyOS PC.

kgraphviewer is the KDE Graphviz DOT graph viewer (release-service
26.04.0). The package ships:
  - bin/kgraphviewer          (GUI application)
  - lib/libkgraphviewer.so.0  (kgraphviewerlib, SHARED)
  - lib/plugins/kf6/parts/kgraphviewerpart.so  (KParts plugin)
  - lib/libKF6{Parts,XmlGui,JobWidgets,ConfigWidgets}.so.6
    (vendored KF6 frameworks, see below)

OHOS-specific adaptations:
  - Vendored KF6 frameworks (E277 build-vendored-to-staging): kparts is not
    published on ohpcd at all, and kxmlgui/kconfigwidgets/kjobwidgets only
    exist on the 6.18 track while kio (KIOCore, a hard kparts dependency)
    is only published at 6.26. Consuming both tracks in one conan graph
    forces version overrides that invalidate every published KF6 package_id
    and trigger full source rebuilds whose in-recipe ctest suites fail in
    the OHOS sandbox (CI rounds 4-6 measured). The staging chain below
    therefore builds kconfigwidgets -> kjobwidgets -> kxmlgui -> kparts
    (6.18.0, sha256-pinned, BUILD_TESTING=OFF) against the published 6.26
    line and ships the four .so + their lib/cmake configs inside this
    package. They are built SHARED because KParts/XmlGui are QObject
    frameworks consumed by the app, the lib and the plugin: a static
    archive linked into several shared objects would duplicate Q_OBJECT
    metaobjects and break qobject_cast at runtime.
  - Staging patches:
      0007: kparts — drop its PRIVATE KF6::KIOWidgets link (sources only
            use KIOCore classes; kio is KIOCORE_ONLY here);
      0015: kparts — NavigationExtension::pasteRequest drops its
            KUriFilter usage (not shipped by the KIOCORE_ONLY kio;
            pasted text is opened as a plain user-input URL);
  - E537 relocatable link (generate-time, no source patch): the published
    KF6/Qt5Compat dependency libraries have no DT_SONAME, so their absolute
    cache paths leak into DT_NEEDED. The generated conan_cmakedeps_paths.cmake
    hooks find_package in every project of the build (app + vendored staging)
    and swaps each affected imported target's location for a private
    patchelf --set-soname proxy copy (link-time input only, never shipped);
    ld then records just the soname basename, resolved via LD_LIBRARY_PATH.
      0011/0012/0013: kxmlgui — drop Qt6 PrintSupport (component, link
            line, kshortcutseditor print feature -> exported no-op);
      0014: kjobwidgets — drop the KF6Notifications dependency together
            with the KNotificationJobUiDelegate convenience class (nothing
            in kgraphviewer/kparts uses it; knotifications is only
            published on the 6.18 track).
  - patch 0001: drop Qt6 PrintSupport and DBus from the top-level
    find_package: the published qtbase/6.11.1 line has PrintSupport
    disabled and FEATURE_dbus=OFF (kio/knotifications USE_DBUS=OFF
    platform precedent; no session bus in the OHOS sandbox).
  - patch 0003-0006: the simple printing subsystem is compiled out
    (sources/ui/link), DotGraphView::print/printPreview/pageSetup stay as
    exported no-ops, the part drops the print GUI actions (.rc too).
  - patch 0016: KgvPageFormat::defaultFormat() returns DIN A4 directly
    (QPrinterInfo/Qt6::PrintSupport unavailable; DotGraphView::
    hideToolsWindows becomes a no-op in patch 0004).
  - patch 0002: FindGraphviz version fallback for graphviz 13 headers
    (GRAPHVIZ_VERSION instead of PACKAGE_VERSION).
  - E447-style cache-variable bridge: generate() predefines the bundled
    FindGraphviz module's cache variables with isfile-guarded absolute
    paths into the conan graphviz package.
  - KF_IGNORE_PLATFORM_CHECK / KF_SKIP_PO_PROCESSING / manual ECM_MODULE_PATH
    and conan_cmakedeps_paths.cmake (kio 6.26.0 recipe precedent).
  - QT_ADDITIONAL_PACKAGES_PREFIX_PATH points Qt6Config.cmake (qtbase
    package) at the qtsvg/qt5compat packages so the Qt6Svg and
    Qt6Core5Compat components resolve across conan package prefixes
    (alligator/26.04.0 recipe precedent).
  - CMAKE_SHARED_LIBRARY_SONAME_*_FLAG (CMake has no Platform/HarmonyOS
    module) so every shipped .so gets a DT_SONAME (E537, CI L5a).
  - Explicit linker closure: -L/-Wl,-rpath-link for every dependency
    libdir (implement policy 5).
  - E132: OHOS SDK lld libxml2.so.16 declared + LD_LIBRARY_PATH injected.
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import build_jobs
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    patch,
)

KDE_FRAMEWORKS_URL = "https://download.kde.org/stable/frameworks/6.18"

# Vendored staging chain, built in order into a shared staging prefix.
# (name, version, sha256, patches applied from patches/)
STAGING_FRAMEWORKS = [
        (
            "kconfigwidgets",
            "6.18.0",
            "aa5a7be6278a19733f77e6a435f84c3e71926b28f1ac3766313778890d640813",
            [],
        ),
        (
            "kjobwidgets",
            "6.18.0",
            "e739ff254c4fa34c0de00aa2d9deee138135d99cd0b46ef5db253c18c02bce98",
            ["0014-kjobwidgets-drop-knotifications.patch"],
        ),
        (
            "kxmlgui",
            "6.18.0",
            "6d5e240c835668419ac036666fa4c99e3479795c6988100763f810ca8835c401",
            [
                "0011-kxmlgui-CMakeLists.patch",
                "0012-kxmlgui-src-CMakeLists.patch",
                "0013-kxmlgui-kshortcutseditor.patch",
            ],
        ),
        (
            "kparts",
            "6.18.0",
            "846e522e6aff2a219064a52e9baeefdfbcbea71dadb1810b9c58cb9c41821604",
            [
                "0007-vendored-kparts-drop-kiowidgets.patch",
                "0015-vendored-kparts-navigationextension-no-urifilter.patch",
            ],
        ),
]

STAGING_SONAME_CHECKS = {
    "kconfigwidgets": "libKF6ConfigWidgets.so.6",
    "kjobwidgets": "libKF6JobWidgets.so.6",
    "kxmlgui": "libKF6XmlGui.so.6",
    "kparts": "libKF6Parts.so.6",
}

# E537 relocatable link (injected into conan_cmakedeps_paths.cmake, which the
# CI toolchain includes in every project of the build — the application and
# each vendored staging framework): the published KF6/Qt5Compat dependency
# libraries ship without DT_SONAME, so CMake passes their absolute Conan-cache
# paths to the linker and ld records those machine-private paths in DT_NEEDED.
# Hook find_package so that, right after a config defines one of these targets,
# its link location is swapped for a private proxy copy carrying a stable
# DT_SONAME (patchelf --set-soname): ld records only the soname basename, and
# LD_LIBRARY_PATH resolves it to the real published library at runtime. The
# proxies live in each project's build dir and are link-time inputs only —
# never shipped (patchelf-rewritten .so files are refused by the HMDFS loader
# at runtime, so this must not replace any published artifact).
OHOS_E537_FIXUP_CMAKE = r"""
# OHOS E537: relocatable linkage for soname-less published KF6 dependencies.
set(OHOS_SONAME_LESS_DEPS
    KF6::CoreAddons KF6::I18n KF6::ConfigCore KF6::ConfigGui
    KF6::ColorScheme KF6::GuiAddons KF6::WidgetsAddons KF6::Service
    KF6::ItemViews KF6::WindowSystem KF6::Codecs Qt6::Core5Compat
)
set(OHOS_SONAME_PROXIES "${CMAKE_BINARY_DIR}/ohos-soname-proxies")
macro(find_package)
  _find_package(${ARGV})
  ohos_relocatable_link_fixup()
endmacro()
function(ohos_relocatable_link_fixup)
  foreach(_t ${OHOS_SONAME_LESS_DEPS})
    if(NOT TARGET ${_t})
      continue()
    endif()
    get_target_property(_done ${_t} OHOS_SONAME_PROXY)
    if(_done)
      continue()
    endif()
    set_property(TARGET ${_t} PROPERTY OHOS_SONAME_PROXY TRUE)
    set(_loc "")
    foreach(_p IMPORTED_LOCATION_RELEASE IMPORTED_LOCATION)
      if(NOT _loc OR _loc STREQUAL "_loc-NOTFOUND")
        get_target_property(_loc ${_t} ${_p})
      endif()
    endforeach()
    if(_loc MATCHES "^/")
      get_filename_component(_b "${_loc}" NAME)
      set(_px "${OHOS_SONAME_PROXIES}/${_b}")
      set(_ok FALSE)
      if(EXISTS "${_px}")
        set(_ok TRUE)
      else()
        file(MAKE_DIRECTORY "${OHOS_SONAME_PROXIES}")
        find_program(OHOS_PATCHELF_EXE patchelf HINTS /data/service/hnp/bin)
        if(OHOS_PATCHELF_EXE)
          file(COPY_FILE "${_loc}" "${_px}")
          execute_process(
            COMMAND "${OHOS_PATCHELF_EXE}" --set-soname "${_b}" "${_px}"
            RESULT_VARIABLE _rc OUTPUT_QUIET ERROR_QUIET
          )
          if(_rc EQUAL 0)
            set(_ok TRUE)
          else()
            file(REMOVE "${_px}")
          endif()
        endif()
      endif()
      if(_ok)
        set_target_properties(${_t} PROPERTIES
          IMPORTED_LOCATION "${_px}"
          IMPORTED_LOCATION_RELEASE "${_px}")
      endif()
    endif()
  endforeach()
endfunction()
"""


class KgraphviewerConan(ConanFile):
    name = "kgraphviewer"
    version = "26.04.0"
    description = "KDE Graphviz DOT graph viewer (application, library and KParts plugin)"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/graphics/kgraphviewer"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)
        # Staging patches apply to the vendored framework sources (fetched
        # in build()), not to the kgraphviewer source, so they are exported
        # explicitly and kept out of conandata.yml. The source folder is
        # patches/ itself so the files land directly in
        # export_sources_folder/patches (next to the conandata ones).
        staging_src = os.path.join(self.recipe_folder, "patches")
        staging_dst = os.path.join(self.export_sources_folder, "patches")
        for name in (
            "0007",
            "0011",
            "0012",
            "0013",
            "0014",
            "0015",
        ):
            copy(
                self,
                "{}-*.patch".format(name),
                staging_src,
                staging_dst,
            )

    def requirements(self):
        # qtbase/6.11.1 is the line every published KF6 package (kio 6.26,
        # kservice 6.26, ...) and qtsvg/qt5compat 6.11.1 is built against;
        # staying on it keeps published dependency binaries reusable. It is
        # built with FEATURE_dbus=OFF and PrintSupport disabled — the D-Bus
        # single-instance mechanism and the printing subsystem are compiled
        # out (see the header docstring and notes.md).
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("qt5compat/6.11.1")
        # Header-only usage (spirit classic); 1.90.0.3 matches graphviz's
        # poppler pin, so no override is needed.
        self.requires("boost/1.90.0.3")
        self.requires("graphviz/13.1.2")
        # KF6 6.26 published line: direct links of kgraphviewerlib / app /
        # the vendored staging frameworks.
        self.requires("kconfig/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("ki18n/6.26.0")
        self.requires("kwidgetsaddons/6.26.0")
        self.requires("karchive/6.26.0")
        self.requires("kservice/6.26.0")
        self.requires("kio/6.26.0")  # KF6KIOCore (KIOCORE_ONLY baseline)
        self.requires("kcolorscheme/6.26.0")
        self.requires("kguiaddons/6.26.0")
        self.requires("kiconthemes/6.26.0")
        self.requires("kitemviews/6.26.0")
        self.requires("kwindowsystem/6.26.0")
        self.requires("kcodecs/6.18.0")  # kconfigwidgets staging dep
        # E132: the OHOS SDK lld depends on libxml2.so.16 at link time.
        self.requires("libxml2/2.15.3")
        # Version unifications inside the graphviz closure (same-minor
        # raises to the newer published build; measured in CI rounds 2-5):
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("fontconfig/2.18.1.1", override=True)
        self.requires("expat/2.8.2.1", override=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── vendored staging paths (deterministic, derived from the conan
    # build folder) ──
    def _staging_prefix(self):
        return os.path.join(self.build_folder, "kde-staging")

    def _staging_srcdir(self, name):
        return os.path.join(self.build_folder, "kde-src", name)

    def _staging_builddir(self, name):
        return os.path.join(self.build_folder, "kde-build", name)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "ON"
        # GNUInstallDirs would pick lib64 for the OHOS triplet; the conan
        # package layout convention is lib/ (kio/kxmlgui precedent).
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_INSTALL_BINDIR"] = "bin"
        tc.variables["CMAKE_INSTALL_PLUGINDIR"] = "lib/plugins"
        # CMake has no Platform/HarmonyOS module: provide the SONAME flag so
        # libkgraphviewer.so and the staged KF6 libs get DT_SONAMEs (kio
        # 6.26.0 precedent, CI L5a gate, E537).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        # E447: bridge the conan graphviz package into the bundled
        # FindGraphviz module via its cache variables.
        self._bridge_graphviz(tc)
        # find_package(Boost) support for the header-only spirit usage.
        boost = self.dependencies.get("boost")
        if boost and boost.package_folder:
            tc.cache_variables["Boost_INCLUDE_DIR"] = os.path.join(
                boost.package_folder, "include"
            )

        # The qtbase package's Qt6Config.cmake locates Qt component packages
        # (Qt6Svg from qtsvg, Qt6Core5Compat from qt5compat) only inside its
        # own prefix unless the extra prefixes are listed in
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH (Qt's official split-prefix
        # mechanism; alligator/26.04.0 recipe precedent).
        qt_component_prefixes = []
        for dep_name in ("qtsvg", "qt5compat"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_component_prefixes.append(dep.package_folder)
        if qt_component_prefixes:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                qt_component_prefixes
            )

        # Explicit linker closure: -L and -Wl,-rpath-link for every
        # dependency libdir plus the vendored staging libdir. The paths are
        # written unquoted on purpose: embedded quotes break the toolchain's
        # set(CMAKE_*_LINKER_FLAGS "...") into a CMake list (-L;/path" ...)
        # and invalidate every -L entry (measured in CI r16-r17); the conan
        # cache paths on this platform contain no spaces.
        link_dirs = self._link_dirs()
        flags = " ".join(
            "-L{} -Wl,-rpath-link,{}".format(d, d) for d in link_dirs
        )
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = flags
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = flags
        tc.variables["CMAKE_MODULE_LINKER_FLAGS"] = flags

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated one does not (kio 6.26.0 precedent).
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        tc.generate()

        # E132: expose the SDK lld's libxml2.so.16 to build and test envs.
        libxml2 = self.dependencies.get("libxml2")
        if libxml2:
            libxml2_lib = os.path.join(libxml2.package_folder, "lib")
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", libxml2_lib)
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", libxml2_lib)

        self._write_cmake_paths(ecm)

    def _bridge_graphviz(self, tc):
        gv = self.dependencies.get("graphviz")
        if not gv or not gv.package_folder:
            return
        incdir = os.path.join(gv.package_folder, "include")
        libdir = os.path.join(gv.package_folder, "lib")
        tc.cache_variables["Graphviz_INCLUDE_DIRECTORIES"] = incdir
        for var, name in (
            ("Graphviz_GVC_LIBRARY", "gvc"),
            ("Graphviz_CDT_LIBRARY", "cdt"),
            ("Graphviz_GRAPH_LIBRARY", "cgraph"),
            ("Graphviz_PATHPLAN_LIBRARY", "pathplan"),
        ):
            lib = os.path.join(libdir, "lib{}.so".format(name))
            if not os.path.isfile(lib):
                candidates = sorted(
                    glob.glob(
                        os.path.join(libdir, "lib{}.so.*".format(name))
                    )
                )
                if not candidates:
                    raise ConanException(
                        "graphviz package has no lib{}.so[.*] in {}".format(
                            name, libdir
                        )
                    )
                lib = candidates[0]
            tc.cache_variables[var] = lib
        # Defensive fallback; the patched module normally reads the version
        # from graphviz_version.h.
        tc.cache_variables["Graphviz_VERSION"] = str(gv.ref.version)

    def _link_dirs(self):
        dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                d = os.path.join(dep.package_folder, "lib")
                if d not in dirs:
                    dirs.append(d)
        staging_lib = os.path.join(self._staging_prefix(), "lib")
        if staging_lib not in dirs:
            dirs.append(staging_lib)
        return dirs

    def _write_cmake_paths(self, ecm):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        # The vendored staging frameworks are the only providers of
        # KF6Parts/KF6XmlGui/KF6JobWidgets/KF6ConfigWidgets.
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(
                os.path.join(self._staging_prefix(), "lib", "cmake")
            )
        )
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")',
                    ]
                )
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        lines.append(OHOS_E537_FIXUP_CMAKE)
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        if self.settings.os != "OHOS":
            # Non-OHOS: upstream build against system dependencies.
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
            return
        apply_conandata_patches(self)
        # Vendored KF6 staging chain first: the kgraphviewer configure
        # needs find_package(KF6 Parts/XmlGui) to hit the staging configs
        # (E277 build-vendored-to-staging).
        self._build_vendored_staging()
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _staging_patches_path(self, patch_name):
        return os.path.join(
            self.export_sources_folder, "patches", patch_name
        )

    def _build_vendored_staging(self):
        prefix = self._staging_prefix()
        toolchain = os.path.join(
            self.generators_folder, "conan_toolchain.cmake"
        )
        jobs = build_jobs(self)
        for name, version, sha256, patch_names in STAGING_FRAMEWORKS:
            src = self._staging_srcdir(name)
            build_dir = self._staging_builddir(name)
            os.makedirs(build_dir, exist_ok=True)
            get(
                self,
                "{}/{}-{}.tar.xz".format(KDE_FRAMEWORKS_URL, name, version),
                filename="{}-{}.tar.xz".format(name, version),
                sha256=sha256,
                strip_root=True,
                destination=src,
            )
            for patch_name in patch_names:
                patch(
                    self,
                    src,
                    patch_file=self._staging_patches_path(patch_name),
                )
            args = [
                'cmake -S "{}" -B "{}"'.format(src, build_dir),
                '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
                '-DCMAKE_INSTALL_PREFIX="{}"'.format(prefix),
                "-DBUILD_TESTING=OFF",
                "-DUSE_DBUS=OFF",
                "-DWITH_X11=OFF",
                "-DBUILD_DESIGNERPLUGIN=OFF",
                "-DBUILD_PYTHON_BINDINGS=OFF",
            ]
            if name == "kxmlgui":
                # kglobalaccel is not published on ohpcd; kxmlgui supports
                # building without it (HAVE_GLOBALACCEL stays undefined).
                args.append("-DFORCE_DISABLE_KGLOBALACCEL=ON")
            with self._cmake_build_env().vars(self).apply():
                self.run(" ".join(args))
                self.run(
                    'cmake --build "{}" --target install -j{}'.format(
                        build_dir, jobs
                    )
                )
            staged = os.path.join(prefix, "lib", STAGING_SONAME_CHECKS[name])
            if not os.path.isfile(staged):
                raise ConanException(
                    "vendored {} build did not produce {}".format(
                        name, staged
                    )
                )

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the
            # SDK's llvm/lib directory (kio 6.26.0 precedent).
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos"
                    "/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so; prepend /system/lib64 so the loader resolves
            # the compatible one first (kconfig/kcrash/kio precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        runtime_env.prepend_path(
            "LD_LIBRARY_PATH",
            os.path.join(self._staging_prefix(), "lib"),
        )
        for rel in ("bin", "lib"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.install()
        if self.settings.os == "OHOS":
            # Ship the vendored KF6 frameworks inside this package.
            staging = self._staging_prefix()
            copy(
                self,
                "*",
                os.path.join(staging, "lib"),
                os.path.join(self.package_folder, "lib"),
            )
            copy(
                self,
                "*",
                os.path.join(staging, "include"),
                os.path.join(self.package_folder, "include"),
            )

    def package_info(self):
        # The package ships its own vendored KF6 framework configs
        # (KF6Parts/KF6XmlGui/KF6JobWidgets/KF6ConfigWidgets) and
        # KGraphViewerPartConfig.cmake; use cmake_find_mode=none so
        # CMakeDeps does not shadow them (kio 6.26.0 precedent).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["kgraphviewer"]
        self.cpp_info.bindirs = ["bin"]
        # Consumers need this package's lib/ for libkgraphviewer.so.0 and
        # the vendored KF6 framework libraries.
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
