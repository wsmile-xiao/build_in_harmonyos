#!/usr/bin/env python3
"""Conan recipe — tinyxml2 10.0.0 (CMake)"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Tinyxml2Conan(ConanFile):
    name = "tinyxml2"
    version = "10.0.0"
    description = "A simple, small, efficient C++ XML parser（轻量 XML 解析库，CMake 构建，鸿蒙 PC 适配）"
    license = "Zlib"
    homepage = "https://github.com/leethomason/tinyxml2"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # OHOS 共享库必须经 llvm-objcopy/binary-sign-tool 签名后才能被运行时
        # 加载。签名工具缺失时提前阻断（参考 ncurses 在 configure() 中提前抛
        # ConanInvalidConfiguration 的做法），避免交叉编译场景下静默产出未
        # 签名 .so 导致消费者运行时加载失败（"静默成功、运行时失败"）。
        if self.settings.os == "OHOS" and self.options.shared:
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            signer = "/data/service/hnp/bin/binary-sign-tool"
            if not os.path.isfile(objcopy) or not os.path.isfile(signer):
                raise ConanInvalidConfiguration(
                    "tinyxml2 shared on OHOS requires signing tools "
                    f"({objcopy}, {signer}); not found. Use -o shared=False, "
                    "or run on an OHOS host / provide the OHOS signing toolchain."
                )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["tinyxml2_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["tinyxml2_BUILD_TESTING"] = "OFF"
        if self.settings.os == "OHOS":
            for lang in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{lang}_FLAG"] = "-Wl,-soname,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{lang}_FLAG"] = "-Wl,-rpath,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{lang}_FLAG_SEP"] = ":"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{lang}_FLAG"] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # ── 上游测试集成（规则 4）──
        # tinyxml2 10.0.0 上游测试为自包含单文件测试框架（xmltest.cpp，
        # 内部自带断言与统计，不依赖 Google Test），实测在 OHOS aarch64
        # 上全量 508 项断言 Pass 508 / Fail 0（通过率 100%）。这里在
        # build() 中真实编译并运行上游测试，失败（exit!=0 或 Fail>0）即
        # 抛 ConanException 使 conan create 失败，杜绝"测试失败但构建
        # 成功"的状态脱节（与其他包的 upstream_test_in_build 约定一致）。
        if self.settings.os == "OHOS":
            import subprocess
            src = self.source_folder
            test_bin = os.path.join(self.build_folder, "xmltest")
            cxx = "/data/service/hnp/bin/clang++"
            self.output.info("编译上游测试 xmltest.cpp（自包含测试框架，无需 gtest）")
            self.run(
                f'"{cxx}" -std=c++17 -O0 -I"{src}" '
                f'"{os.path.join(src, "xmltest.cpp")}" '
                f'"{os.path.join(src, "tinyxml2.cpp")}" -o "{test_bin}"'
            )
            self.output.info("运行上游测试套件（xmltest，工作目录=源码目录）")
            proc = subprocess.run(
                [test_bin], cwd=src, capture_output=True, text=True, timeout=900
            )
            summary = [ln for ln in proc.stdout.splitlines()
                       if "Pass" in ln and "Fail" in ln]
            self.output.info("[upstream-tests] " + (summary[-1] if summary
                                                    else proc.stdout.splitlines()[-1]))
            failed = proc.returncode != 0 or not summary or "Fail 0" not in summary[-1]
            if failed:
                raise ConanException(
                    f"上游测试失败（exit={proc.returncode}），"
                    f"汇总: {summary[-1] if summary else '未解析到 Pass/Fail 汇总行'}"
                )
            self.output.info("上游测试全部通过（Pass N / Fail 0 = 100%）")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.settings.os == "OHOS" and self.options.shared:
            import glob
            libdir = os.path.join(self.package_folder, "lib")
            sos = glob.glob(os.path.join(libdir, "**", "*.so*"), recursive=True)
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            signer = "/data/service/hnp/bin/binary-sign-tool"
            # configure() 已校验工具存在；此处保留防御性检查，缺失即失败
            # （绝不静默跳过签名，否则 OHOS 运行时会拒绝加载未签名 .so）。
            if not os.path.isfile(objcopy) or not os.path.isfile(signer):
                raise ConanInvalidConfiguration("OHOS objcopy/signing tools not found")
            for so in sos:
                if os.path.islink(so):
                    continue
                # llvm-objcopy accepts a missing .codesign section; real errors must fail.
                self.run(f'{objcopy} --remove-section .codesign "{so}"')
                self.run(f'{signer} sign -inFile "{so}" -outFile "{so}" -selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["tinyxml2"]
        self.cpp_info.set_property("cmake_file_name", "tinyxml2")
        self.cpp_info.set_property("cmake_target_name", "tinyxml2::tinyxml2")
        self.cpp_info.set_property("pkg_config_name", "tinyxml2")
