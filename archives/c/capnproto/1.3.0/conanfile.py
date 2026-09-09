#!/usr/bin/env python3
"""Conan recipe - capnproto 1.3.0 (Cap'n Proto C++ library and tools).

CMake 构建入口（与上游官方 CMakeLists.txt 对齐，参考同仓 1.1.0 已验证配方）。
OHOS 平台要点（历史配方经验）：
- BUILD_SHARED_LIBS=OFF：OHOS RPATH 问题，静态构建（同 1.1.0/1.3.0 验证配置）
- CMAKE_CXX_EXTENSIONS=ON：capnproto 需要 -std=gnu++NN（拒绝纯 -std=c++NN）
- CMAKE_POLICY_VERSION_MINIMUM=3.5：CMake 4.x 兼容
- 可选依赖 OpenSSL/zlib/fibers 全部关闭，保持配方自包含
"""

import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CapnprotoConan(ConanFile):
    name = "capnproto"
    version = "1.3.0"
    description = "Cap'n Proto serialization/RPC framework - C++ libraries and tools"
    license = "MIT"
    homepage = "https://capnproto.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x compatibility (root CMakeLists.txt uses cmake_minimum_required 3.10)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # capnproto requires GNU extensions (-std=gnu++14); Conan toolchain sets
        # CMAKE_CXX_EXTENSIONS=OFF for cppstd=17, so force it via cache + post-patch.
        tc.cache_variables["CMAKE_CXX_EXTENSIONS"] = True
        # Static build — avoid RPATH issues on OHOS (proven with 1.1.0/1.3.0)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Upstream tests run separately in this recipe; keep package build lean
        tc.variables["BUILD_TESTING"] = False
        # Disable optional dependencies to keep recipe self-contained
        tc.variables["WITH_OPENSSL"] = "OFF"
        tc.variables["WITH_ZLIB"] = "OFF"
        tc.variables["WITH_FIBERS"] = "OFF"
        # Use the capnp compiler built by this recipe, not a system one
        tc.variables["EXTERNAL_CAPNP"] = False
        tc.generate()
        self._patch_toolchain_extensions()

    def _patch_toolchain_extensions(self):
        """Force CMAKE_CXX_EXTENSIONS=ON in the generated Conan toolchain file.

        Conan's toolchain sets CMAKE_CXX_EXTENSIONS OFF when compiler.cppstd
        is a plain -std value; capnproto requires GNU extensions, so the
        toolchain must be patched after generation (same as 1.1.0 recipe).
        """
        tc_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        for f in glob.glob(tc_file):
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
            content = content.replace(
                "set(CMAKE_CXX_EXTENSIONS OFF)",
                "set(CMAKE_CXX_EXTENSIONS ON)"
            )
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(content)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # CMake package name: CapnProto (matches upstream CapnProtoConfig.cmake)
        self.cpp_info.set_property("cmake_file_name", "CapnProto")

        # Bindir contains capnp, capnpc-c++, capnpc-capnp
        self.cpp_info.bindirs = ["bin"]

        # --- Components (match upstream CapnProto::xxx targets) ---
        # KJ core
        kj = self.cpp_info.components["kj"]
        kj.libs = ["kj"]
        kj.set_property("cmake_target_name", "CapnProto::kj")

        # KJ async
        kj_async = self.cpp_info.components["kj-async"]
        kj_async.libs = ["kj-async"]
        kj_async.requires = ["kj"]
        kj_async.set_property("cmake_target_name", "CapnProto::kj-async")

        # KJ HTTP
        kj_http = self.cpp_info.components["kj-http"]
        kj_http.libs = ["kj-http"]
        kj_http.requires = ["kj-async"]
        kj_http.set_property("cmake_target_name", "CapnProto::kj-http")

        # capnp core
        capnp = self.cpp_info.components["capnp"]
        capnp.libs = ["capnp"]
        capnp.requires = ["kj"]
        capnp.set_property("cmake_target_name", "CapnProto::capnp")

        # capnp RPC
        capnp_rpc = self.cpp_info.components["capnp-rpc"]
        capnp_rpc.libs = ["capnp-rpc"]
        capnp_rpc.requires = ["capnp", "kj-async"]
        capnp_rpc.set_property("cmake_target_name", "CapnProto::capnp-rpc")

        # capnp JSON
        capnp_json = self.cpp_info.components["capnp-json"]
        capnp_json.libs = ["capnp-json"]
        capnp_json.requires = ["capnp"]
        capnp_json.set_property("cmake_target_name", "CapnProto::capnp-json")

        # capnp WebSocket
        capnp_ws = self.cpp_info.components["capnp-websocket"]
        capnp_ws.libs = ["capnp-websocket"]
        capnp_ws.requires = ["capnp-rpc", "kj-http"]
        capnp_ws.set_property("cmake_target_name", "CapnProto::capnp-websocket")

        # capnpc (schema compiler library)
        capnpc = self.cpp_info.components["capnpc"]
        capnpc.libs = ["capnpc"]
        capnpc.requires = ["capnp"]
        capnpc.set_property("cmake_target_name", "CapnProto::capnpc")