#!/usr/bin/env python3
"""Conan recipe for kdiagram 3.0.1 — KDE charting libraries (KChart + KGantt).

kdiagram is the KDE diagram library module shipping two independent
libraries:

  - KChart6 (libKChart6.so.3): Cartesian/Polar/Ternary chart engine
    (Chart/AbstractDiagram/coordinate planes/legends/axes) used by e.g.
    eventviews (KDE PIM dependency line) and KLatexFormula.
  - KGantt6 (libKGantt6.so.3): Gantt chart scene/view toolkit
    (GraphicsScene/GraphicsView/DateTimeGrid/ConstraintModel).

It is an independently released KDE module (not a Framework), Qt6-based
since 2.7.90/3.0.0 (upstream QT_REQUIRED_VERSION 6.5.0, KF_MIN_VERSION
5.245.0 ECM-only — no KF6 framework libraries are linked, verified by a
full-tree find_package scan: ECM + Qt6{Svg,Widgets} only, plus optional
Qt6Test/Qt6Sql guarded lookups).

Upstream test suite: 23 ctest targets via ecm_add_test
  - qtests/ (19 KChart QTests: AttributesModel, AxisOwnership,
    BarDiagrams, CartesianDiagramDataCompressor, CartesianPlanes,
    ChartElementOwnership, Cloning, DrawIntoPainter, Legends,
    LineDiagrams, Measure, Palette, ParamVsParam, PieDiagrams,
    PolarDiagrams, PolarPlanes, QLayout, RelativePosition,
    WidgetElementOwnership)
  - src/KGantt/test/ (4: KGanttConstraint, KGanttConstraintModel,
    KGanttMultiItems, KGanttView)
tests/ (DelayedData/RootIndex/tests-Gantt) are interactive example
executables registered without add_test — not part of the ctest count.

OHOS adaptations (patches/0001-ohos-drop-printsupport.patch):
* Qt6::PrintSupport removed from the top-level find_package component
  list, the KGantt6 target_link_libraries PRIVATE line and the
  KGantt6Config.cmake.in find_dependency chain: the published
  qtbase/6.11.1 line is built with PrintSupport=OFF (kgraphviewer
  26.04.0 precedent; the platform has no printing stack).
* -DQT_NO_PRINTER defined at the top level: the upstream HAVE_PRINTER
  guards (kganttgraphicsscene.cpp:36-44) then turn every KGantt
  printing entry point into a no-op — the API surface (print/printDiagram
  overloads) is preserved for source compatibility.
* QPrinter/QPrintDialog/QPrintPreviewDialog includes and the remaining
  unguarded printing function bodies in examples/tests are guarded with
  #ifndef QT_NO_PRINTER (the majority already carried the upstream
  guard).

Dependency line: qtbase/6.11.1 (Core/Gui/Widgets/Test/Network) +
qtsvg/6.11.1 (Qt6::Svg for KChart6 PRIVATE) + ecm/6.26.0 (tool_requires).
No KF6 framework libraries are needed — do not add kcoreaddons/ki18n.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class KDiagramConan(ConanFile):
    name = "kdiagram"
    version = "3.0.1"
    description = (
        "KDE charting libraries: KChart (Cartesian/Polar/Ternary charts) "
        "and KGantt (Gantt scene/view toolkit), Qt6 edition (3.0.1)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/graphics/kdiagram"
    url = "https://download.kde.org/stable/kdiagram/3.0.1/kdiagram-3.0.1.tar.xz"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 Core/Gui/Widgets (+ Test for the upstream autotests).
        self.requires("qtbase/6.11.1")
        # Qt6::Svg — KChart6 links it PRIVATE (qtsvg 6.11.1, kfourinline
        # 26.04.0 / kgraphviewer 26.04.0 consumption precedent).
        self.requires("qtsvg/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kdiagram is adapted for Linux and OHOS, not "
                f"{self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        # CMakeDeps generates configs for the non-Qt graph packages
        # (none beyond qtbase/qtsvg today, kept for graph stability).
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (no Platform/HarmonyOS module
        # in CMake). OHOS is POSIX: force the Linux platform (chain-wide
        # convention; abcmidi/adios2/kpeople5/kinfocenter precedent).
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # Run the full upstream autotest suite (23 ctest targets).
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        # OHOS is not in the KDE platform list (kfourinline precedent).
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Skip translation catalog generation: poqm/*.po -> .qm needs the
        # gettext msgfmt toolchain (audiocd 26.04.3 precedent;
        # ecm_process_po_files_as_qm returns early under this flag).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # KDEInstallDirs single-prefix layout on conan (kgoldrunner /
        # qqc2-breeze-style / kinfocenter precedents).
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        # OHOS loader workaround (audiocd 26.04.3 / kfourinline 26.04.0
        # precedent): default lld 0x10000 max-page-size can split
        # .dynsym/.dynstr into separate high-address RW LOAD segments the
        # OHOS musl loader refuses to mmap; pin the 4K page layout.
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            self._configure_ohos_shared_library_rules(tc)
        # ECM's own ECMConfig.cmake sets ECM_MODULE_PATH but the
        # CMakeDeps-generated layout does not propagate the variable the
        # project relies on — set it manually (audiocd/kgoldrunner/
        # kinfocenter precedent).
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )
        # Qt6 split-package component discovery: Qt6Svg lives in the qtsvg
        # package (kfourinline 26.04.0 / libkdegames verified pattern);
        # Qt discovers additional components through the official
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH hook.
        qt_extra = []
        for dep_name in ("qtsvg",):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                qt_extra
            )
        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        # The OHOS conan toolchain does not emit -Wl,-soname by itself;
        # KChart6/KGantt6 need sonames so consumers reference
        # libKChart6.so.3 / libKGantt6.so.3 instead of build-tree paths
        # (qqc2-breeze-style 6.7.5 / kinfocenter 6.7.2 precedent).
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        save(
            self,
            rules,
            "\n".join((
                'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP ":")',
            )) + "\n",
        )
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

    def _write_cmake_paths(self):
        # qtbase/qtsvg use cmake_find_mode=none, so CMakeDeps doesn't put
        # their lib/cmake dirs on CMAKE_PREFIX_PATH. Write
        # conan_cmakedeps_paths.cmake manually (kfourinline/libkdegames
        # precedent).
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))
                add_unique(modules, os.path.join(dep.package_folder, "lib", "cmake"))
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            add_unique(prefixes, os.path.join(ecm_share, "cmake"))
            for rel in ("modules", "find-modules", "kde-modules"):
                add_unique(modules, os.path.join(ecm_share, rel))
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # The PrintSupport trim patch is needed on every target platform
        # consuming the PrintSupport=OFF qtbase line; apply unconditionally
        # (the QT_NO_PRINTER guards keep the tree buildable on stock Linux
        # Qt6 as well).
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        self._prepare_ctest_runtime_links()
        test_env = self._runtime_env(include_build=True)
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        # The upstream QTests need a Qt platform plugin: the offscreen QPA
        # ships in the qtbase package plugins dir (kinfocenter 6.7.2
        # precedent).
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _prepare_ctest_runtime_links(self):
        """Mirror the build-tree shared libraries into bin/ + lib/ of the
        build folder so every ctest working directory resolves the
        DT_NEEDED entries (libKChart6.so.3 in src/KChart, libKGantt6.so.3
        in src/KGantt, libtesttools.so in examples/tools; ctest runs each
        test binary from its own binary dir — kinfocenter 6.7.2 /
        kcmutils 6.26.0 precedent, extended with a glob over the whole
        build tree)."""
        import shutil as _shutil

        so_files = []
        for pattern in (
            os.path.join(self.build_folder, "src", "KChart", "lib*.so*"),
            os.path.join(self.build_folder, "src", "KGantt", "lib*.so*"),
            os.path.join(self.build_folder, "examples", "tools", "lib*.so*"),
        ):
            so_files.extend(glob.glob(pattern))
        so_files.extend(
            glob.glob(os.path.join(self.build_folder, "lib", "lib*.so*"))
        )
        so_files.extend(
            glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        )
        # Collect every directory holding a test binary (qtests/*,
        # src/KGantt/test) so the loader resolves from each CWD too.
        compatibility_dirs = {
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.build_folder, "lib"),
        }
        for pattern in (
            os.path.join(self.build_folder, "qtests", "*"),
            os.path.join(self.build_folder, "src", "KGantt", "test"),
        ):
            for path in glob.glob(pattern):
                if os.path.isdir(path):
                    compatibility_dirs.add(path)
        for cdir in compatibility_dirs:
            os.makedirs(cdir, exist_ok=True)
        for src in so_files:
            for cdir in compatibility_dirs:
                dst = os.path.join(cdir, os.path.basename(src))
                if os.path.exists(src) and not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        _shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        copy(self, "LICENSE.GPL.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "LICENSES",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._sign_ohos_payload()

    def _sign_ohos_payload(self):
        """Re-sign every packaged ELF for the OHOS loader.

        Freshly linked OHOS ELF files carry an invalid linker stub
        .codesign section; dlopen() validates the code signature and
        rejects the file with EACCES before LD_LIBRARY_PATH is even
        consulted — verified locally: after remove-section +
        binary-sign-tool -selfSign 1 the same payload loads. Sign
        libKChart6/libKGantt6 so the consumer test (QLibrary::load) and
        any downstream consumer can dlopen them (kgoldrunner 26.04.0 /
        kinfocenter 6.7.2 precedent, applied at package() level).
        """
        import fnmatch
        import subprocess

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.warning(
                "OHOS signing tools not found; skipping payload signing"
            )
            return
        count = 0
        for root, _, files in os.walk(self.package_folder):
            for fn in files:
                path = os.path.join(root, fn)
                if os.path.islink(path) or not fnmatch.fnmatch(fn, "*.so*"):
                    continue
                try:
                    with open(path, "rb") as f:
                        if f.read(4) != b"\x7fELF":
                            continue
                except OSError:
                    continue
                # The stub section may or may not exist; either way the
                # signer rewrites a valid one.
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", path],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", path,
                     "-selfSign", "1"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                count += 1
        self.output.info("OHOS payload signed: %d ELF files" % count)

    def _runtime_env(self, include_build=False):
        # Host tools (moc/uic/rcc) are OHOS binaries needing
        # libc++_shared from /system/lib64 plus the dependency lib dirs
        # on LD_LIBRARY_PATH (audiocd 26.04.3 / kfourinline 26.04.0
        # precedents).
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def package_info(self):
        # The package installs its own KChart6Config.cmake /
        # KGantt6Config.cmake (find_dependency on Qt6Core/Qt6Svg/
        # Qt6Widgets) with the KChart6::KChart6 and KGantt6::KGantt6
        # exported targets; use cmake_find_mode=none so CMakeDeps doesn't
        # shadow them (kpeople5 5.116.0 precedent).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KChart6", "KGantt6"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
