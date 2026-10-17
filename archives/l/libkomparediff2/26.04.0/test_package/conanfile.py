#!/usr/bin/env python3
"""Conan test_package for libkomparediff2 26.04.0.

Verifies that the KompareDiff2 package can be found via CMake (its own
KompareDiff2Config.cmake, which find_dependency()s Qt6Core/Qt6Widgets and
KF6Config/KF6XmlGui) and that the public DiffModel/Difference API is
callable without an external diff binary. Note the export set carries no
CMake NAMESPACE (upstream install(EXPORT ...) passes none), so consumers
link the plain "KompareDiff2" target.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibKompareDiff2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.18.0")
        self.requires("kxmlgui/6.18.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        self._prepare_stale_cache_compat_links()
        tc = CMakeToolchain(self)
        tc.generate()

        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        # KompareDiff2Config.cmake find_dependency()s Qt6Core/Qt6Widgets and
        # KF6Config/KF6XmlGui; put every dependency's lib/cmake on the prefix
        # path so the whole find_dependency chain resolves (kxmlgui
        # test_package-style loop over the graph).
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
        lines.append(
            f'list(PREPEND CMAKE_PREFIX_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")
        self._prepare_relative_needed_compat_bin()

    def _prepare_relative_needed_compat_bin(self):
        # Prebuilt KF6 binaries from the ohpcd registry also embed RELATIVE
        # DT_NEEDED entries ("../../bin/libKF6ConfigCore.so", same E607 trap
        # class as the stale-cache absolute paths): musl resolves a
        # slash-containing DT_NEEDED against the process CWD with no
        # LD_LIBRARY_PATH fallback, and ctest runs the consumer with
        # CWD=<preset build dir> (so ../.. is this test_package folder).
        # Mirror every dependency's lib*.so* into <test_package>/bin so the
        # relative entries resolve (same idea as the main recipe's
        # _prepare_ctest_runtime_links / _prepare_stale_cache_compat_links).
        import glob
        import shutil

        if self.settings.os != "OHOS":
            return
        compat_bin = os.path.join(self.recipe_folder, "bin")
        os.makedirs(compat_bin, exist_ok=True)
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            for src in glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*")):
                dst = os.path.join(compat_bin, os.path.basename(src))
                if not os.path.exists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    def _prepare_stale_cache_compat_links(self):
        # Prebuilt KF6 binaries from the ohpcd registry embed ABSOLUTE
        # DT_NEEDED paths of their build machine's ~/.cache/conan2 conan
        # home; musl resolves slash-containing DT_NEEDED entries literally
        # (no LD_LIBRARY_PATH fallback, E607 trap class). Package folder
        # names are content hashes, so mirroring each dependency's lib dir
        # under the legacy cache root resolves the stale absolute paths.
        import shutil

        if self.settings.os != "OHOS":
            return
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            folder = dep.package_folder.replace("\\", "/").rstrip("/")
            if not folder.endswith("/p"):
                continue
            pkg_id = os.path.basename(os.path.dirname(folder))
            legacy_pkg_dir = os.path.join(
                os.path.expanduser("~"), ".cache", "conan2", "p", pkg_id, "p"
            )
            legacy_lib = os.path.join(legacy_pkg_dir, "lib")
            if os.path.exists(legacy_lib):
                continue
            live_lib = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(live_lib):
                continue
            os.makedirs(legacy_pkg_dir, exist_ok=True)
            try:
                os.symlink(live_lib, legacy_lib)
            except OSError:
                shutil.copytree(live_lib, legacy_lib, dirs_exist_ok=True)

    def build(self):
        # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the SDK's
        # llvm/lib directory; CI workers may not export it via LD_LIBRARY_PATH
        # (observed on OpenHarmonyPCDeveloper-CI-021). Prepend it so CMake's
        # TryCompile can link. Must not clobber conanbuild env on other hosts.
        sdk_llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
            "/ohos/native/llvm/lib"
        )
        env = Environment()
        if os.path.isdir(sdk_llvm_lib):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        if self.settings.os == "OHOS":
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so which shadows the compatible one; prepend
            # /system/lib64 so the consumer binary resolves the compatible
            # libc++ first (main recipe / kconfig 6.26.0 precedent).
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # The consumer test uses QCoreApplication only; offscreen + writable
        # HOME/XDG keep it headless (same as the upstream test env).
        env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        with env.vars(self).apply():
            cmake = CMake(self)
            # Runs the add_test() consumer binary (CWD = build dir, where the
            # relative DT_NEEDED compat bin at <test_package>/bin resolves).
            cmake.test()
            # Gate L0d additionally requires an explicit self.run() execution.
            # conanfile.run() does not inherit the os.environ applied above,
            # so pass the loader environment inline for the shell to apply.
            ld_dirs = []
            if self.settings.os == "OHOS":
                ld_dirs.append("/system/lib64")
            ld_dirs += [
                os.path.join(p.package_folder, "lib")
                for p in self.dependencies.values()
                if p.package_folder
            ]
            self.run(
                'cd "{dir}" && LD_LIBRARY_PATH="{ld}" QT_QPA_PLATFORM=offscreen'
                ' HOME="{home}" XDG_RUNTIME_DIR="{xdg}" ./test_libkomparediff2'.format(
                    dir=self.build_folder,
                    ld=os.pathsep.join(ld_dirs),
                    home=test_home,
                    xdg=xdg_runtime,
                )
            )
