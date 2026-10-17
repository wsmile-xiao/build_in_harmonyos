#!/usr/bin/env python3
"""Conan recipe — libaec 1.1.7 (cmake)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
import os
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches


class LibaecConan(ConanFile):
    name = "libaec"
    version = "1.1.7"
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
        self.cpp_info.set_property("cmake_file_name", "libaec")

        # **必须按组件声明，不能只给聚合 target。**
        # 上游自己的 libaec-config.cmake 导出的是 libaec::sz 与 libaec::aec 两个 target，
        # 下游按这两个名字链接 —— HDF5 1.14.6 的 CMakeFilters.cmake 就是：
        #     find_package(libaec ... OPTIONAL_COMPONENTS shared)   # 纯 Config 模式
        #     set(LINK_COMP_LIBS ${LINK_COMP_LIBS} libaec::sz libaec::aec)
        # 若这里只设 cmake_target_name=libaec::libaec，CMakeDeps 生成的 config 里
        # 就只有那一个聚合 target，HDF5 会报 "Target libaec::sz not found"——
        # 而这**发生在下游构建期**，本包自己的 test_package 完全测不出来。
        #
        # sz 是 szip 兼容层（HDF5 实际消费的就是它，其 DT_NEEDED 为 libsz.so.2），
        # 且 libsz 里已内含 aec 的对象文件，故 sz 不对 aec 声明 requires。
        self.cpp_info.components["sz"].libs = ["sz"]
        self.cpp_info.components["sz"].set_property("cmake_target_name", "libaec::sz")
        self.cpp_info.components["sz"].set_property("pkg_config_name", "szip")

        self.cpp_info.components["aec"].libs = ["aec"]
        self.cpp_info.components["aec"].set_property("cmake_target_name", "libaec::aec")
        self.cpp_info.components["aec"].set_property("pkg_config_name", "libaec")

        self.cpp_info.set_property("pkg_config_name", "libaec")
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
