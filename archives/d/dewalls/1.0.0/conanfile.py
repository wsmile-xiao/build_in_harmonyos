#!/usr/bin/env python3
"""Conan recipe for dewalls 1.0.0 — C++/Qt5 parser for Walls cave survey data.

Upstream build system is QBS (dewalls.qbs, Qt Build Suite). CI has no QBS
toolchain, so the recipe ships a CMakeLists.txt (patches/) that builds the
same targets declared upstream:
  - libdewalls    (shared library, src/*)
  - dewalls-test  (Catch-based test runner, test/*)

Dependency: qt/5.15.19 (Qt5 Core only, per upstream dewalls.qbs).
"""
import glob
import os
import shlex

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DewallsConan(ConanFile):
    name = "dewalls"
    version = "1.0.0"
    description = "C++/Qt5 parser library for Walls .wpj/.srv cave survey data"
    license = "MIT"
    homepage = "https://github.com/jedwards1211/dewalls"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qt/5.15.19 ships its own Qt5Config.cmake (cmake_find_mode=none) and
        # declares no CMake package name; CMakeDeps therefore cannot generate a
        # qt-config/proxy target for downstream find_dependency(qt). Keep qt as
        # a private build-time requirement (visible=False): libdewalls links
        # against Qt5Core, but consumers resolve Qt5 by themselves exactly as
        # posixsignalmanager does (self.requires("qt/5.15.19") in their own
        # recipe + CMAKE_PREFIX_PATH -> find_package(Qt5)).
        self.requires("qt/5.15.19", visible=False)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sdk_llvm_lib_dirs(self):
        """Resolve the OHOS SDK native llvm/lib directory without hardcoding a
        machine-local absolute path in the recipe.

        The OHOS SDK ships libc++_shared.so (needed by qt5's bin/moc at
        AUTOMOC time) under <llvm>/lib/aarch64-linux-ohos/. The SDK location
        is derived from the profile-declared toolchain (conf
        tools.build:compiler_executables): the SDK tree lives in the same
        prefix as the compiler at <prefix>/ohos-sdk.org/*/ohos/native/llvm/lib.
        An explicit override (OHOS_NATIVE_LLVM_LIB) wins when set. We only
        inject what actually exists, so machines without the SDK are unaffected.
        """
        dirs = []

        def _collect(base):
            if not base or not os.path.isdir(base):
                return
            for sub in (base, os.path.join(base, "aarch64-linux-ohos")):
                if os.path.isdir(sub) and sub not in dirs:
                    dirs.append(sub)

        env = os.environ.get("OHOS_NATIVE_LLVM_LIB", "").strip()
        if env:
            _collect(env)
        if dirs:
            return dirs

        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
            cxx = compilers.get("cpp") or compilers.get("c")
        except Exception:
            cxx = None
        if cxx and isinstance(cxx, str) and os.path.isabs(cxx):
            prefix = os.path.dirname(os.path.dirname(os.path.normpath(cxx)))
            for hit in glob.glob(os.path.join(
                    prefix, "ohos-sdk.org", "*", "ohos", "native", "llvm", "lib")):
                _collect(hit)
        return dirs

    def generate(self):
        tc = CMakeToolchain(self)
        # Qt5 ships its own Qt5Config.cmake (cmake_find_mode=none); point CMake
        # at the qt package directory so find_package(Qt5) resolves.
        qt_prefix = self.dependencies["qt"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qt_prefix
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"

        # OHOS platform name mapping (CMake has no HarmonyOS module).
        if self.settings.os in ("Linux", "OHOS"):
            # SONAME emission: OHOS platform CMake does not inject the
            # -Wl,-soname flag automatically; without it libdewalls.so has no
            # DT_SONAME and the downstream linker cannot address it by name
            # (W3 L5a gate / E383). Same fix as libaccounts-qt.
            tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        # Provide explicit moc/rcc paths for AUTOMOC/AUTORCC (libaccounts-qt
        # precedent): qt5 host tools are loadable on the OHOS host.
        for tool, var in (("moc", "CMAKE_AUTOMOC_EXECUTABLE"),
                          ("rcc", "CMAKE_AUTORCC_EXECUTABLE")):
            tool_path = os.path.join(qt_prefix, "bin", tool)
            if os.path.isfile(tool_path):
                tc.variables[var] = tool_path

        tc.generate()

        # qt5's bin/moc needs the OHOS SDK libc++_shared.so at AUTOMOC time;
        # inject the SDK llvm lib dirs (from environment/profile, not a
        # hardcoded path) into the build environment via buildenv_info.
        for sub in self._sdk_llvm_lib_dirs():
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", sub)

    def build(self):
        apply_conandata_patches(self)
        # libc++_shared.so for AUTOMOC's moc must be visible when CMake spawns
        # the moc subprocess. Derive the SDK lib dirs from the profile-declared
        # toolchain (conf) instead of hardcoding a machine-local path, and apply
        # them through conan's Environment so the child processes inherit them.
        env = Environment()
        for sub in self._sdk_llvm_lib_dirs():
            env.prepend_path("LD_LIBRARY_PATH", sub)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
        # Run upstream tests (dewalls-test, Catch v1.2.1 single-header).
        if self.settings.os in ("Linux", "OHOS"):
            qt_lib = os.path.join(self.dependencies["qt"].package_folder, "lib")
            build_bin = self.cpp.build.bindirs[0] if self.cpp.build.bindirs else self.build_folder
            # dewalls-test links libdewalls (build dir), Qt5Core (qt lib) and
            # libc++_shared.so (SDK llvm lib dirs, derived from profile conf).
            lib_dirs = [p for p in (build_bin, qt_lib)
                        if p and os.path.isdir(p)]
            lib_dirs.extend(self._sdk_llvm_lib_dirs())
            lib_paths = os.pathsep.join(lib_dirs)
            self.run(
                f"LD_LIBRARY_PATH={shlex.quote(lib_paths)}:$LD_LIBRARY_PATH "
                f"ctest --output-on-failure",
                env="conanbuild", ignore_errors=False)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["dewalls"]
        self.cpp_info.set_property("cmake_file_name", "dewalls")
        self.cpp_info.set_property("cmake_target_name", "dewalls::dewalls")
        # Consumers must resolve Qt5 themselves (qt/5.15.19 ships its own
        # Qt5Config.cmake with cmake_find_mode=none; CMakeDeps generates no
        # qt::core target). Consumers point CMAKE_PREFIX_PATH at the qt
        # package folder and run find_package(Qt5) in their own CMake.
        # Runtime: make libdewalls discoverable on LD_LIBRARY_PATH. The qt
        # library path is provided by qt/5.15.19's own runenv_info once the
        # consumer declares the qt requirement.
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        # libdewalls.so has DT_NEEDED libc++_shared.so; on OHOS the correct
        # runtime lives under the SDK llvm lib dirs (derived from the
        # profile-declared toolchain, not a hardcoded path). Expose them so
        # consumers and test_package can load the library.
        for sub in self._sdk_llvm_lib_dirs():
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", sub)