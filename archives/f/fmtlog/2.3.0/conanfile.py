#!/usr/bin/env python3
"""Conan recipe — fmtlog 2.3.0 (cmake)

上游 fmtlog 2.3.0：CMake 工程，依赖 fmt 库（上游以 git submodule 形式
锁定 fmt commit 9cf9f38 = fmt 11.1.3）。GitHub tarball 不含子模块内容，
故按 conan 惯例在 conandata.submodules 中 vendored 下载 fmt 源码到 fmt/。
registry 的 fmt 12.2.0 与 fmtlog 2.3.0 的 fmt::detail 内部 API
（named_arg 模板参数顺序 <Char,T> → <T,Char>）不兼容，因此不 declares
registry fmt，而是使用上游锁定的 fmt 源码随包一起构建（同 adlplug 先例）。

产物：libfmtlog-static.a / libfmtlog-shared.so、include/fmtlog.h +
include/fmtlog-inl.h、嵌入 fmt 的 include/fmt/* 与 libfmt.a（编译期模板依赖）。
无 CLI（library package）。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class FmtlogConan(ConanFile):
    name = "fmtlog"
    version = "2.3.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # vendored fmt 子模块（上游锁定 commit，GitHub tarball 不含 submodule）
        for _name, info in self.conan_data.get("submodules", {}).items():
            get(
                self,
                url=info["url"],
                sha256=info["sha256"],
                destination=os.path.join(self.source_folder, info["destination"]),
                strip_root=True,
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        # ★ os=OHOS 时 conan 默认把 CMAKE_SYSTEM_NAME 设成 "HarmonyOS"，
        # 而 cmake 平台文件叫 Modules/Platform/OHOS.cmake，没有 HarmonyOS.cmake，
        # 名字对不上会导致平台变量留空（无 SONAME 等）。必须带 os 守卫：
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # 64 位默认可能装到 lib64/，而 conan cpp_info.libdirs 找 lib/。
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # fmtlog 顶层 CMakeLists 无 BUILD_SHARED_LIBS 开关（自行 add_library
        # fmtlog-static / fmtlog-shared 两个 target），此处仅对齐 conan 惯例。
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        """OHOS 产物需代码签名才能加载；工具在 CI 机 /data/service/hnp/bin。"""
        if self.settings.os != "OHOS":
            return
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = self._resolve_sign_tool(
            "/data/service/hnp/bin/llvm-objcopy", "llvm-objcopy")
        signer = self._resolve_sign_tool(
            "/data/service/hnp/bin/binary-sign-tool", "binary-sign-tool")
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    @staticmethod
    def _resolve_sign_tool(hardcoded, fallback_name):
        if os.path.exists(hardcoded):
            return hardcoded
        found = __import__("shutil").which(fallback_name)
        return found or hardcoded

    def package_info(self):
        # fmtlog.h 依赖 fmt 头（#include "fmt/format.h"），fmt 是 vendored 子模块，
        # 其头文件与静态库（libfmt.a）随本包 install 进 include/fmt 与 lib/。
        # fmtlog-static 对 fmt 有 4 个未定义符号（vformat_to/vformat/report_error/
        # assert_fail），静态模式消费方必须同时链接 libfmt.a；共享模式 fmtlog-shared
        # 已在链接期吸收 fmt，无需再列。
        if self.options.shared:
            self.cpp_info.libs = ["fmtlog-shared"]
        else:
            self.cpp_info.libs = ["fmtlog-static", "fmt"]
        self.cpp_info.set_property("cmake_file_name", "fmtlog")
        self.cpp_info.set_property("cmake_target_name", "fmtlog::fmtlog")
        self.cpp_info.set_property("pkg_config_name", "fmtlog")