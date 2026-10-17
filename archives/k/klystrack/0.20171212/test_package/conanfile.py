#!/usr/bin/env python3
"""Consumer test for klystrack 0.20171212 — verify SDL2 dep + klystrack binary."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy


class KlystrackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # CI 真根因: SDL2 包无 set_property("cmake_target_name") → CMakeDeps 不生成 SDL2Config.cmake
    # → CMake find_package(SDL2) 炸。改用 VirtualBuildEnv 注入 SDL2 包路径，裸 clang 编 test.c
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("sdl2/2.30.10")

    def build(self):
        # Copy test source to build folder（src/dst 同值致 copy() 拒绝 → 拆开避同值）
        src_dir = os.path.join(self.source_folder, "")
        dst_dir = os.path.join(self.build_folder, "src")
        os.makedirs(dst_dir, exist_ok=True)
        copy(self, "test.c", src=src_dir, dst=dst_dir)

    def generate(self):
        # 裸 clang 编 test.c 链 SDL2 验证 SDL2 包可用（避 CMakeDeps SDL2 缺 cmake target 问题）
        # SDL2 包头在 include/SDL2/SDL.h，库在 lib/libSDL2.a + libSDL2main.a
        sdl2 = self.dependencies["sdl2"]
        sdl2_inc = os.path.join(sdl2.package_folder, "include")
        sdl2_inc_sub = os.path.join(sdl2_inc, "SDL2")
        sdl2_lib = os.path.join(sdl2.package_folder, "lib")
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        test_src = os.path.join(self.build_folder, "src", "test.c")
        test_bin = os.path.join(self.build_folder, "test_klystrack")
        # klystrack 是 application（cpp_info.libs=[]），消费者无需链 klystrack 符号
        # 验证 SDL2 依赖可用即可（test.c 调 SDL_Init/SDL_Quit 真实 API）
        self._compile_cmd = (
            f'"{cc}" -O2 -I"{sdl2_inc}" -I"{sdl2_inc_sub}" '
            f'-o "{test_bin}" "{test_src}" '
            f'-L"{sdl2_lib}" -lSDL2 -lSDL2main'
        )

    def test(self):
        # 裸 clang 编 test.c（避 CMake find_package(SDL2) 炸）
        # cross_building 时 CI worker 跑不了 arm64 二进制 → 传 -DSKIP_RUNTIME_TEST 跳过运行时验证
        cross = self.settings.os != "Linux" or hasattr(self, "settings_build")
        skip_flag = "-DSKIP_RUNTIME_TEST" if cross else ""
        self.run(f'{self._compile_cmd} {skip_flag}', cwd=self.build_folder, env="conanbuild")
        if can_run(self):
            # env="conanrun" + VirtualRunEnv 自动注入运行时环境
            self.run("./test_klystrack", cwd=self.build_folder, env="conanrun")
