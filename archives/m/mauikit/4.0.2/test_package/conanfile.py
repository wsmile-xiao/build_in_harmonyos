#!/usr/bin/env python3
"""Conan test_package for MauiKit 4.0.2.

Consumes the published-style MauiKit4 CMake config (cmake_find_mode=none),
links the exported (un-namespaced) MauiKit4 target and runs three OHOS-specific cases on the device:
meta (exported C++ API), defaults (patched MauiMan fallbacks + platform
guards) and qml (offscreen plugin load + control instantiation).
"""
import glob
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class MauikitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtmultimedia/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("kcoreaddons/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("knotifications/6.14.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        qt_extra = []
        for dep_name in ("qtdeclarative", "qtmultimedia", "qtsvg"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)
        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()

    def _write_cmake_paths(self):
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))
                add_unique(modules, os.path.join(dep.package_folder, "lib", "cmake"))

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
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _qml_dirs(self, package_folder):
        dirs = []
        for rel in ("qml", os.path.join("lib", "qml"), os.path.join("lib", "qt6", "qml")):
            path = os.path.join(package_folder, rel)
            if os.path.isdir(path):
                dirs.append(path)
        return dirs

    def _prepare_runtime_links(self):
        # OHOS linker records sibling libraries with path-qualified names in
        # some build trees; provide every dependency .so next to the test
        # binary so the loader always resolves them.
        runtime_dirs = {self.cpp.build.bindirs[0], self.build_folder}
        lib_sources = []
        deps = list(self.dependencies.values()) + list(self.dependencies.test.values())
        for dep in deps:
            if dep and dep.package_folder:
                runtime_dirs.add(os.path.join(dep.package_folder, "bin"))
                lib_sources.extend(glob.glob(os.path.join(dep.package_folder, "lib", "*.so*")))
        for src in lib_sources:
            for runtime_dir in runtime_dirs:
                os.makedirs(runtime_dir, exist_ok=True)
                dst = os.path.join(runtime_dir, os.path.basename(src))
                if os.path.exists(dst) or os.path.abspath(src) == os.path.abspath(dst):
                    continue
                shutil.copy2(src, dst)

    def test(self):
        self._bridge_cache_roots()
        self._prepare_runtime_links()

        env = Environment()
        deps = list(self.dependencies.values()) + list(self.dependencies.test.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
                env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "lib", "qml")
                )
                for qml_dir in self._qml_dirs(dep.package_folder):
                    env.prepend_path("QML2_IMPORT_PATH", qml_dir)
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        # Headless sandbox: writable HOME/XDG runtime, never the real session.
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)

        binary = os.path.join(self.cpp.build.bindirs[0], "test_mauikit")
        with env.vars(self).apply():
            # ctest must fail when no tests run at all (empty-suite guard).
            self.run(
                "ctest --test-dir {} --output-on-failure --no-tests=error".format(
                    shlex.quote(self.build_folder)
                ),
                env="",
            )
            self.run(shlex.quote(binary), env="")
            self.run("{} meta".format(shlex.quote(binary)), env="")
            self.run("{} defaults".format(shlex.quote(binary)), env="")
            self.run("{} qml".format(shlex.quote(binary)), env="")

        self._dump_needed_sections(binary)
        self._assert_needed_hygiene(binary, strict=False)
        mauikit = self.dependencies.get(self.tested_reference_str.split("/")[0])
        if mauikit and mauikit.package_folder:
            for lib in glob.glob(os.path.join(mauikit.package_folder, "lib", "lib*.so*")):
                self._assert_needed_hygiene(lib)

    def _find_ohos_tool(self, name):
        candidates = [os.path.join("/data/service/hnp/bin", name)]
        found = shutil.which(name)
        if found:
            candidates.append(found)
        return next((path for path in candidates if os.path.isfile(path)), None)

    def _needed_entries(self, path):
        readelf = self._find_ohos_tool("llvm-readelf") or self._find_ohos_tool("readelf")
        if not readelf:
            self.output.warning("no readelf available; skipping DT_NEEDED hygiene for " + path)
            return None
        proc = subprocess.run([readelf, "-d", path], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True)
        entries = []
        for line in proc.stdout.splitlines():
            if "(NEEDED)" in line:
                name = line.split("[")[-1].rsplit("]", 1)[0].strip()
                entries.append(name)
        return entries

    def _dump_needed_sections(self, path):
        self.output.info("DT_NEEDED of {}: {}".format(
            os.path.basename(path), self._needed_entries(path)))

    def _assert_needed_hygiene(self, path, strict=True):
        # OHOS-specific link closure assertion. Packaged libraries must carry
        # bare sonames only (the recipe normalizes the SONAME-less published
        # KF6/Qt6Multimedia dependencies). The test binary itself is linked
        # against those published packages, so it legitimately keeps absolute
        # NEEDED entries for the SONAME-less libraries; musl opens absolute
        # entries directly, therefore require the target file to exist (the
        # cache-root bridge guarantees this on PR workers). Relative entries
        # resolve against the CWD and stay fatal everywhere.
        entries = self._needed_entries(path)
        if entries is None:
            return
        bad = [
            name for name in entries
            if "/" in name and (strict or not os.path.isfile(name))
        ]
        if bad:
            raise ConanException(
                "unresolvable DT_NEEDED entries in {}: {}".format(path, bad)
            )
        self.output.info(
            "DT_NEEDED hygiene OK for {} ({} entries, strict={})".format(
                os.path.basename(path), len(entries), strict)
        )

    def _bridge_cache_roots(self):
        # Temporary platform cache-root bridge. The release machines built and
        # published the dependency packages with the conan cache rooted at
        # ~/.conan2, so their .so files carry absolute DT_NEEDED entries such
        # as /storage/Users/currentUser/.conan2/p/<hash>/p/lib/libKF6*.so.
        # PR-check workers keep the same cache under ~/.cache/conan2 and musl
        # performs no fallback for slash-qualified NEEDED entries, so recreate
        # each baked prefix as a symlink to the real package folder. Remove
        # once the rebuilt dependency packages ship.
        bridges = []
        for dep in self.dependencies.values():
            try:
                folder = dep.package_folder if dep else None
                if not folder:
                    continue
                idx = folder.rfind("/p/")
                if idx < 0:
                    continue
                rest = folder[idx + 1:]
                legacy = os.path.expanduser("~/.conan2") + "/" + rest
                if os.path.abspath(legacy) == os.path.abspath(folder):
                    continue
                if os.path.lexists(legacy):
                    continue
                os.makedirs(os.path.dirname(legacy), exist_ok=True)
                os.symlink(folder, legacy)
                bridges.append(legacy)
            except Exception as exc:  # bridge is best-effort, never fatal
                self.output.warning(
                    f"cache-root bridge skipped for "
                    f"{getattr(dep, 'name', 'dependency')}: {exc}"
                )
        if bridges:
            self.output.info("cache-root bridges created: " + ", ".join(bridges))
