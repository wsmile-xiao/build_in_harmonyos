#!/usr/bin/env python3
"""Conan recipe - capnproto 1.1.0 (Cap'n Proto C++ library and tools)."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
import os


class CapnprotoConan(ConanFile):
    name = "capnproto"
    version = "1.1.0"
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

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x compatibility (root CMakeLists.txt uses cmake_minimum_required 3.4)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # capnproto requires GNU extensions (-std=gnu++14, not -std=c++14)
        # NOTE: tc.cache_variables is overridden by toolchain's set(), so we
        # patch the toolchain file after generation.
        tc.cache_variables["CMAKE_CXX_EXTENSIONS"] = True
        # Static build — avoid RPATH issues on OHOS (matches 1.3.0 proven config)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Disable upstream tests — run separately; /tmp issue on OHOS
        tc.variables["BUILD_TESTING"] = False
        # Disable optional dependencies to keep recipe self-contained
        tc.variables["WITH_OPENSSL"] = "OFF"
        tc.variables["WITH_ZLIB"] = "OFF"
        tc.variables["WITH_FIBERS"] = "OFF"
        # Don't try to use external capnp during build
        tc.variables["EXTERNAL_CAPNP"] = False
        tc.generate()
        # Patch toolchain: force CMAKE_CXX_EXTENSIONS=ON (Conan toolchain
        # sets it to OFF for compiler.cppstd=17, overriding cache variables)
        self._patch_toolchain_extensions()

    def _patch_toolchain_extensions(self):
        """Force CMAKE_CXX_EXTENSIONS=ON in generated toolchain file."""
        import glob
        pattern = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        for f in glob.glob(pattern):
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
            content = content.replace(
                "set(CMAKE_CXX_EXTENSIONS OFF)",
                "set(CMAKE_CXX_EXTENSIONS ON)"
            )
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(content)

    def _patch_conanbuild_ld_library_path(self):
        """Append LD_LIBRARY_PATH to conanbuild.sh so lld can find libxml2.so.16."""
        import glob
        pattern = os.path.join(self.generators_folder, "conanbuild*.sh")
        for script in glob.glob(pattern):
            with open(script, "a", encoding="utf-8") as f:
                f.write('\n# capnproto OHOS fix: lld needs libxml2.so.16\n')
                f.write('export LD_LIBRARY_PATH="/storage/Users/currentUser/usr/local/lib:${LD_LIBRARY_PATH:-}"\n')

    def build(self):
        if self.settings.os in ("Linux", "OHOS"):
            self._patch_conanbuild_ld_library_path()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
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
