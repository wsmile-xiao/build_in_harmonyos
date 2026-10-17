#!/usr/bin/env python3
"""Conan recipe — fmt 9.1.0 (cmake)

上游 {fmt} 9.1.0，标准 CMake 项目，无运行时第三方依赖。
0 patch：上游源码直接可用 OHOS 工具链构建（参考 8.1.1/12.2.0 已验证配方）。

产物：libfmt.{a,so}（按 shared option）、include/fmt/*、fmt-config.cmake /
fmt-targets.cmake、lib/pkgconfig/fmt.pc、LICENSE。无 CLI（library package）。
"""
from conan import ConanFile
from conan.tools.files import get
import os
import shutil
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches


class FmtConan(ConanFile):
    name = "fmt"
    version = "9.1.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # fmt 9.1.0 无运行时第三方依赖：src/ 只用 C/C++ 标准库。
        # 测试侧依赖 gtest（随 test/ 源码 vendored），不是 package 运行时依赖。
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        # ★ os=OHOS 时 conan 默认把 CMAKE_SYSTEM_NAME 设成 "HarmonyOS"，
        # 而 cmake 装的平台文件叫 Modules/Platform/OHOS.cmake（内容就一行
        # include(Platform/Linux)），**没有 HarmonyOS.cmake**。名字对不上时
        # cmake 不报错退出，只打一句 "System is unknown to cmake" 就继续，
        # 把一批平台变量留空——其中 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空，
        # 于是链接命令里没有 -Wl,-soname, → 产物没有 DT_SONAME、也不生成版本
        # 软链。无 SONAME 会传染给下游（8.1.1 recipe 注释已详述）。
        # 必须带 os 守卫：无条件设会在 os=Linux 等别的 profile 上把 cmake
        # 正确的平台识别顶掉。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            # 不设则 CMAKE_SYSTEM_PROCESSOR 为 "unknown"，上游按它分支的判断
            # （SIMD/汇编选择等）会走错支。
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # 64 位默认可能装到 lib64/，而 conan cpp_info.libdirs 与 test_package 找 lib/。
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # 必须跟随 options.shared，不能写死 True：写死会让消费方的
        # `-o shared=False` 静默失效（conan 算出不同 package_id，内容却仍是
        # 动态库，cpp_info.libs 与实际产物对不上，下游链接才炸）。
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 上游 option：FMT_TEST/FMT_DOC 默认随 FMT_MASTER_PROJECT（顶层时 ON）。
        # 作为 Conan 依赖被构建时不是 master project，但显式关掉更稳妥。
        tc.variables["FMT_TEST"] = "OFF"
        tc.variables["FMT_DOC"] = "OFF"
        # FMT_INSTALL 默认随 master project；显式开，确保装包。
        tc.variables["FMT_INSTALL"] = "ON"
        tc.generate()

        # 依赖由 CMakeDeps 自动接线（本包无依赖，保留以与 8.1.1 一致）。
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="")
        cmake.build()

    def package(self):
        CMake(self).install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 代码签名是鸿蒙专有动作，工具在 OHOS 设备的 /data/service/hnp/bin 下。
        # 别的 profile（os=Linux）上它们不存在，必须守卫，否则 package 阶段崩。
        # 签名是内容哈希（存 .codesign 节），链接之后再改字节就失效。
        if self.settings.os != "OHOS":
            return
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        # CI 机器上工具在 /data/service/hnp/bin；开发机上同款工具装在
        # /storage/.../usr/local/bin。先试 CI 硬路径，不在再按名查 PATH，
        # 两处都没有才回退到硬路径（让 self.run 报出可读的 not found）。
        objcopy = self._resolve_sign_tool(
            "/data/service/hnp/bin/llvm-objcopy", "llvm-objcopy")
        signer = self._resolve_sign_tool(
            "/data/service/hnp/bin/binary-sign-tool", "binary-sign-tool")
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    @staticmethod
    def _resolve_sign_tool(hardcoded, fallback_name):
        """CI 硬路径优先；不在则按工具名查 PATH（开发机）；都没有回退硬路径。"""
        if os.path.exists(hardcoded):
            return hardcoded
        found = shutil.which(fallback_name)
        return found or hardcoded

    def package_info(self):
        self.cpp_info.includedirs = self._detect_include_dirs()
        self.cpp_info.libs = ['fmt']
        self.cpp_info.set_property("cmake_file_name", "fmt")
        self.cpp_info.set_property("cmake_target_name", "fmt::fmt")
        self.cpp_info.set_property("pkg_config_name", "fmt")

    # 与标准 C/C++ 头同名的文件名。含这类文件的子目录**不能**进 includedirs，
    # 否则它会被 -isystem 加进搜索路径、抢在真正的系统头前面被找到。
    # fmt 的 include/fmt/ 里有 locale.h（8.1.1 已实证 spdlog 实撞），
    # 所以 includedirs 只声明 include 这一层，不展开 include/fmt。
    _STD_HEADER_NAMES = {
        "time.h", "math.h", "string.h", "stdio.h", "stdlib.h", "assert.h",
        "errno.h", "signal.h", "limits.h", "float.h", "locale.h", "setjmp.h",
        "ctype.h", "wchar.h", "wctype.h", "complex.h", "fenv.h", "inttypes.h",
        "stdint.h", "stddef.h", "stdarg.h", "stdbool.h", "iso646.h", "uchar.h",
        "memory", "list", "array", "vector", "string", "map", "set", "queue",
        "stack", "algorithm", "functional", "utility", "thread", "mutex",
        "atomic", "chrono", "ranges", "format", "locale",
    }

    def _detect_include_dirs(self):
        """扫 include/ 下含头文件的一层子目录，连同 include 本身一起返回。

        fmt 公开头在 include/fmt/，消费方写 #include <fmt/format.h>，
        只需要 include 这一层。展开 include/fmt 反而会把其中的 locale.h
        推进 -isystem，遮蔽 musl 的 <locale.h>（见 _STD_HEADER_NAMES 注释）。
        """
        base = os.path.join(self.package_folder, "include")
        dirs = ["include"]
        if not os.path.isdir(base):
            return dirs
        for name in sorted(os.listdir(base)):
            sub = os.path.join(base, name)
            if not os.path.isdir(sub):
                continue
            try:
                direct = os.listdir(sub)
            except OSError:
                continue
            if any(f in self._STD_HEADER_NAMES for f in direct):
                continue
            for _root, _d, files in os.walk(sub):
                if any(f.endswith((".h", ".hpp", ".hh", ".hxx")) for f in files):
                    dirs.append("include/" + name)
                    break
        return dirs
