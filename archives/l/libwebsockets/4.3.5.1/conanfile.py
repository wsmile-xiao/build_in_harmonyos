#!/usr/bin/env python3
"""Conan recipe for libwebsockets 4.3.5.1 (OpenHarmony PC).

4.3.5.1 是 R37 适配修复后缀版本：上游源码仍为 v4.3.5，
在 4.3.5 基础上启用 libuv 事件循环集成（LWS_WITH_LIBUV=ON），
满足下游 ttyd 1.7.7 对 libwebsockets 必须 built with libuv 的要求。
"""

import glob
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class LibwebsocketsConan(ConanFile):
    name = "libwebsockets"
    version = "4.3.5.1"
    description = (
        "A lightweight, pure C library for websockets and web server "
        "implementation, used by ttyd and other realtime web consumers "
        "(R37 fix: enable libuv event loop support)"
    )
    license = "MIT"
    homepage = "https://libwebsockets.org"
    url = "https://github.com/warmcat/libwebsockets"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libwebsockets is validated only for Linux and OHOS, "
                f"not {self.settings.os}"
            )

    def requirements(self):
        self.requires("openssl/3.5.6")
        # R37 修复：ttyd 1.7.7 无条件要求 libwebsockets 启用 libuv 支持，
        # 因此新增真实 libuv 依赖（对应 LWS_WITH_LIBUV=ON）。
        self.requires("libuv/1.52.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        openssl_pkg = self.dependencies["openssl"]
        openssl_root = openssl_pkg.package_folder.replace("\\", "/")
        libuv_pkg = self.dependencies["libuv"]
        libuv_root = libuv_pkg.package_folder.replace("\\", "/")
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # libwebsockets 4.3.5 用传统 OPENSSL_INCLUDE_DIRS/OPENSSL_LIBRARIES
        # 变量探测 OpenSSL，而 CMakeDeps 只提供 openssl::openssl target，
        # 因此显式把依赖包的头文件/库路径传给 LWS_OPENSSL_* cache 变量。
        tc.variables["LWS_OPENSSL_INCLUDE_DIRS"] = os.path.join(
            openssl_root, "include"
        ).replace("\\", "/")
        tc.variables["LWS_OPENSSL_LIBRARIES"] = ";".join(
            os.path.join(openssl_root, "lib", lib)
            for lib in ("libssl.a", "libcrypto.a")
        )
        # 外部 libuv：上游 lib/event-libs/libuv/CMakeLists.txt 接受
        # LWS_LIBUV_INCLUDE_DIRS / LWS_LIBUV_LIBRARIES cache 变量，
        # 为空时才回退 find_path/find_library（可能误中宿主系统库）。
        # 这里显式指向 Conan libuv 包，避免静默使用未归档的系统库。
        tc.variables["LWS_LIBUV_INCLUDE_DIRS"] = os.path.join(
            libuv_root, "include"
        ).replace("\\", "/")
        libuv_lib = self._pick_libuv_library(libuv_root)
        if not libuv_lib:
            raise ConanInvalidConfiguration(
                "libuv package does not provide libuv.a / libuv.so under lib/"
            )
        tc.variables["LWS_LIBUV_LIBRARIES"] = libuv_lib
        tc.variables["LWS_WITH_LIBUV"] = "ON"
        # 把 libuv 事件循环支持直接编入 libwebsockets（而不是默认 UNIX 下的
        # 运行时插件 websockets-evlib_uv.so），消费者链接 libwebsockets 即得
        # 到 libuv 集成，避免运行时插件加载路径问题。
        tc.variables["LWS_WITH_EVLIB_PLUGINS"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["LWS_WITH_SSL"] = "ON"
        tc.variables["LWS_WITH_HTTP2"] = "ON"
        tc.variables["LWS_WITHOUT_TESTAPPS"] = "ON"
        tc.variables["LWS_WITH_MINIMAL_EXAMPLES"] = "OFF"
        tc.variables["LWS_WITHOUT_EXTENSIONS"] = "ON"
        tc.variables["LWS_WITH_NETLINK"] = "ON"
        tc.variables["LWS_WITH_IPV6"] = "ON"
        tc.variables["LWS_WITH_CLIENT"] = "ON"
        tc.variables["LWS_WITH_SERVER"] = "ON"
        if not self.options.shared and self.settings.os != "Windows":
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        tc.generate()

    def _pick_libuv_library(self, libuv_root):
        """libuv 包同时可能提供 libuv.a 与 libuv.so，优先取共享库，其次静态库。"""
        libdir = os.path.join(libuv_root, "lib")
        for pattern in ("libuv.so*", "libuv.dylib", "libuv.a", "libuv.lib"):
            hits = sorted(
                glob.glob(os.path.join(libdir, pattern)),
                key=lambda p: len(os.path.basename(p)),
            )
            if hits:
                return hits[0].replace("\\", "/")
        return ""

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libwebsockets")
        # libwebsockets.h 会 #include <openssl/ssl.h>，libuv 集成 API
        # （lws_uv_getloop 等）需要 <uv.h>，因此消费者编译时必须拿到
        # OpenSSL 与 libuv 的头文件和库，传递这两个依赖。
        self.cpp_info.requires = ["openssl::openssl", "libuv::libuv"]
        self.cpp_info.libs = ["websockets"] if self.options.shared else ["websockets_static"]
        if not self.options.shared:
            self.cpp_info.system_libs = ["ssl", "crypto"]  # libwebsockets_static needs OpenSSL
