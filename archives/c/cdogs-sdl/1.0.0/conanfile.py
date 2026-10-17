#!/usr/bin/env python3
"""Conan recipe — cdogs-sdl 1.0.0 (CMake, SDL2 game).

Dependencies: SDL2, SDL2_image, SDL2_mixer, Nanopb.
Generates executables: cdogs-sdl, cdogs-sdl-editor.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CdogssdlConan(ConanFile):
    name = "cdogs-sdl"
    version = "1.0.0"
    description = "C-Dogs SDL — classic overhead run-and-shoot game"
    license = "MIT"
    homepage = "https://github.com/cxong/cdogs-sdl"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "build_editor": [True, False]}
    default_options = {"shared": False, "build_editor": False}
    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")
        self.requires("sdl2_image/2.6.0")
        self.requires("sdl2_mixer/2.8.1")
        self.requires("nanopb/0.4.9.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 cmake_minimum_required(3.1) 与新 CMake（≥3.5 移除旧版兼容）冲突，
        # 通过缓存变量在配方侧修复，不改动上游源码。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # R10 显式 CMake bridge（E300 cmake-cache-path-bridge 模式）：
        # vendored FindSDL2*.cmake 用 find_path/find_library 解析 SDL2_* 变量，
        # 在 OHOS 交叉编译 + CMakeDeps 环境下查找失败（r08/r09 六次调参已证）。
        # 直接从 Conan cpp_info 预置这些缓存变量：
        #   1) include 目录 → 消除 find_path 失败（SDL_audio.h not found）
        #   2) 库变量 → 指向 CMakeDeps imported target，
        #      使 sdl2_image::sdl2_image 的 INTERFACE_LINK_LIBRARIES
        #      （libwebp/libtiff/zlib 等）传递到实际消费目标（WebP/TIFF undefined）
        sdl2 = self.dependencies["sdl2"]
        sdl2_image = self.dependencies["sdl2_image"]
        sdl2_mixer = self.dependencies["sdl2_mixer"]
        for dep, var_list in [
            (sdl2, ["SDL2"]),
            (sdl2_image, ["SDL2_IMAGE"]),
            (sdl2_mixer, ["SDL2_MIXER"]),
        ]:
            inc_dirs = []
            for rel in dep.cpp_info.includedirs:
                full = rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)
                if full not in inc_dirs:
                    inc_dirs.append(full)
                child = os.path.join(full, "SDL2")
                if os.path.isdir(child) and child not in inc_dirs:
                    inc_dirs.append(child)
            prefix = var_list[0]
            tc.cache_variables[f"{prefix}_INCLUDE_DIR"] = ";".join(inc_dirs)
            tc.cache_variables[f"{prefix}_INCLUDE_DIRS"] = ";".join(inc_dirs)
            target = dep.ref.name + "::" + dep.ref.name
            tc.cache_variables[f"{prefix}_LIBRARY"] = target
            tc.cache_variables[f"{prefix}_LIBRARY_TEMP"] = target
            tc.cache_variables[f"{prefix}_LIBRARIES"] = target
        tc.variables["BUILD_EDITOR"] = "ON" if self.options.build_editor else "OFF"
        tc.generate()

    def _patch_source(self, root):
        """Patch CMakeLists.txt files for OHOS cross-compilation compatibility.
        Runs on the source_folder before cmake.configure().
        """
        # 1. Inject -Wno-implicit-const-int-float-conversion (clang 15 + -Werror)
        top = os.path.join(root, "CMakeLists.txt")
        if os.path.isfile(top):
            with open(top) as f:
                content = f.read()
            if "-Wno-implicit-const-int-float-conversion" not in content:
                content = content.replace(
                    'add_definitions(-std=gnu99)',
                    'add_definitions(-std=gnu99)\n        add_definitions(-Wno-implicit-const-int-float-conversion)')
            # 2. Use Conan CMakeDeps targets (lowercase) for transitive dep resolution
            #    Vendored FindSDL2_*.cmake modules don't pass libtiff/libwebp/libsndfile.
            find_pkg_block = """
