#!/usr/bin/env python3
"""Conan recipe — cppgir 2.0+git20250629.2a7d9ce (CMake).

cppgir 是 KDE 维护的 GObject-Introspection C++ 绑定生成器：解析 .gir XML
生成 C++ 头文件（namespace/class/RAII 包装）。产物为 cppgir 生成器可执行
文件 + gi/ override/ 头文件集合（INTERFACE 目标）+ cmake config 导出。

上游 Debian 快照 2.0+git20250629.2a7d9ce-2（commit 2a7d9ce），orig tarball
不含 expected-lite 子模块（Debian 打包时剥离），适配时用 expected-lite/0.10.0
头文件包补齐（拷贝 nonstd/expected.hpp 到源码 expected-lite/include/）。

构建要点（探索期实测）：
- BUILD_TOOLS=ON 需要 fmt（FMTLIB 路径，C++17）+ boost 头文件
- fmt 12.2.0 的 pkg-config Cflags 必须进编译命令（上游 CMakeLists 只
  target_link_libraries 不加 include —— PkgConfigDeps 生成 .pc 后由
  pkg-config 提供 cflags，本配方直接注入 cpp_info 编译链）
- 测试目标 gi-test/gi-test-17 需要 glib2（gobject-2.0），已引入
- expected-lite 子模块用 conan 头文件包填充

补丁：0001 修复上游测试源码中 gboolean/gint64 信号参数类型与 glib>=2.80
严格 GValue 类型校验不兼容的问题（gboolean=int→G_TYPE_INT vs 注册的
G_TYPE_BOOLEAN；gint64 在 LP64 glibconfig 中 typedef signed long 而非
long long → G_TYPE_LONG vs G_TYPE_INT64）。只改测试，不改库代码。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CppgirConan(ConanFile):
    name = "cppgir"
    version = "2.0+git20250629.2a7d9ce"
    description = "GObject-Introspection C++ binding generator (KDE)"
    license = "MIT"
    homepage = "https://invent.kde.org/libraries/cppgir"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("gobject-introspection", "gir", "cpp-binding", "generator")
    package_type = "header-library"  # INTERFACE 头库 + 生成器工具

    settings = "os", "arch", "compiler", "build_type"
    # 纯头文件库 + 构建工具，无需 shared/fPIC 选项

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 生成器运行时依赖（tools/ 代码 include fmt、boost 头）
        self.requires("fmt/12.2.0")
        self.requires("boost/1.90.0.1.1")
        # gi/ 头文件的 expected-lite 子模块（orig tarball 剥离了）
        self.requires("expected-lite/0.10.0")
        # 上游测试（BUILD_TESTING）需要 gobject-2.0
        self.requires("glib2/2.88.0.1")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 填充被 Debian tarball 剥离的 expected-lite 子模块
        # （上游 git submodule，CMakeLists INTERNAL_EXPECTED=ON 时从
        #  expected-lite/include/nonstd/expected.hpp 读）
        el = self.dependencies["expected-lite"]
        dst = os.path.join(self.source_folder, "expected-lite", "include")
        os.makedirs(dst, exist_ok=True)
        copy(self, "expected.hpp",
             src=os.path.join(el.cpp_info.includedirs[0], "nonstd"),
             dst=dst and os.path.join(dst, "nonstd"))

    def generate(self):
        tc = CMakeToolchain(self)
        # E092 系：OHOS 平台 cmake 识别
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # 关闭 examples/doc（需要 gtk/gst/gio-unix，环境不具备）
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_DOC"] = False
        # 测试打开（BUILD_TESTING 默认 ON 由 CTest include 设置）
        tc.variables["BUILD_TESTING"] = True
        # 用 fmt 库（BUILD_FMT=AUTO，C++20 std::format 在 clang15 不可用）
        tc.variables["BUILD_FMT"] = "FMTLIB"
        # 头文件安装前缀（安装到 include/cppgir）
        tc.generate()
        # fmt include 路径注入：上游 pkg_check_modules 只取 LDFLAGS，
        # 编译命令需 CFLAGS 的 -I。直接生成环境注入 CXXFLAGS。
        env = Environment()
        fmt = self.dependencies["fmt"]
        env.append("CXXFLAGS", "-I{}".format(fmt.cpp_info.includedirs[0]))
        boost = self.dependencies["boost"]
        env.append("CXXFLAGS", "-I{}".format(boost.cpp_info.includedirs[0]))
        env.vars(self).save_script("conanbuildenv_cppgir_fmt")
        # E266: lld 依赖 SDK libxml2
        if self.settings.os == "OHOS":
            env2 = Environment()
            env2.prepend_path(
                "LD_LIBRARY_PATH",
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
            )
            env2.vars(self).save_script("conanbuildenv_ohos_llvm")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游测试：gi-test + gi-test-17（C++14 与 C++17 两个口径）
        if can_run(self):
            cmake.test()

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
        # OHOS ELF 需签名（工具在 CI /data/service/hnp/bin；开发机按名查 PATH）
        if self.settings.os != "OHOS":
            return
        targets = []
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
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    @staticmethod
    def _resolve_sign_tool(hardcoded, fallback_name):
        if os.path.exists(hardcoded):
            return hardcoded
        found = shutil.which(fallback_name)
        return found or hardcoded

    def package_info(self):
        # 工具运行时需要 libc++_shared.so（OHOS SDK/系统提供）与 fmt 动态库
        if self.settings.os in ("Linux", "OHOS"):
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
            # libc++_shared.so 在 SDK aarch64-linux-ohos 与系统 /system/lib64
            for sdk_lib in (
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos",
                "/system/lib64",
            ):
                if os.path.isdir(sdk_lib):
                    self.runenv_info.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        # cppgir 主要是工具 + INTERFACE 头库。
        # 头文件在 include/cppgir（gi/ 与 override/ 及 expected-lite 的 nonstd/）
        self.cpp_info.includedirs = ["include/cppgir"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        # INTERFACE 库：无实体 .a/.so，链接的是消费方的 glib 栈
        self.cpp_info.libs = []
        # 消费方使用生成代码需要 glib 系列库
        self.cpp_info.requires = [
            "fmt::fmt",
            "boost::boost",
            "expected-lite::expected-lite",
            "glib2::glib2",
        ]
        # cmake 导出名（上游 install(EXPORT) CppGirTargets：CppGir::gi）
        self.cpp_info.set_property("cmake_file_name", "cppgir")
        self.cpp_info.set_property("cmake_target_name", "CppGir::gi")
        self.cpp_info.set_property("pkg_config_name", "cppgir")
