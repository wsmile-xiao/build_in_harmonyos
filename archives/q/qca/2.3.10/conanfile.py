#!/usr/bin/env python3
"""Conan recipe for QCA 2.3.10 on OpenHarmony PC."""
import glob
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy


class QcaConan(ConanFile):
    name = "qca"
    version = "2.3.10"
    description = "Qt Cryptographic Architecture library"
    license = "LGPL-2.1-or-later"
    homepage = "https://userbase.kde.org/QCA"
    url = "https://invent.kde.org/libraries/qca"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Qt6Core5Compat 自包含依赖（同 qbs 方案——Qt 官方 archive 下载，
        # build() 编译提供 Qt6Core5Compat）
        get(self, **self.conan_data["qtcore5compat"])
        cmake_path = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        with open(cmake_path, "r", encoding="utf-8") as fh:
            text = fh.read()
        text = re.sub(r'if\(UNIX(?: OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")?\)', "if(NOT WIN32)", text)
        text = re.sub(r'IF \(UNIX(?: OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")?\)', "IF (NOT WIN32)", text)
        with open(cmake_path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def requirements(self):
        # qtcore5compat remote 无制品——改为自包含（source 下载 Qt5Compat
        # 源码 + build 编译到 core5compat-install，generate 指向）
        self.requires("qtbase/6.11.1")

    def generate(self):
        tc = CMakeToolchain(self)
        qt_prefix = self.dependencies["qtbase"].package_folder
        core5_prefix = os.path.join(self.build_folder, "build", "Release", "core5compat-install")
        tc.variables["BUILD_WITH_QT6"] = True
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTS"] = True
        tc.variables["BUILD_TOOLS"] = False
        tc.variables["BUILD_PLUGINS"] = "none"
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join([qt_prefix, core5_prefix])
        tc.cache_variables["Qt6_DIR"] = os.path.join(qt_prefix, "lib", "cmake", "Qt6")
        tc.cache_variables["Qt6Core5Compat_DIR"] = os.path.join(
            core5_prefix, "lib", "cmake", "Qt6Core5Compat")
        tc.cache_variables["CMAKE_MODULE_PATH"] = os.path.join(
            qt_prefix, "lib", "cmake", "Qt6", "platforms")
        tc.generate()

    def build(self):
        # Qt6Core5Compat 自包含编译（同 qbs 方案——qca 的 Qt6Core5Compat_DIR
        # 配置需要——remote 无 qtcore5compat 制品；Qt 模块 CMake 构建依赖
        # qtbase Qt6Core，安装到 build 目录 core5compat-install）
        core5_src = os.path.join(self.source_folder, "qt5compat-everywhere-src-6.11.1")
        core5_inst = os.path.join(self.build_folder, "build", "Release", "core5compat-install")
        qtbase_root = self.dependencies["qtbase"].package_folder
        if os.path.isdir(core5_src):
            os.makedirs(core5_inst, exist_ok=True)
            self.run(f"cd {core5_src} && cmake -B build -S . "
                     f"-DCMAKE_PREFIX_PATH={qtbase_root} "
                     f"-DCMAKE_INSTALL_PREFIX={core5_inst} "
                     f"-DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release "
                     f"-DCMAKE_CXX_FLAGS='-stdlib=libc++'",
                     ignore_errors=True)
            self.run(f"cd {core5_src} && cmake --build build --parallel 1",
                     ignore_errors=True)
            self.run(f"cd {core5_src} && cmake --install build --prefix={core5_inst}",
                     ignore_errors=True)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            qt_prefix = self.dependencies["qtbase"].package_folder
            release_lib = os.path.join(self.build_folder, "lib")
            legacy_lib = os.path.join(os.path.dirname(self.build_folder), "lib")
            lib_paths = [
                os.path.join(qt_prefix, "lib"),
                os.path.join(self.build_folder, "core5compat-install", "lib"),
                release_lib,
                legacy_lib,
            ]
            os.makedirs(legacy_lib, exist_ok=True)
            os.makedirs(release_lib, exist_ok=True)
            src_lib = os.path.join(release_lib, "libqca-qt6.so")
            if os.path.isfile(src_lib):
                self.run("cp -f {} {}".format(shlex.quote(src_lib), shlex.quote(os.path.join(legacy_lib, "libqca-qt6.so"))))
            self.run(f"LD_LIBRARY_PATH={shlex.quote(os.pathsep.join(lib_paths))} ctest --test-dir {shlex.quote(self.build_folder)} --output-on-failure", env=["conanbuild"])
        else:
            self.output.warning("QCA upstream tests were built but not run because target binaries cannot execute on this host")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.options.shared:
            self._sign_shared_libs()
        # Qt6Core5Compat 自包含产物打进包（qca 库链接 Qt6Core5Compat——消费方
        # test_package 的 find_package(Qt6 Core5Compat) 通过本包 CMAKE_PREFIX_PATH
        # 找到 Qt6Core5Compat 配置 + 库——同 qbs 自包含方案）
        core5_cands = glob.glob(os.path.join(self.build_folder, "**", "core5compat-install"),
                               recursive=True)
        core5_inst = core5_cands[0] if core5_cands else None
        if core5_inst and os.path.isdir(core5_inst):
            # conan copy 的 pattern 匹配目录（Qt6Core5Compat）但不复制目录内文件
            # （Qt6Core5CompatConfig.cmake 不在匹配集）——用 shutil.copytree
            # 复制整个 core5compat-install（配置 + 库 + 头完整进包）
            import shutil as _sh
            _sh.copytree(os.path.join(core5_inst, "lib", "cmake", "Qt6Core5Compat"),
                         os.path.join(self.package_folder, "lib", "cmake", "Qt6Core5Compat"),
                         dirs_exist_ok=True)
            if os.path.isdir(os.path.join(core5_inst, "lib", "cmake", "Qt6Core5CompatPrivate")):
                _sh.copytree(os.path.join(core5_inst, "lib", "cmake", "Qt6Core5CompatPrivate"),
                             os.path.join(self.package_folder, "lib", "cmake", "Qt6Core5CompatPrivate"),
                             dirs_exist_ok=True)
            for _f in glob.glob(os.path.join(core5_inst, "lib", "libQt6Core5Compat*")):
                _sh.copy2(_f, os.path.join(self.package_folder, "lib"))
            if os.path.isdir(os.path.join(core5_inst, "include", "QtCore5Compat")):
                _sh.copytree(os.path.join(core5_inst, "include", "QtCore5Compat"),
                             os.path.join(self.package_folder, "include", "QtCore5Compat"),
                             dirs_exist_ok=True)

    def _sign_shared_libs(self):
        if str(self.settings.os) != "OHOS":
            return
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        shared_objects += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not shared_objects:
            return
        objcopy = os.environ.get("HNP_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("HNP_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException("Required OHOS signing tool not found: {}".format(tool))
        quoted_objcopy = shlex.quote(objcopy)
        quoted_signer = shlex.quote(signer)
        for shared_object in shared_objects:
            if os.path.islink(shared_object):
                continue
            quoted_object = shlex.quote(shared_object)
            probe = self.run(
                f"{quoted_objcopy} --dump-section .codesign=/dev/null {quoted_object}",
                ignore_errors=True,
            )
            if probe == 0:
                self.run(f"{quoted_objcopy} --remove-section .codesign {quoted_object}")
            self.run(f"{quoted_signer} sign -inFile {quoted_object} -outFile {quoted_object} -selfSign 1")

    def package_info(self):
        self.cpp_info.libs = ["qca-qt6"]
        self.cpp_info.includedirs = ["include/Qca-qt6", "include"]
        self.cpp_info.set_property("cmake_file_name", "Qca-qt6")
        self.cpp_info.set_property("cmake_target_name", "qca-qt6")
        self.cpp_info.set_property("pkg_config_name", "qca2-qt6")
