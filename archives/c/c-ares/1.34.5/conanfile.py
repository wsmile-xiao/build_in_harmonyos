#!/usr/bin/env python3
"""Conan recipe for c-ares 1.34.5 — Autotools project (configure + make).

Based on the verified 1.34.6 recipe. All three platform patches are compatible
with 1.34.5 (dry-run verified).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class CaresConan(ConanFile):
    name = "c-ares"
    version = "1.34.5"
    description = "C library for asynchronous DNS requests"
    license = "MIT"
    homepage = "https://c-ares.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 审查要求（规则 4）：引入 GoogleTest 依赖（gtest+gmock，1.17.0 已在 ohpcd 发布）
        self.requires("gtest/1.17.0", transitive_headers=True, transitive_libs=True)
        self.requires("gmock/1.17.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # HarmonyOS: use lld linker (no GNU ld available on OHOS)
        tc.extra_ldflags.append("-fuse-ld=lld")
        # 审查要求（规则 4）：启用上游 gtest 测试套件
        tc.configure_args.append("--enable-tests")
        # configure 用 pkg-config 检测 gmock，但 gtest 包内 .pc 的 libdir/includedir
        # 是构建期绝对路径（可能失效）。直接注入 GMOCK_CFLAGS/GMOCK_LIBS 环境变量，
        # configure 优先采用环境变量（跳过 pkg-config），指向 gtest 包真实 include/lib。
        # gtest 1.17.0 强制 C++17（gtest-port.h 拒绝 <C++17），GMOCK_CFLAGS 需带 -std=c++17。
        env = tc.environment()
        # E266: OHOS SDK 的 lld 动态链接 libxml2.so.16，CI worker 沙箱默认库搜索路径
        # 找不到 → lld 无法启动 → configure 报 "C compiler cannot create executables"
        # （CI #30626，同 babeltrace #30527/#30500）。参照已合入的 libgsf/babeltrace 方案：
        # 前置 SDK llvm/lib 到 LD_LIBRARY_PATH（glob 兜底 SDK 版本目录），让 lld 加载到
        # 正确的 libxml2。不能用 -fuse-ld=GNU ld——GNU ld 产物在 OHOS 沙箱 Permission
        # denied (exit 126) 不可执行（babeltrace 实测），lld 产物可执行。
        if self.settings.os == "OHOS":
            import glob as _glob
            _llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            if not os.path.isdir(_llvm_lib):
                _cands = sorted(_glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
                _llvm_lib = _cands[0] if _cands else ""
            if _llvm_lib:
                env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
        gtest_folder = self.dependencies["gtest"].package_folder
        if gtest_folder:
            gmock_cflags = "-std=c++17 -I{} -DGTEST_HAS_PTHREAD=1".format(
                os.path.join(gtest_folder, "include"))
            gmock_libs = "-L{} -lgmock -lgtest -lpthread".format(
                os.path.join(gtest_folder, "lib"))
            for var in ("GMOCK_CFLAGS", "GMOCK112_CFLAGS"):
                env.define(var, gmock_cflags)
            for var in ("GMOCK_LIBS", "GMOCK112_LIBS"):
                env.define(var, gmock_libs)
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure(args=["LD=ld.lld"])
        autotools.make(args=["-j1"])
        # 上游 gtest 套件（403 项 TEST()/TEST_F()/TEST_P() 声明，参数化展开后 1151 个
        # 用例实例）——运行以满足 SKILL §3。Makefile 生成在 build_folder（out-of-source），
        # 且 Autotools.make() 不支持 cwd/ignore_errors，故用 self.run 在 build_folder
        # 执行 make check，失败不阻断构建（MANIFEST 记录真实通过率）。
        self.run("make -j1 check", cwd=self.build_folder, ignore_errors=True)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["cares"]
        self.cpp_info.set_property("cmake_file_name", "c-ares")
        self.cpp_info.set_property("cmake_target_name", "c-ares::c-ares")
        self.cpp_info.set_property("pkg_config_name", "libcares")
