#!/usr/bin/env python3
"""Conan recipe for knewstuff 6.29.0 on HarmonyOS PC.

KNewStuff is the KDE Frameworks 6 library for downloading application assets
from the network (Get Hot New Stuff), producing KF6NewStuffCore,
KF6NewStuffWidgets, a QML plugin and the knewstuff-dialog tool.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation for the
    baseline package
  - BUILD_TESTING=ON and ctest execution for upstream autotests
  - Optional deps (KF6Kirigami, KF6Syndication) are left unfound/disabled so
    the baseline package does not drag in unpublished frameworks
  - Dependencies: qtbase/6.11.1 (Qt6 Gui/Widgets/Xml), qtdeclarative/6.11.1
    (Qt6 Qml/Quick/QuickWidgets), karchive/6.19.0, kconfig/6.18.0,
    kcoreaddons/6.26.0, ki18n/6.26.0, kpackage/6.18.0.2, kwidgetsaddons/6.18.0,
    attica/6.28.0, ecm/6.26.0 (ECM, build tool)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase, qtdeclarative
    and the KF6 packages use cmake_find_mode=none, so CMakeDeps does not add
    their lib/cmake builddirs to CMAKE_PREFIX_PATH
  - 0001-lower-ecm-and-kf-dep-version.patch lowers ECM 6.29.0 -> 6.26.0 and
    KF_DEP_VERSION 6.29.0 -> 6.18.0 to match published ohpcd dependency versions
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KNewStuffConan(ConanFile):
    name = "knewstuff"
    version = "6.29.0.1"
    description = "KDE Frameworks 6 - Support for downloading application assets from the network"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/frameworks/knewstuff"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("karchive/6.19.0")
        self.requires("kconfig/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kpackage/6.18.0.2")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("attica/6.28.0")
        # karchive/6.19.0 的 KF6ArchiveConfig.cmake 激活 find_dependency(ZLIB)/
        # find_dependency(OpenSSL)/PkgConfig::LibZstd；显式声明并提供注入路径，
        # 避免 FindZLIB/FindOpenSSL 在 OHOS 交叉环境查找失败（kiconthemes 同款先例）
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # Qt Designer plugin is for non-cross builds; leave OFF explicitly
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        # Optional KDE frameworks not published on ohpcd; keep out of baseline
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6Kirigami"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6Syndication"] = "ON"

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

        # R05 relocatable linkage: the KF6 deps are published without a DT_SONAME,
        # so linking them by their absolute cache path makes the linker record that
        # machine-private path in DT_NEEDED (cf. the kpackage/6.18.0.1/6.18.0.2
        # DT_NEEDED relocatability fix). Expose
        # their lib dirs to the patched CMakeLists (target_link_directories) so deps
        # are linked by basename (-lKF6CoreAddons...) and DT_NEEDED stays relocatable.
        kf6_dep_lib_dirs = []
        kf6_dep_include_dirs = []
        for dep_name in (
            "karchive",
            "kconfig",
            "kcoreaddons",
            "ki18n",
            "kpackage",
            "kwidgetsaddons",
            "attica",
        ):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                kf6_dep_lib_dirs.append(os.path.join(dep.package_folder, "lib"))
                inc = os.path.join(dep.package_folder, "include")
                kf6_dep_include_dirs.append(inc)
                # KF6 headers live under include/KF6/<Module> (e.g.
                # include/KF6/KI18n/KLocalizedString, include/KF6/Attica/Attica/...);
                # the imported-target configs expose exactly these subdirs, so inject
                # them too for the bare -l consumers that no longer get target usage
                # requirements.
                kf6_root = os.path.join(inc, "KF6")
                if os.path.isdir(kf6_root):
                    for module in sorted(os.listdir(kf6_root)):
                        mod_dir = os.path.join(kf6_root, module)
                        if os.path.isdir(mod_dir):
                            kf6_dep_include_dirs.append(mod_dir)
        if kf6_dep_lib_dirs:
            tc.variables["KNEWSTUFF_DEP_LIB_DIRS"] = ";".join(kf6_dep_lib_dirs)
        # R05 include/link fallback: the KF6 deps are linked by bare -l (no target
        # propagation of include dirs or -L), so inject their include dirs and lib
        # dirs globally. This keeps every CMake target able to find KF6 headers and
        # resolve the -l basenames regardless of the target's own link properties.
        if kf6_dep_include_dirs:
            tc.variables["CMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES"] = ";".join(kf6_dep_include_dirs)
            tc.variables["CMAKE_C_STANDARD_INCLUDE_DIRECTORIES"] = ";".join(kf6_dep_include_dirs)
        # karchive/6.19.0 以静态库（libKF6Archive.a）被裸 -l 链接，其 kzstdfilter 引用
        # ZSTD_* 符号；KF6ArchiveTargets 的 INTERFACE_LINK_LIBRARIES（PkgConfig::LibZstd/
        # ZLIB::ZLIB/OpenSSL::Crypto）因裸 -l 链接不传导，须显式补 -L/-l（kiconthemes 同款）
        kf6_extra_lib_dirs = []
        for dep_name in ("zlib", "openssl", "zstd"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                kf6_extra_lib_dirs.append(os.path.join(dep.package_folder, "lib"))
        kf6_extra_libs = ["-lzstd", "-lz", "-lcrypto", "-lssl"]
        all_link_dirs = kf6_dep_lib_dirs + kf6_extra_lib_dirs
        if all_link_dirs:
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-L{} {}".format(
                " -L".join(all_link_dirs), " ".join(kf6_extra_libs)
            )
            tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-L{} {}".format(
                " -L".join(all_link_dirs), " ".join(kf6_extra_libs)
            )
            # QtQuick plugin is built as a MODULE target; it needs its own -L set
            # to resolve the -lKF6* basenames propagated through KF6NewStuffCore.
            tc.variables["CMAKE_MODULE_LINKER_FLAGS"] = "-L{} {}".format(
                " -L".join(all_link_dirs), " ".join(kf6_extra_libs)
            )

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            lines = []
            self._append_dependency_paths(lines, qtbase.package_folder)
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')

            qtdeclarative = self.dependencies.get("qtdeclarative")
            if qtdeclarative:
                # Qt6Config lives in the qtbase package; Qt6Qml/Qt6Quick/
                # Qt6QuickWidgets configs live in the qtdeclarative package.
                # Qt only searches the additional prefixes listed in
                # QT_ADDITIONAL_PACKAGES_PREFIX_PATH for module configs
                # (qtpositioning/qtshadertools precedent).
                lines.append(
                    f'set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH '
                    f'"{qtdeclarative.package_folder}")'
                )

            for dep_name in (
                "karchive",
                "kconfig",
                "kcoreaddons",
                "ki18n",
                "kpackage",
                "kwidgetsaddons",
                "attica",
            ):
                dep = self.dependencies.get(dep_name)
                if dep and dep.package_folder:
                    self._append_dependency_paths(lines, dep.package_folder)

            # karchive/6.19.0 transitive deps: FindZLIB/FindOpenSSL must resolve
            # against the Conan packages (see kiconthemes precedent).
            zlib_dep = self.dependencies.get("zlib")
            if zlib_dep and zlib_dep.package_folder:
                self._append_dependency_paths(lines, zlib_dep.package_folder)
            openssl_dep = self.dependencies.get("openssl")
            if openssl_dep and openssl_dep.package_folder:
                ossl_pkg = openssl_dep.package_folder
                lines.append(f'set(OPENSSL_ROOT_DIR "{ossl_pkg}" CACHE PATH "")')
                lines.append(
                    f'set(OPENSSL_INCLUDE_DIR "{ossl_pkg}/include" CACHE PATH "")'
                )
                lines.append(
                    f'set(OPENSSL_CRYPTO_LIBRARY '
                    f'"{ossl_pkg}/lib/libcrypto.a" CACHE FILEPATH "")'
                )
                lines.append(
                    f'set(OPENSSL_SSL_LIBRARY '
                    f'"{ossl_pkg}/lib/libssl.a" CACHE FILEPATH "")'
                )
            zstd_dep = self.dependencies.get("zstd")
            if zstd_dep and zstd_dep.package_folder:
                zstd_pkg = zstd_dep.package_folder
                self._append_dependency_paths(lines, zstd_pkg)
                zstd_libs = [
                    os.path.join(zstd_pkg, "lib", "libzstd.so"),
                    os.path.join(zstd_pkg, "lib", "libzstd.a"),
                ]
                zstd_lib = next(
                    (path for path in zstd_libs if os.path.exists(path)),
                    zstd_libs[0],
                )
                lines.append("if(NOT TARGET PkgConfig::LibZstd)")
                lines.append("  add_library(PkgConfig::LibZstd UNKNOWN IMPORTED)")
                lines.append("  set_target_properties(PkgConfig::LibZstd PROPERTIES")
                lines.append(f'    IMPORTED_LOCATION "{zstd_lib}"')
                lines.append(
                    f'    INTERFACE_INCLUDE_DIRECTORIES "{zstd_pkg}/include"'
                )
                lines.append("  )")
                lines.append("endif()")

            lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            lines.append(
                f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase.package_folder}/lib")'
            )
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        with self._library_runtime_env().vars(self).apply():
            cmake.build()
        self._run_upstream_tests()

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
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
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
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _prepare_ctest_runtime_links(self):
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            dst = os.path.join(compatibility_bin, os.path.basename(src))
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def _make_relocatable(self, root):
        # R05 post-build sweep: any DT_NEEDED entry that is an absolute cache path
        # (machine-private, e.g. /storage/Users/currentUser/.conan2/p/...) or a
        # build-tree-relative path (e.g. ../../../bin/...) is rewritten to its bare
        # basename so the packaged artifact resolves via the consumer runtime
        # library path and stays consumable on any cache layout.
        import subprocess

        # readelf/patchelf are not on the default PATH in the Conan subprocess
        # (they resolve through the OHOS toolchain dir), so look them up explicitly.
        def _tool(candidates):
            for cand in candidates:
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
            return shutil.which(candidates[0])

        readelf = _tool(
            [
                "/data/service/hnp/bin/readelf",
                "/usr/bin/readelf",
                "/bin/readelf",
                "readelf",
            ]
        )
        patchelf = _tool(
            [
                "/data/service/hnp/bin/patchelf",
                "/usr/bin/patchelf",
                "/bin/patchelf",
                "patchelf",
            ]
        )
        if not readelf or not patchelf:
            self.output.warning(
                "R05: readelf/patchelf not found (readelf={}, patchelf={}); "
                "skipping relocatable NEEDED sweep".format(readelf, patchelf)
            )
            return

        artifacts = []
        for subdir in ("bin", "lib"):
            base = os.path.join(root, subdir)
            if not os.path.isdir(base):
                continue
            for name in os.listdir(base):
                p = os.path.join(base, name)
                if os.path.isfile(p) and (name.endswith(".so") or os.access(p, os.X_OK)):
                    artifacts.append(p)
        for p in artifacts:
            try:
                dump = subprocess.run(
                    [readelf, "-d", p], capture_output=True, text=True, timeout=30
                ).stdout
            except Exception:
                continue
            for line in dump.splitlines():
                m = re.search(r"\(NEEDED\)\s+Shared library: \[(.*)\]", line)
                if not m:
                    continue
                needed = m.group(1)
                if "/" not in needed:
                    continue
                basename = os.path.basename(needed)
                try:
                    subprocess.run(
                        [patchelf, "--replace-needed", needed, basename, p],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    self.output.info(
                        "R05 relocatable: {} -> {} in {}".format(needed, basename, p)
                    )
                except subprocess.CalledProcessError as e:
                    self.output.warning(
                        "R05 patchelf failed on {} ({}): {}".format(p, needed, e.stderr.strip())
                    )

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6NewStuffCore", "KF6NewStuffWidgets"]
        self.cpp_info.bindirs = ["bin"]
