#!/usr/bin/env python3
"""Conan recipe for sasm 3.15.0 — SASM, a simple crossplatform IDE for
NASM/MASM/GAS/FASM assembly development (Qt5 Widgets GUI application).

Upstream build system is qmake (SASM.pro). CI builds via the CMakeLists.txt
shipped in patches/0001-CMakeLists.txt.patch (qmake to CMake rewrite), which
builds the same `sasm` executable target with AUTOMOC/AUTOUIC/AUTORCC.

Dependency: qt/5.15.19 (Qt5 Core/Gui/Widgets/Network — the app links
QtSingleApplication sources in-tree, which need Qt5Network).

Note: SASM is an IDE that shells out to external assemblers (nasm/gas/
masm/fasm) and gdb at runtime; this package ships the IDE binary itself.
The test_package verifies the binary launches headless (offscreen platform).
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class SasmConan(ConanFile):
    name = "sasm"
    version = "3.15.0"
    description = "SASM — simple crossplatform IDE for assembler development (Qt5)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/Dman95/SASM"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt/5.15.19")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # filename= 显式指定：codeload URL 不以 .tar.gz 结尾，conan 无法从
        # URL 推断压缩格式（会误判为 zip 解包失败）。
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="SASM-3.15.0.tar.gz")

    def _sdk_llvm_lib_dirs(self):
        """Resolve the OHOS SDK native llvm/lib directory without hardcoding a
        machine-local absolute path in the recipe (dewalls/libaccounts-qt
        precedent): qt5's bin/moc needs the SDK libc++_shared.so at AUTOMOC
        time. Derived from the profile-declared toolchain (conf
        tools.build:compiler_executables); explicit OHOS_NATIVE_LLVM_LIB
        override wins when set."""
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
        # qt/5.15.19 ships its own Qt5Config.cmake (cmake_find_mode=none):
        # point CMake at the qt package directory so find_package(Qt5) resolves.
        qt_prefix = self.dependencies["qt"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qt_prefix
        # Explicit moc/rcc/uic paths for AUTOMOC/AUTORCC/AUTOUIC (qt5 host
        # tools are loadable on the OHOS host).
        for tool, var in (("moc", "CMAKE_AUTOMOC_EXECUTABLE"),
                          ("rcc", "CMAKE_AUTORCC_EXECUTABLE"),
                          ("uic", "CMAKE_AUTOUIC_EXECUTABLE")):
            tool_path = os.path.join(qt_prefix, "bin", tool)
            if os.path.isfile(tool_path):
                tc.variables[var] = tool_path
        tc.generate()

        # qt5's bin/moc needs the OHOS SDK libc++_shared.so at AUTOMOC time.
        for sub in self._sdk_llvm_lib_dirs():
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", sub)

    def build(self):
        apply_conandata_patches(self)
        env = Environment()
        for sub in self._sdk_llvm_lib_dirs():
            env.prepend_path("LD_LIBRARY_PATH", sub)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def package(self):
        from conan.tools.files import copy
        copy(self, "sasm", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # GUI 应用运行时也依赖 qt 包提供的共享库路径。
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "bin"))
