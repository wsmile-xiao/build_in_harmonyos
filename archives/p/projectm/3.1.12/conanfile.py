#!/usr/bin/env python3
"""Conan recipe for projectM 3.1.12 — Milkdrop audio visualizer library
(C++, autotools build — 3.1.12 is the 2020 release using autotools).

Build: autogen.sh → configure → make (3.1.12 ships no pre-generated
configure; GLES3 comes from the OHOS SDK (system-provided, like Vulkan);
glm is required from ohpcd.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class ProjectMConan(ConanFile):
    name = "projectm"
    version = "3.1.12"
    description = "Milkdrop audio visualizer library (libprojectM)"
    license = "LGPL-2.1"
    homepage = "https://github.com/projectM-visualizer/projectm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    package_type = "library"

    def requirements(self):
        # glm: OpenGL mathematics (ohpcd); GLES3 is system-provided (OHOS SDK)
        self.requires("glm/0.9.9.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # autotools: release 发布包自带预生成 configure（绕过 autogen.sh
        # 的 aclocal 依赖）；OHOS 上 configure 无法 guess build type，
        # 显式 --build/--host；禁用 Qt/SDL/LLVM（OHOS 无），启用 GLES
        # （OHOS SDK 系统提供）
        # E011: HMDFS umask 077 — configure 的 umask 077 + mktemp 临时目录
        # 权限问题（Permission denied on subs1.awk）→ sed 改 umask 022
        self.run(
            "sed -i 's/umask 077/umask 022/' configure",
            cwd=self.source_folder)
        # SOIL2.c 在无 GLES 宏时走 X11 分支 include GL/glx.h（OHOS 无）——
        # -DSOIL_GLES2 强制 GLES2 分支（include GLES2/gl2.h，OHOS SDK 提供）
        # -UNDEBUG cancels NDEBUG so Parser::test() (#ifndef NDEBUG) builds
        # (Expr::test() stays unavailable: LLVM 20 API is incompatible with
        # projectM 3.1.12 — make_unique/getBasicBlockList removed — ohpcd has
        # only llvm/20.1.0, no older LLVM; attempts documented)
        self.run(
            f"./configure --build=aarch64-linux-gnu --host=aarch64-linux-gnu "
            f"--disable-shared --enable-static "
            f"--enable-qt=no --enable-sdl=no --enable-llvm=no --enable-gles=yes "
            f"CFLAGS='-DSOIL_GLES2 -UNDEBUG' "
            f"CXXFLAGS='-DSOIL_GLES2 -UNDEBUG -std=c++17'",
            cwd=self.source_folder)
        # make CXXFLAGS override: configure's CXXFLAGS may not reach subdir
        # compiles — Expr.cpp needs -std=c++17 for LLVM headers
        # (std::remove_cv_t, verified) + -UNDEBUG for Parser::test()
        self.run("make -j1 "
                 "CXXFLAGS='-DSOIL_GLES2 -UNDEBUG -std=c++17'",
                 cwd=self.source_folder)

    def package(self):
        src_lib = os.path.join(self.source_folder, "src", "libprojectM",
                               ".libs", "libprojectM.a")
        if not os.path.isfile(src_lib):
            raise ConanException(f"libprojectM.a missing: {src_lib}")
        lib = os.path.join(self.package_folder, "lib")
        os.makedirs(lib, exist_ok=True)
        shutil.copy2(src_lib, os.path.join(lib, "libprojectM.a"))
        inc = os.path.join(self.package_folder, "include")
        shutil.copytree(
            os.path.join(self.source_folder, "src", "libprojectM"),
            os.path.join(inc, "libprojectM"))
        if not os.path.isfile(os.path.join(inc, "libprojectM", "projectM.hpp")):
            raise ConanException("projectM.hpp missing")

    def package_info(self):
        self.cpp_info.libs = ["projectM"]
