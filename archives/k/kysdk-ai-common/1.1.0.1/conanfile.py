#!/usr/bin/env python3
"""Conan recipe for kysdk-ai-common 1.1.0.1 (CMake, pure C++ shared library).

Upstream: https://gitee.com/openkylin/kysdk-ai-common (tag upstream/1.1.0.1)
No external dependencies (CMakeLists.txt has no find_package).
Exposes find_package(KysdkAiCommon) with target KysdkAiCommon::KysdkAiCommon.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches
from conan.tools.scm import Git
import os
import shutil

_OFFICIAL_REPO = "https://gitee.com/openkylin/kysdk-ai-common.git"


class KysdkAiCommonConan(ConanFile):
    name = "kysdk-ai-common"
    version = "1.1.0.1"
    description = "Kylin AI common library (libkysdk-ai-common)"
    license = "GPL-3.0-or-later"
    homepage = "https://gitee.com/openkylin/kysdk-ai-common"
    url = "https://gitee.com/openkylin/kysdk-ai-common"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # pure C++ library, no external deps

    def layout(self):
        cmake_layout(self)

    def source(self):
        # gitee 归档端点(/repository/archive/...)对 conan 的 Python urllib 下载器
        # 返回 HTML 反爬页(46902B)而非 tar.gz，sha256 每次不同无法固定，
        # 故改用 Git clone 官方源 + 固定 commit（commit = tag upstream/1.1.0.1 指向）。
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
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "KysdkAiCommon")
        # CMakeDeps 默认目标名为 pkg_name::pkg_name（kysdk-ai-common::kysdk-ai-common），
        # 上游导出的 CMake 目标是 KysdkAiCommon::KysdkAiCommon，必须显式覆盖，
        # 下游 libkysdk-genai 才能按上游语义 find_package(KysdkAiCommon) 链接。
        self.cpp_info.set_property("cmake_target_name", "KysdkAiCommon::KysdkAiCommon")
        self.cpp_info.set_property("pkg_config_name", "kysdk-ai-common")
        self.cpp_info.libs = ["kysdk-ai-common"]
        self.cpp_info.includedirs = ["include"]
