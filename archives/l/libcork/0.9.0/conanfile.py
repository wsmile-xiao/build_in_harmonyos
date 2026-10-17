#!/usr/bin/env python3
"""Conan recipe — libcork 0.9.0 (cmake)

OHOS 适配要点：
- CMakeLists.txt 增加 CORK_BUILD_TESTS 选项（patch 0002）：
  上游单元测试依赖外部 check 框架，OHOS 包构建默认关闭，
  保持上游源码行为不变（选项 ON 时仍构建测试）。
- src/CMakeLists.txt 使用 BUILD_SHARED_LIBS 控制共享/静态（patch 0003），
  与 Conan shared 选项语义一致（cork 非系统同名库，不适用 R26 静态强制）。
- version.sh 修正：无 .git 的源码包(conan get)下 git describe 失败，
  需回退 RELEASE-VERSION；脚本 shebang 改为 /usr/bin/env bash（patch 0001）。
"""
from conan import ConanFile
from conan.tools.files import get, save, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMakeToolchain, CMakeDeps, cmake_layout


class LibcorkConan(ConanFile):
    name = "libcork"
    version = "0.9.0"
    description = "A simple, easily embeddable cross-platform C library"
    license = "MIT"
    homepage = "https://github.com/dcreager/libcork"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # version.sh 在无 .git 的源码包中无法用 git describe 取版本，
        # 写入 RELEASE-VERSION 作为回退（与上游 make-dist.sh 行为一致）。
        save(self, "RELEASE-VERSION", f"{self.version}\n")

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # R26: 系统同名库默认静态
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 上游测试依赖 check 框架，包构建默认关闭
        tc.variables["CORK_BUILD_TESTS"] = "OFF"
        # 上游 cmake_minimum_required(2.6) 过旧，cmake>=3.5 移除旧兼容，需放开策略下限
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # OHOS 交叉工具链由 profile conf tools.build:compiler_executables 提供
        tc.generate()

    def build(self):
        # OHOS 交叉编译由 profile conf tools.build:compiler_executables 提供
        # （bootstrap 审计已确认 clang 工具链在 PATH 中），CMake 直接构建即可
        apply_conandata_patches(self)
        from conan.tools.cmake import CMake
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        from conan.tools.cmake import CMake
        cmake = CMake(self)
        cmake.install()
        if self.options.shared:
            self._sign_shared_libs()

    def _sign_shared_libs(self):
        import glob
        import os
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so*"), recursive=True)
        if not sos:
            return
        # 签名工具路径由环境注入（OHOS_TOOLCHAIN_BIN），CI/制品流水线按环境提供
        tc_bin = os.environ.get("OHOS_TOOLCHAIN_BIN", "")
        if not tc_bin:
            return
        objcopy = os.path.join(tc_bin, "llvm-objcopy")
        signer = os.path.join(tc_bin, "binary-sign-tool")
        for so in sos:
            if os.path.islink(so):
                continue
            # 首次签名前 .codesign section 不存在属预期，忽略该分支错误
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        # src/CMakeLists.txt 将 target OUTPUT_NAME 设为 cork → libcork.so/.a
        self.cpp_info.libs = ["cork"]
        self.cpp_info.set_property("cmake_file_name", "libcork")
        self.cpp_info.set_property("cmake_target_name", "libcork::libcork")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]