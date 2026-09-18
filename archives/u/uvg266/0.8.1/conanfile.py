#!/usr/bin/env python3
"""Conan recipe for uvg266 0.8.1 on HarmonyOS PC (aarch64).

uvg266 is an open-source VVC (Versatile Video Coding) encoder implemented
in C, licensed under 3-clause BSD.  It provides both a shared/static library
(libuvg266) and a CLI encoder binary (uvg266).

Build: upstream provides a CMakeLists.txt.  This recipe uses the CMake path
and builds the upstream unit tests (greatest framework) via BUILD_TESTS=ON,
running ctest inside build() so the L1 gate sees real upstream test output.
The `greatest` submodule is not shipped inside the release tarball, so it is
fetched from the exact commit pinned by upstream tag v0.8.1 (.gitmodules).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Uvg266Conan(ConanFile):
    name = "uvg266"
    version = "0.8.1"
    package_type = "library"
    description = "Open-source VVC encoder written in C (3-clause BSD)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ultravideo/uvg266"
    url = "https://github.com/ultravideo/uvg266"

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 纯 C 编码器，无第三方运行时依赖（仅系统 Threads/libm）
        pass

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # greatest 为官方子模块（.gitmodules 指向 ultravideo/greatest），
        # release tarball 不含子模块内容；按 v0.8.1 钉扎提交拉取到 greatest/。
        get(self, **self.conan_data["greatest"], strip_root=True,
            destination=os.path.join(self.source_folder, "greatest"))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTS"] = "ON"
        tc.generate()

    def build(self):
        # 依赖外部工具（ffmpeg 生成输入 / VTM DecoderAppStatic 校验解码，
        # 上游从 ultravideo.fi 下载的 x86-64 静态二进制，OHOS aarch64 无
        # 对应制品）的 shell 测试，沿用上游原生 XFAIL_TESTS 机制
        # （CMakeLists 在 configure 阶段读取该环境变量）从 ctest 注册中
        # 排除；C 单元测试 Test_uvg266 与符号检查 test_external_symbols
        # 保持注册并实际执行。详见 notes.md 测试台账。
        os.environ["XFAIL_TESTS"] = (
            "test_mtt;test_intra;test_invalid_input;test_monochrome;"
            "test_lmcs;test_tools;test_slices;test_cabac_state"
        )
        try:
            # 上游 shell 测试脚本（tests/util.sh）以 ../bin/uvg266 与
            # ../lib/libuvg266.a 相对路径调用，等价于上游 CI 的
            # "cmake -DCMAKE_INSTALL_PREFIX=./ && make install"。这里在测试前
            # 把构建产物放置到源树 bin/ 与 lib/，保持一致。
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
            src_bin = os.path.join(self.source_folder, "bin")
            src_lib = os.path.join(self.source_folder, "lib")
            os.makedirs(src_bin, exist_ok=True)
            os.makedirs(src_lib, exist_ok=True)
            build_dir = self.build_folder
            for pat, src, dst in (
                ("uvg266", None, src_bin),
                ("libuvg266.a", None, src_lib),
            ):
                cand = os.path.join(build_dir, pat)
                if not os.path.exists(cand):
                    cand = os.path.join(build_dir, "Release", pat)
                if os.path.exists(cand):
                    import shutil
                    shutil.copy2(cand, os.path.join(dst, os.path.basename(cand)))
            # L1: 上游 make check —— 实际执行 upstream 单元测试二进制
            cmake.test()
        finally:
            os.environ.pop("XFAIL_TESTS", None)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["uvg266"]
        self.cpp_info.includedirs = ["include"]
        # 构建产物含 CLI（uvg266 编码器可执行文件），R38/L0k 据此识别为 tool 类
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "uvg266")
        self.cpp_info.set_property("cmake_target_name", "uvg266::uvg266")
        self.cpp_info.set_property("pkg_config_name", "uvg266")
