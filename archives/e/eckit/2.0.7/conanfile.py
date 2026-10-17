#!/usr/bin/env python3
"""Conan recipe — eckit 2.0.7 (cmake)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
import os
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches


class EckitConan(ConanFile):
    name = "eckit"
    version = "2.0.7"
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
        self.requires("ecbuild/3.15.0")
        self.requires("libaec/1.1.7")
        self.requires("libzip/1.11.4")
        self.requires("bzip2/1.0.8")
        self.requires("eigen/3.4.0")
        self.requires("lz4/1.10.0")

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
        tc.variables["ENABLE_MPI"] = "OFF"
        tc.variables["ENABLE_ECKIT_CMD"] = "OFF"
        tc.variables["ENABLE_BUILD_TOOLS"] = "OFF"
        tc.variables["ENABLE_TESTS"] = "OFF"
        tc.variables["ENABLE_EIGEN"] = "ON"
        tc.variables["ENABLE_AEC"] = "ON"
        tc.variables["ENABLE_ZIP"] = "ON"
        tc.variables["ENABLE_BZIP2"] = "ON"
        tc.variables["ENABLE_LZ4"] = "ON"
        tc.variables["ENABLE_RADOS"] = "OFF"
        tc.variables["ENABLE_MKL"] = "OFF"
        tc.variables["ENABLE_OMP"] = "OFF"
        tc.variables["ENABLE_SNAPPY"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        # ── ecbuild 接线（手工，原因见下）─────────────────────────────────
        # eckit 的第 14 行是：
        #   find_package( ecbuild 3.7 REQUIRED HINTS ${CMAKE_CURRENT_SOURCE_DIR}
        #                                             ${CMAKE_CURRENT_SOURCE_DIR}/../ecbuild)
        # 带 HINTS 且我们把 CMAKE_SYSTEM_NAME 设成了 OHOS（CMAKE_CROSSCOMPILING=TRUE），
        # find_package 会走 CMAKE_FIND_ROOT_PATH 过滤，CMakeDeps 放在 generators 里的
        # config 可能被挡掉——实测报 "Could not find a package configuration file
        # provided by ecbuild"，而那个文件明明已经生成了。
        # 直接给 ecbuild_DIR 指到包内宏目录，绕过搜索逻辑（skill「cmake 库依赖库」一节的做法）。
        _ecb = self.dependencies["ecbuild"].package_folder
        tc.variables["ecbuild_DIR"] = _ecb + "/share/ecbuild/cmake"
        tc.variables["ecbuild_ROOT"] = _ecb
        # 让 ecbuild 的宏目录进 CMAKE_MODULE_PATH，include(ecbuild) 才找得到入口
        tc.variables["CMAKE_MODULE_PATH"] = _ecb + "/share/ecbuild/cmake"
        # 我们把 CMAKE_SYSTEM_NAME 设成 OHOS → CMAKE_CROSSCOMPILING=TRUE →
        # find_package 的 config 搜索会走 CMAKE_FIND_ROOT_PATH 过滤。
        # 依赖的包目录虽然在 root path 里，但 MODE_PACKAGE 若为 ONLY，
        # 命中范围仍可能与预期不符。显式放宽这三项（skill「cmake 库依赖库」一节）。
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_INCLUDE"] = "BOTH"
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_LIBRARY"] = "BOTH"
        tc.generate()
        # 走这条路线的**理由**：依赖由 CMakeDeps 自动接线，不必像裸 cmake 路那样
        # 逐个手工补 -DX_DIR=... / 预设 find 缓存变量。
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # ⚠️ **必须走命令行 -D，不能只靠 tc.variables**。
        # eckit 的 CMakeLists 第 14 行 find_package(ecbuild) 在第 16 行 project() **之前**，
        # 而 CMAKE_TOOLCHAIN_FILE 是在 project()/enable_language() 时才被加载的 ——
        # 那之前 toolchain 里设的 ecbuild_DIR / CMAKE_PREFIX_PATH / CMAKE_MODULE_PATH
        # **统统还不存在**。实测 --debug-find-pkg=ecbuild 的搜索路径里
        # 完全没有依赖包目录，只有环境默认路径。
        # 命令行 -D 建的是 cache 项，在任何 CMakeLists 语句之前就已生效。
        _ecb = self.dependencies["ecbuild"].package_folder
        # LZ4 的老式变量接线（见下方说明）
        _l = self.dependencies["lz4"].cpp_info
        _lz4_inc = _l.includedirs[0] if _l.includedirs else ""
        _lz4_libdir = _l.libdirs[0] if _l.libdirs else ""
        _lz4_name = _l.libs[0] if _l.libs else "lz4"
        # **不要拼文件名**。第一版写死 lib<name>.so，实际包里不是这个名字，
        # make 报 "No rule to make target '.../liblz4.so'"。
        # 实际去目录里找：优先无版本号的 .so（链接用），退而取带版本的，再退静态库。
        import glob as _glob
        _cands = (sorted(_glob.glob(_lz4_libdir + "/lib" + _lz4_name + ".so")) or
                  sorted(_glob.glob(_lz4_libdir + "/lib" + _lz4_name + ".so.*")) or
                  sorted(_glob.glob(_lz4_libdir + "/lib" + _lz4_name + ".a")))
        _lz4_lib = _cands[0] if _cands else ""
        self.output.info("LZ4_LIBRARIES 解析为: %s（目录 %s 内容: %s）"
                         % (_lz4_lib, _lz4_libdir,
                            ", ".join(sorted(__import__("os").listdir(_lz4_libdir))[:8])
                            if _lz4_libdir else "-"))
        cmake.configure(build_script_folder="", cli_args=[
            '-Decbuild_DIR=%s/share/ecbuild/cmake' % _ecb,
            # ecbuild 的 OS 白名单没有 HarmonyOS，上游报错里给的开关
            '-DDISABLE_OS_CHECK=ON',
            # eckit 对 LZ4 用**老式变量**接线（src/eckit/CMakeLists.txt:926/934
            # 直接引用 "${LZ4_INCLUDE_DIRS}" / "${LZ4_LIBRARIES}"），
            # 而 CMakeDeps 只生成 modern target `lz4::lz4`、不设这两个变量 →
            # 变量为空 → `#include "lz4.h"` 找不到头。
            #
            # ⚠️ 对照：同一文件 940 行的 AEC 走的是 target（$<...:libaec::aec>），
            # 所以 libaec 不用额外接线就生效。**同一个库里两种风格并存**——
            # 不能因为一个依赖通了就假定其余的也通，得逐个看它在 CMakeLists 里怎么被引用。
            '-DLZ4_INCLUDE_DIRS=%s' % _lz4_inc,
            '-DLZ4_LIBRARIES=%s' % _lz4_lib,
        ])
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
        explicit_libs = ['eckit']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "eckit")
        self.cpp_info.set_property("cmake_target_name", "eckit::eckit")
        pkg = "eckit" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
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
