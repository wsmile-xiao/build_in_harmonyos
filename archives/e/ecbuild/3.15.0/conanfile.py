#!/usr/bin/env python3
"""Conan recipe — ecbuild 3.15.0 (cmake)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
import os
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches


class EcbuildConan(ConanFile):
    name = "ecbuild"
    version = "3.15.0"
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

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        # ★ 这一行是本路线的全部意义所在。
        # os=OHOS 时 conan 默认把 CMAKE_SYSTEM_NAME 设成 "HarmonyOS"，而 cmake 装的平台文件叫
        # Modules/Platform/OHOS.cmake（内容就一行 include(Platform/Linux)），**没有 HarmonyOS.cmake**。
        # 名字对不上时 cmake 不会报错退出，只打一句 "System is unknown to cmake" 就继续，
        # 把一批平台变量留空——其中 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空，
        # 于是链接命令里没有 -Wl,-soname, → 产物没有 DT_SONAME、也不生成版本软链。
        #
        # 无 SONAME 会**传染给下游**：链接器会把本库的绝对路径原样写进消费方的 DT_NEEDED，
        # 烤死包目录哈希，换机器/清 cache 后消费方在加载期炸（expat → fontconfig 实证）。
        tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
        # 不设则 CMAKE_SYSTEM_PROCESSOR 为 "unknown"，上游按它分支的判断（SIMD/汇编选择等）会走错支。
        tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # 64 位默认可能装到 lib64/，而 conan cpp_info.libdirs 与 test_package 找 lib/。
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["BUILD_SHARED_LIBS"] = True
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()
        # 走这条路线的**理由**：依赖由 CMakeDeps 自动接线，不必像裸 cmake 路那样
        # 逐个手工补 -DX_DIR=... / 预设 find 缓存变量。
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="")
        cmake.build()

    def package(self):
        CMake(self).install()
        # ── 补 VERSION 文件（上游 install 规则漏了）────────────────────────────
        # ecbuild-config-version.cmake 第 2 行：
        #     ecbuild_parse_version_file(${CMAKE_CURRENT_LIST_DIR}/VERSION PREFIX PACKAGE)
        # 它要在**宏目录里**读 VERSION，而上游只 `install(DIRECTORY cmake ...)`，
        # 仓库根的 VERSION 文件没被装进去 → 版本解析失败 → CMake 判该 config「不可用」
        # → 下游报 "Could not find a package configuration file provided by ecbuild"。
        #
        # 这个报错极具误导性：文件明明在、路径也给对了（ecbuild_DIR / CMAKE_PREFIX_PATH
        # 都指向它），CMake 却说找不到——因为**版本检查不过时 CMake 就当没找到**，
        # 不会告诉你是版本文件的问题。
        import os, shutil
        _src = os.path.join(self.source_folder, "VERSION")
        for _d in (os.path.join(self.package_folder, "share", "ecbuild", "cmake"),
                   os.path.join(self.package_folder, "lib", "cmake", "ecbuild")):
            if os.path.isdir(_d) and os.path.isfile(_src):
                shutil.copy2(_src, os.path.join(_d, "VERSION"))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted（cmake/SDK-toolchain 产的自签无效，且 conan install 复制会破坏链接器自签）。
        # ① lib/ 的 .so  ② bin/ 的 ELF 可执行文件（llvm-config/xxx CLI 等）——产可执行文件的包必须签 bin。
        import glob, os
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        import os
        # ecbuild 既无库也无头，只有 CMake 模块 —— conan 的标准打包模型围绕「库+头」设计，
        # 这类包要显式接线，否则下游 find_package 到的是 conan 生成的空壳 config，
        # 拿不到 ecbuild_add_option 等命令（**find_package 会成功**，命令却不可用，
        # 报错要等下游真正用到宏时才出现）。
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

        # 宏文件装在 share/ecbuild/cmake/。注意上游还装了一份
        # lib/cmake/ecbuild/ecbuild-config.cmake，它用相对路径 `../../../cmake` 找宏目录，
        # 在我们的布局下会指到不存在的 <prefix>/cmake —— 别让下游命中那一份。
        _macros = os.path.join("share", "ecbuild", "cmake")
        self.cpp_info.builddirs = [_macros]

        # cmake_build_modules 让 CMakeDeps 生成的 config **主动 include 上游的入口**，
        # 从而把 ecbuild 的全部宏注入下游作用域。这是 conan 对「CMake 模块包」的原生机制。
        self.cpp_info.set_property("cmake_build_modules",
                                   [os.path.join(_macros, "ecbuild-config.cmake")])
        self.cpp_info.set_property("cmake_file_name", "ecbuild")

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