# Conan CMakeDeps targets (lowercase, case-sensitive OHOS)
find_package(sdl2 CONFIG QUIET)
find_package(sdl2_image CONFIG QUIET)
find_package(sdl2_mixer CONFIG QUIET)
find_package(nanopb CONFIG QUIET)
"""
            if "find_package(sdl2 CONFIG" not in content:
                content = content.replace(
                    "find_package(CCache)",
                    find_pkg_block + "find_package(CCache)")
            with open(top, "w") as f:
                f.write(content)

        # 3. APPEND Conan CMakeDeps targets to link lines in src/cdogs/CMakeLists.txt.
        #    保留上游 MODULE 变量（SDL2_INCLUDE_DIRS 等，41% 处已证有效），
        #    追加 target 使 sdl2_image::sdl2_image 的 INTERFACE_LINK_LIBRARIES
        #    （libwebp/libtiff/zlib 等传递依赖）到达消费目标。
        cdogs_cmake = os.path.join(root, "src", "cdogs", "CMakeLists.txt")
        if os.path.isfile(cdogs_cmake):
            with open(cdogs_cmake) as f:
                content = f.read()
            if "sdl2::sdl2" not in content:
                content = content.replace(
                    "\t${SDL2_MIXER_LIBRARIES}\n\t${ENet_LIBRARIES})",
                    "\t${SDL2_MIXER_LIBRARIES}\n\t"
                    "sdl2::sdl2 sdl2_image::sdl2_image sdl2_mixer::sdl2_mixer\n"
                    "\t${ENet_LIBRARIES})")
                content = content.replace(
                    "${SDL2_LIBRARY}\n\t${SDL2_IMAGE_LIBRARIES}\n\t${SDL2_MIXER_LIBRARIES}",
                    "${SDL2_LIBRARY}\n\t${SDL2_IMAGE_LIBRARIES}\n\t${SDL2_MIXER_LIBRARIES}")
                with open(cdogs_cmake, "w") as f:
                    f.write(content)

        # 3b. Use pre-generated nanopb files in src/proto/CMakeLists.txt
        proto_cmake = os.path.join(root, "src", "proto", "CMakeLists.txt")
        if os.path.isfile(proto_cmake):
            with open(proto_cmake) as f:
                content = f.read()
            if "pre-generated nanopb" not in content:
                content = content.replace(
                    "nanopb_generate_cpp(PROTO_SRCS PROTO_HDRS msg.proto)",
                    "if(EXISTS \"${CMAKE_CURRENT_SOURCE_DIR}/msg.pb.c\")\n"
                    "    message(STATUS \"Using pre-generated nanopb files\")\n"
                    "    set(PROTO_SRCS msg.pb.c)\n"
                    "    set(PROTO_HDRS msg.pb.h)\n"
                    "else()\n"
                    "    nanopb_generate_cpp(PROTO_SRCS PROTO_HDRS msg.proto)\n"
                    "    set_source_files_properties(${PROTO_SRCS} ${PROTO_HDRS} PROPERTIES GENERATED TRUE)\n"
                    "endif()")
                # Remove the unconditional GENERATED TRUE that follows
                content = content.replace(
                    "set_source_files_properties(${PROTO_SRCS} ${PROTO_HDRS}\n    PROPERTIES GENERATED TRUE)",
                    "")
                # Add nanopb library link to cdogs_proto (skipped when not using nanopb_generate_cpp)
                content = content.replace(
                    "add_library(cdogs_proto STATIC ${PROTO_SRCS} ${PROTO_HDRS} msg.options msg.proto)",
                    "add_library(cdogs_proto STATIC ${PROTO_SRCS} ${PROTO_HDRS} msg.options msg.proto)\n"
                    "target_link_libraries(cdogs_proto nanopb::nanopb)")
                with open(proto_cmake, "w") as f:
                    f.write(content)

        # 4. APPEND Conan targets to test executables, keep MODULE vars.
        tests_cmake = os.path.join(root, "src", "tests", "CMakeLists.txt")
        if os.path.isfile(tests_cmake):
            with open(tests_cmake) as f:
                content = f.read()
            if "sdl2::sdl2" not in content:
                content = content.replace(
                    "\t${SDL2_IMAGE_LIBRARIES}\n\t${EXTRA_LIBRARIES})",
                    "\t${SDL2_IMAGE_LIBRARIES}\n\t"
                    "sdl2::sdl2 sdl2_image::sdl2_image\n"
                    "\t${EXTRA_LIBRARIES})")
                content = content.replace(
                    "\t${SDL2_MIXER_LIBRARIES}\n\t${EXTRA_LIBRARIES})",
                    "\t${SDL2_MIXER_LIBRARIES}\n\t"
                    "sdl2::sdl2 sdl2_mixer::sdl2_mixer\n"
                    "\t${EXTRA_LIBRARIES})")
                with open(tests_cmake, "w") as f:
                    f.write(content)

    def build(self):
        apply_conandata_patches(self)
        self._patch_source(self.source_folder)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["."]
        self.cpp_info.libs = []
