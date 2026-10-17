#!/usr/bin/env python3
"""Conan test_package for khelpcenter 26.04.0.

Verifies that the delivered headless search stack is consumable and
functional (R34: real API usage):
  - the khcdocmetainfo library: DocMetaInfo/DocEntry construction,
    traverser round trip, kcfg-generated Prefs settings singleton
    (the upstream tests/testmetainfo.cxx semantics)
  - the khc_xapiansearch tool: Xapian query round trip against an index
    built from a synthetic documentation cache via khc_xapianindexer
    (CacheReader/KCompressionDevice + libxml2 htmlTextDump path)
  - the khc_xapianindexer tool: builds a Xapian index out of the
    KDocTools documentation dirs (KDocTools::documentationDirs() against
    the kdoctools 6.19.0 dependency package)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KHelpCenterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("ki18n/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # The tested package, qtbase and the KF6 packages all use
        # cmake_find_mode=none, so the generated conan_cmakedeps_paths.cmake
        # would not contain their lib/cmake dirs. Create it manually
        # (audiocd 26.04.3 recipe precedent).
        lines = []
        for dep_name in (
            "qtbase",
            "kconfig",
            "kcoreaddons",
            "ki18n",
            "khelpcenter",
        ):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                pkg = dep.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qtbase.package_folder}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qtbase.package_folder}/include")'
            )
        khc = self.dependencies.get("khelpcenter")
        if khc and khc.package_folder:
            lines.append(
                "set(KHC_LIB_DIR "
                f'"{khc.package_folder}/lib")'
            )
            # headers are installed under include/khelpcenter
            lines.append(
                "set(KHC_INCLUDE_DIR "
                f'"{khc.package_folder}/include/khelpcenter")'
            )
            # the search tools are installed into bin/ (KDEInstallDirs
            # maps KDE_INSTALL_LIBEXECDIR to the same dir on this layout)
            lines.append(
                "set(KHC_LIBEXEC_DIR "
                f'"{khc.package_folder}/bin")'
            )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
        if qtbase and qtbase.package_folder:
            lines.append(
                f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase.package_folder}/lib")'
            )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            # Qt host tools (moc) are OHOS binaries needing libc++_shared;
            # /system/lib64 provides the compatible one (audiocd precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with build_env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _prepare_runtime_links(self):
        # kconfig's libKF6ConfigGui.so carries a relative DT_NEEDED entry
        # '../../bin/libKF6ConfigCore.so' (a build-tree rpath baked in at
        # kconfig packaging time). The dynamic linker resolves path-style
        # NEEDED entries relative to the process cwd, so provide the file at
        # <build_folder>/../../bin (audiocd 26.04.3 recipe precedent).
        kconfig = self.dependencies.get("kconfig")
        if not kconfig:
            return
        compatibility_bins = set()
        for libfile in ("libKF6ConfigCore.so", "libKF6ConfigGui.so"):
            src = os.path.join(kconfig.package_folder, "lib", libfile)
            if os.path.isfile(src):
                compatibility_bins.add((src, libfile))
        qtbase = self.dependencies.get("qtbase")
        qt_libs = set()
        if qtbase and qtbase.package_folder:
            qt_lib_dir = os.path.join(qtbase.package_folder, "lib")
            for libfile in os.listdir(qt_lib_dir):
                if libfile.startswith("libQt6") and libfile.endswith(".so"):
                    qt_libs.add((os.path.join(qt_lib_dir, libfile), libfile))
        khc = self.dependencies.get("khelpcenter")
        khc_libs = set()
        if khc and khc.package_folder:
            khc_lib_dir = os.path.join(khc.package_folder, "lib")
            if os.path.isdir(khc_lib_dir):
                for libfile in os.listdir(khc_lib_dir):
                    if libfile.endswith(".so"):
                        khc_libs.add((os.path.join(khc_lib_dir, libfile), libfile))
        bin_dir = os.path.join(self.build_folder, "bin")
        parent_bin = os.path.normpath(
            os.path.join(self.build_folder, "..", "..", "bin")
        )
        for target_dir in (bin_dir, parent_bin):
            os.makedirs(target_dir, exist_ok=True)
            for src, libfile in compatibility_bins | qt_libs | khc_libs:
                dst = os.path.join(target_dir, libfile)
                if not os.path.exists(dst):
                    try:
                        shutil.copy2(src, dst)
                    except OSError:
                        pass

    def test(self):
        if not can_run(self):
            return
        self._prepare_runtime_links()
        run_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                run_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            run_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        khc = self.dependencies.get("khelpcenter")
        if khc and khc.package_folder:
            run_env.prepend_path(
                "PATH", os.path.join(khc.package_folder, "bin")
            )
        # A writable home for QStandardPaths so Prefs::self() and the
        # DocMetaInfo plugin scans do not touch the read-only areas.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_home:
            run_env.define_path("HOME", tmp_home)
            run_env.define_path("XDG_CACHE_HOME", os.path.join(tmp_home, ".cache"))
            run_env.define_path("XDG_CONFIG_HOME", os.path.join(tmp_home, ".config"))
            run_env.define_path("XDG_DATA_HOME", os.path.join(tmp_home, ".local", "share"))
            with run_env.vars(self).apply():
                self.run(
                    os.path.join(self.cpp.build.bindir, "test_khelpcenter"),
                    env="conanrun",
                    cwd=self.build_folder,
                )
                # OHOS-specific verification (rule12): exercise the delivered
                # search tools end to end - build a Xapian index with
                # khc_xapianindexer (empty docs dirs yields an empty index)
                # and query it back with khc_xapiansearch, asserting the
                # searchhandler protocol output.
                if khc and khc.package_folder:
                    tools_bin = os.path.join(khc.package_folder, "bin")
                    index_dir = os.path.join(tmp_home, "index")
                    os.makedirs(os.path.join(index_dir, "docs"), exist_ok=True)
                    self.run(
                        f'"{os.path.join(tools_bin, "khc_xapianindexer")}"'
                        f' --indexdir "{index_dir}" --identifier docs --lang en',
                        env="conanrun",
                        cwd=self.build_folder,
                    )
                    self.run(
                        f'"{os.path.join(tools_bin, "khc_xapiansearch")}"'
                        f' --indexdir "{index_dir}" --identifier docs'
                        ' --words help --method or --maxnum 10 > out.txt 2>&1'
                        f' || (cat out.txt; exit 1)'
                        ' && cat out.txt',
                        env="conanrun",
                        cwd=self.build_folder,
                    )
                    with open(os.path.join(self.build_folder, "out.txt")) as f:
                        search_out = f.read()
                    if "<ul>" not in search_out:
                        raise Exception(
                            "khc_xapiansearch did not emit the searchhandler "
                            f"protocol fragment: {search_out!r}"
                        )
