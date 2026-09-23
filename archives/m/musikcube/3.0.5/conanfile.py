#!/usr/bin/env python3
"""Conan recipe for musikcube 3.0.5 on HarmonyOS PC."""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class MusikcubeConan(ConanFile):
    name = "musikcube"
    version = "3.0.5"
    package_type = "library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/clangen/musikcube"
    url = "https://github.com/clangen/musikcube"
    description = "Terminal-based audio engine and music library core"
    topics = ("audio", "music", "indexer", "metadata")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("sqlite3/3.49.1")
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("libcurl/8.5.0")
        self.requires("taglib/2.3")
        self.requires("ncurses/6.5")
        self.requires("ffmpeg/7.1.5")
        self.requires("libev/4.33")
        self.requires("openssl/3.5.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["main"], strip_root=True)
        # 官方 musikcube 归档不含 submodule 内容，按 ConanCenter 惯例在 sources 增加
        # 官方 Asio tarball；解包到 src/3rdparty/asio/，使 websocketpp 能 include
        # asio/version.hpp（ASIO_STANDALONE 生效）。不创建独立 Conan 包。
        asio_dir = os.path.join(self.source_folder, "_asio_dl")
        os.makedirs(asio_dir, exist_ok=True)
        get(self, **self.conan_data["sources"]["asio"], destination=asio_dir,
            filename="asio-1-30-2.tar.gz", strip_root=False)
        asio_root = os.path.join(self.source_folder, "src", "3rdparty", "asio")
        os.makedirs(asio_root, exist_ok=True)
        # get() 解压后归档即被移除；动态识别解包根目录（tarball 根目录名不固定）
        extracted = os.path.join(asio_dir, "asio-asio-1-30-2")
        if not os.path.isdir(extracted):
            entries = [e for e in os.listdir(asio_dir) if os.path.isdir(os.path.join(asio_dir, e))]
            if entries:
                extracted = os.path.join(asio_dir, entries[0])
        for entry in os.listdir(extracted):
            src = os.path.join(extracted, entry)
            dst = os.path.join(asio_root, entry)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        shutil.rmtree(asio_dir)


    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("sqlite3", "cmake_file_name", "SQLite3")
        deps.set_property("sqlite3", "cmake_target_name", "SQLite::SQLite3")
        deps.generate()
        # musikcube 上游使用 find_library()/include_directories()（非 find_package），
        # 需要把 Conan 依赖的 lib/include 目录注入 CMAKE_LIBRARY_PATH / CMAKE_INCLUDE_PATH。
        lib_paths = []
        inc_paths = []
        for dep in self.dependencies.values():
            for d in dep.cpp_info.libdirs:
                if d not in lib_paths:
                    lib_paths.append(d)
            for d in dep.cpp_info.includedirs:
                if d not in inc_paths:
                    inc_paths.append(d)
        tc = CMakeToolchain(self)
        tc.variables["BUILD_STANDALONE"] = "false"
        tc.variables["BUILD_TESTING"] = "false"
        tc.variables["ENABLE_PCH"] = "false"
        tc.variables["ENABLE_PIPEWIRE"] = "false"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(lib_paths)
        tc.variables["CMAKE_INCLUDE_PATH"] = ";".join(inc_paths)
        tc.variables["CMAKE_CXX_FLAGS"] = " ".join("-I" + d for d in inc_paths)
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = " ".join("-L" + d for d in lib_paths)
        # 上游无条件 find_library 的系统库在 OHOS 上不存在独立文件：
        # - libtinfo：ncursesw 已并入（musikcube 链接 ncursesw 即可）
        # - pthread：OHOS libc 内建，无独立 libpthread.so
        # 预置为空串避免 CMake NOTFOUND 硬失败（链接期符号由 libc/ncurses 提供）
        tc.variables["LIBTINFO"] = ""
        tc.variables["PTHREAD"] = ""
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        # 上游 InstallFiles.cmake 将 libmusikcore.so 安装到 share/musikcube/，
        # 重排为标准 Conan lib/ 布局，使 cpp_info.libs=["musikcore"] 可被消费方定位
        src = os.path.join(self.package_folder, "share", "musikcube", "libmusikcore.so")
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isfile(src):
            os.makedirs(libdir, exist_ok=True)
            shutil.move(src, os.path.join(libdir, "libmusikcore.so"))
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["musikcore"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "musikcube")
        self.cpp_info.set_property("cmake_target_name", "musikcube::musikcore")
        self.cpp_info.set_property("pkg_config_name", "musikcore")
        self.buildenv_info.define_path("MUSIKCUBE_PLUGIN_PATH", os.path.join(self.package_folder, "share", "musikcube", "plugins"))
