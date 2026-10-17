#!/usr/bin/env python3
"""Conan recipe for sems-dsm 2.1.0 — SEMS DSM state-machine interpreter plug-in
on HarmonyOS PC (aarch64-linux-ohos)."""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, mkdir
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
import os


class SemsDsmConan(ConanFile):
    name = "sems-dsm"
    version = "2.1.0"
    description = "SEMS DSM state-machine interpreter plug-in (sems-server/sems 2.1.0, core + dsm app module)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/sems-server/sems"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 实测（sems-opus 同源 core 依赖，制品仓已有）
        self.requires("libevent/2.1.12")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 仅构建 core 静态库 + dsm app 模块；禁用其余可选组件
        tc.variables["SEMS_USE_OPUS"] = "OFF"
        tc.variables["SEMS_USE_ILBC"] = "OFF"
        tc.variables["SEMS_USE_MONITORING"] = "OFF"
        tc.variables["SEMS_USE_PYTHON"] = "OFF"
        tc.variables["SEMS_USE_IPV6"] = "ON"
        # 裁剪全部 app 模块（dsm 除外）：dsm 在 apps 层由 sems_add_app_module(dsm) 引入
        tc.variables["EXCLUDE_APP_MODULES"] = ("ann_b2b announce_transfer announcement annrecorder "
            "callback click2dial conference db_reg_agent diameter_client early_announce "
            "early_dbprompt jsonrpc mobile_push monitoring mp3 msg_storage mwi precoded_announce "
            "reg_agent registrar_client sbc siprec_srs voicebox voicemail webconference "
            "xmlrpc2di conf_auth ivr mailbox pin_collect")
        # R26/OHOS: 静态 core
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # patches/0002 引用 LIBEVENT2_*：注入 conan 依赖的探测变量与
        # 静态库完整路径（musl 无 rpath，共享 libevent 运行时加载失败，
        # 与 sems-opus 同款方案）
        lev = self.dependencies["libevent"]
        tc.variables["LIBEVENT2_INCLUDE_DIR"] = lev.cpp_info.includedirs[0]
        tc.variables["LIBEVENT2_LIB_DIR"] = lev.cpp_info.libdirs[0]
        lev_libs = [os.path.join(lev.cpp_info.libdirs[0], f"libevent{suffix}.a")
                    for suffix in ("", "_pthreads")]
        # CMake 列表语义：分号分隔（空格会被当成单个文件名目标）
        tc.variables["LIBEVENT2_LIBRARIES"] = ";".join(
            p for p in lev_libs if os.path.exists(p))
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # core/sip 静态库 + dsm app 模块（上游 sems_add_app_module 生成
        # 目标名 sems_<name>，实测 TargetDirectories: sems_dsm）
        cmake.build(target="sems_core")
        cmake.build(target="sems_sip")
        cmake.build(target="sems_dsm")
        # 上游测试（R51/rule4：core/tests 10 个 fct.h 测试源编译为单体程序，
        # 随包分发供消费者真实执行——同 sems-opus 实证方案，204/204 通过）
        cmake.build(target="sems_tests")

    def package(self):
        # dsm 插件动态模块 + core 插件接口头文件 + 应用级 DSM 文档示例
        copy(self, "dsm.so",
             src=os.path.join(self.build_folder, "apps", "dsm"),
             dst=os.path.join(self.package_folder, "lib", "sems", "plug-in"),
             keep_path=False)
        # core/sip 静态库：dsm.so 引用 420 个 core 符号（llvm-nm 实测），
        # dlopen 消费方（测试宿主/集成方）需 whole-archive 链接二者
        copy(self, "**/libsems_core.a",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "**/libsems_sip.a",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # 上游测试可执行文件（R51 rule4：随包分发供消费者真实执行）
        copy(self, "**/sems_tests",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "core", "ampi"),
             dst=os.path.join(self.package_folder, "include", "sems", "ampi"))
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "core", "amci"),
             dst=os.path.join(self.package_folder, "include", "sems", "amci"))
        # resample.cpp 被上游 target_sources 只挂到 sems/sems_tests 可执行目标，
        # 不在 sems_core 静态库内（AmAudio 引用 ResampleFactory 会缺符号）——
        # 随包分发源码供 dlopen 宿主编译补齐
        copy(self, "*.cpp",
             src=os.path.join(self.source_folder, "core", "resample"),
             dst=os.path.join(self.package_folder, "share", "sems", "src", "resample"))
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "core", "resample"),
             dst=os.path.join(self.package_folder, "share", "sems", "src", "resample"))
        # DSM 状态机图表（.dsm，位于 apps/dsm/lib/ 下；消费者语义验证输入）
        copy(self, "*.dsm",
             src=os.path.join(self.source_folder, "apps", "dsm", "lib"),
             dst=os.path.join(self.package_folder, "share", "sems", "dsm", "charts"))
        mkdir(self, os.path.join(self.package_folder, "lib", "sems", "plug-in"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # sems_tests 随包分发（R51 rule4 真实执行）
        self.cpp_info.bindirs = ["bin"]
        # core/sip 静态库：dsm.so 引用 420 个 core 符号，dlopen 插件的宿主
        # 进程需 whole-archive 链接二者以提供完整 core 符号
        self.cpp_info.libs = ["sems_core", "sems_sip"]
        self.cpp_info.system_libs = ["dl"]
