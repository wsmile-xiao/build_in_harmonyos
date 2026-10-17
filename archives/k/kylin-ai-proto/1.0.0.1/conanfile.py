#!/usr/bin/env python3
"""Conan recipe for kylin-ai-proto 1.0.0.1 (CMake, pure protocol/data package).

Upstream: https://gitee.com/openkylin/kylin-ai-proto (tag build/1.0.0.1-ok0.3)
This is an INTERFACE library (add_library(KylinAiProto INTERFACE)) — no code is
compiled.  The payload is the AI protocol definitions (gdbus XML + grpc proto)
installed under share/kylin-ai/protocols/ plus the CMake package config under
lib/cmake/KylinAiProto/.  It exposes find_package(KylinAiProto) with the
exported target KylinAiProto::KylinAiProto.

No external dependencies (CMakeLists.txt has no find_package).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches
from conan.tools.scm import Git
import os
import shutil

_OFFICIAL_REPO = "https://gitee.com/openkylin/kylin-ai-proto.git"


class KylinAiProtoConan(ConanFile):
    name = "kylin-ai-proto"
    version = "1.0.0.1"
    description = "Kylin AI protocol definitions (gdbus XML + grpc proto)"
    license = "GPL-3.0-or-later"
    homepage = "https://gitee.com/openkylin/kylin-ai-proto"
    url = "https://gitee.com/openkylin/kylin-ai-proto"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # pure protocol/data package, no external deps

    def layout(self):
        cmake_layout(self)

    def source(self):
        # gitee 归档端点(/repository/archive/...)对 conan 的 Python urllib 下载器
        # 返回 HTML 反爬页而非 tar.gz，sha256 每次不同无法固定，
        # 故改用 Git clone 官方源 + 固定 tag（build/1.0.0.1-ok0.3）。
        # 注意：export_conandata_patches 已把 patches/ 放进 source 目录，
        # 目标 "." 非空，git clone 会 128 失败，故克隆到临时子目录再搬回。
        git = Git(self)
        tmp = "_git_src"
        clone_args = ["--branch", self.conan_data["sources"]["tag"], "--depth", "1"]
        try:
            git.clone(url=self.conan_data["sources"]["url"], target=tmp, args=clone_args)
        except Exception:
            # W3/CI 预下载会把 conandata.yml 的 URL（含备用字段）全部改写成
            # file:// 快照（curl 抓的普通文件，不是 git 裸仓库，clone 报
            # invalid gitfile format），回退必须用硬编码官方源常量。
            git = Git(self)
            git.clone(url=_OFFICIAL_REPO, target=tmp, args=clone_args)
        for item in os.listdir(os.path.join(self.source_folder, tmp)):
            shutil.move(os.path.join(self.source_folder, tmp, item), self.source_folder)
        shutil.rmtree(os.path.join(self.source_folder, tmp), ignore_errors=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # aarch64 上 GNUInstallDirs 默认可能选 lib64/；conan cpp_info 与 CMakeDeps
        # 都按 lib/ 找，统一固定到 lib/（含 lib/cmake/KylinAiProto 配置目录）。
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游仓库无独立 LICENSE 文件，版权信息见 debian/copyright (GPL-3+)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "KylinAiProto")
        # CMakeDeps 默认目标名为 pkg_name::pkg_name（kylin-ai-proto::kylin-ai-proto），
        # 上游导出的 CMake 目标是 KylinAiProto::KylinAiProto，必须显式覆盖，
        # 下游才能按上游语义 find_package(KylinAiProto) 使用。
        self.cpp_info.set_property("cmake_target_name", "KylinAiProto::KylinAiProto")
        self.cpp_info.set_property("pkg_config_name", "kylin-ai-proto")
        # INTERFACE 库：无 lib/include 产物，仅分发协议文件 + CMake 配置
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
