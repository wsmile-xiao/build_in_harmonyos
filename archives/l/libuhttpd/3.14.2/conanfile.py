#!/usr/bin/env python3
"""Conan recipe for libuhttpd 3.14.2 - embedded HTTP server library.

libuhttpd is a CMake-based embedded HTTP server library (MIT) built around
libev. The upstream release tarball (v3.14.2) excludes git submodule content,
so src/{buffer,http-parser,log,ssl} ship empty in the GitHub source archive;
this recipe fetches each submodule at the exact commit pinned by the v3.14.2
tag (see conandata.yml `submodules`) and lays them out where the top-level
CMakeLists.txt expects them.

Adaptation notes:
- Build system is CMake (NOT autotools): the recipe uses CMakeToolchain with
  the OHOS aarch64 profile; upstream CMakeLists.txt declares
  `cmake_minimum_required(VERSION 3.0)`, which CMake 4.x rejects, so
  CMAKE_POLICY_VERSION_MINIMUM=3.5 is injected via the toolchain (same
  approach as adlplug/1.0.2).
- find_package(Libev REQUIRED) uses the shipped FindLibev.cmake
  (find_path/find_library); the dependency include/lib dirs are exposed via
  CMAKE_INCLUDE_PATH / CMAKE_LIBRARY_PATH in generate() so the module finder
  hits the Conan-provided libev.
- SSL support (src/ssl submodule) defaults ON and selects OpenSSL when found;
  OpenSSL is declared as a requirement and its include/lib dirs are added to
  the same module-search paths (FindOpenSSL.cmake uses find_path/find_library).
- BUILD_EXAMPLE defaults ON upstream; examples are demo servers and are not
  installed by the library target, so they are disabled for the package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file


class LibuhttpdConan(ConanFile):
    name = "libuhttpd"
    version = "3.14.2"
    description = "A very lightweight, memory-efficient, HTTP server library based on libev"
    license = "MIT"
    homepage = "https://github.com/zhaojh329/libuhttpd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "ssl": [True, False]}
    default_options = {"shared": True, "ssl": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libev/4.33")
        if self.options.ssl:
            self.requires("openssl/3.5.6")

    def configure(self):
        # gdnsd 先例（同 libev/4.33）：制品仓唯一 published 二进制为 shared 且
        # 无 DT_SONAME。以绝对路径链接会让 libuhttpd.so 的 DT_NEEDED 记录缓存
        # 绝对路径（L5b 违规）且跨机器不可复现；强制静态使 libev 内嵌进
        # libuhttpd.so，产物自包含、DT_NEEDED 干净。
        self.options["libev"].shared = False

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload archive URLs end with the ref (no .tar.gz suffix), so pass
        # an explicit filename to let Conan detect the tar.gz format.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="libuhttpd-3.14.2.tar.gz")
        # GitHub source archives omit submodule content; fetch each submodule
        # at the commit pinned by the v3.14.2 tag into its expected location.
        # codeload URLs end with the commit SHA (no extension), so pass an
        # explicit filename to let Conan detect the tar.gz format.
        for name, info in self.conan_data.get("submodules", {}).items():
            get(self, url=info["url"], sha256=info["sha256"], strip_root=True,
                filename=f"{name}.tar.gz",
                destination=os.path.join(self.source_folder, info["destination"]))
        # CMake 4.x removed compatibility with CMake < 3.5. Upstream declares
        # VERSION 3.0; the toolchain-level CMAKE_POLICY_VERSION_MINIMUM is set
        # too late (CMake resolves cmake_minimum_required before loading the
        # toolchain), so bump the declared minimum like adlplug/1.0.2.
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
            "cmake_minimum_required(VERSION 3.0)",
            "cmake_minimum_required(VERSION 3.5)")
        # L5 SONAME 门禁: 上游只设 VERSION 未设 SOVERSION, 产物缺失 DT_SONAME。
        # 补 SOVERSION 让共享库带 DT_SONAME (libuhttpd.so.3), 下游可按 SONAME 寻址。
        replace_in_file(self, os.path.join(self.source_folder, "src", "CMakeLists.txt"),
            "    set_target_properties(uhttpd PROPERTIES VERSION ${UHTTPD_VERSION_MAJOR}.${UHTTPD_VERSION_MINOR}.${UHTTPD_VERSION_PATCH})",
            "    set_target_properties(uhttpd PROPERTIES VERSION ${UHTTPD_VERSION_MAJOR}.${UHTTPD_VERSION_MINOR}.${UHTTPD_VERSION_PATCH} SOVERSION ${UHTTPD_VERSION_MAJOR})")

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x removed compatibility with CMake < 3.5 (upstream declares 3.0)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # HarmonyOS 真机 CMake 无 platform module（"System is unknown to cmake"），
        # 共享库的 VERSION/SOVERSION 属性因此不生成 DT_SONAME（L5a 违规）。
        # 显式设 CMAKE_SYSTEM_NAME=Linux 让 CMake 走 Linux 平台规则（libindi 先例），
        # 同时源码已补 SOVERSION，产物即可带 DT_SONAME。
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["BUILD_EXAMPLE"] = "OFF"
        if self.options.ssl:
            tc.variables["USE_OPENSSL"] = "ON"
            # Upstream src/ssl/CMakeLists.txt selects OpenSSL via
            # pkg_check_modules() (sets plural OPENSSL_INCLUDE_DIRS) but then
            # reads the SINGULAR OPENSSL_INCLUDE_DIR variable into SSL_INC —
            # which pkg-config never sets, leaving the include path empty.
            # Inject it explicitly from the Conan dependency so openssl/ssl.h
            # resolves (the singular variable is also honored by
            # FindOpenSSL.cmake when the pkg-config path is unavailable).
            ossl = self.dependencies["openssl"].cpp_info
            tc.variables["OPENSSL_INCLUDE_DIR"] = ";".join(ossl.includedirs)
            tc.variables["OPENSSL_LIBRARIES"] = ";".join(ossl.libdirs)
        # Upstream FindLibev.cmake / FindOpenSSL.cmake use module finders
        # (find_path/find_library), so expose dependency dirs explicitly.
        include_dirs, lib_dirs = [], []
        for dep_name in ("libev", "openssl"):
            if dep_name in self.dependencies:
                info = self.dependencies[dep_name].cpp_info
                include_dirs += list(info.includedirs)
                lib_dirs += list(info.libdirs)
        if include_dirs:
            tc.variables["CMAKE_INCLUDE_PATH"] = ";".join(include_dirs)
        if lib_dirs:
            tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(lib_dirs)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libuhttpd")
        self.cpp_info.set_property("cmake_target_name", "libuhttpd::libuhttpd")
        self.cpp_info.libs = ["uhttpd"]
