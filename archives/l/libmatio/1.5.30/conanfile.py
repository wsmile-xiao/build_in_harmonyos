#!/usr/bin/env python3
"""Conan recipe — libmatio 1.5.30 (cmake)"""
from conan import ConanFile
from conan.tools.files import get
import os
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches


class LibMatioConan(ConanFile):
    name = "libmatio"
    version = "1.5.30"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def requirements(self):
        # matio 的 MAT73 需要 hdf5>=1.8 且链接方式与 matio 自身一致
        # （上游 thirdParties.cmake: HDF5_USE_STATIC_LIBRARIES 默认跟随 MATIO_SHARED）。
        # CMakeDeps 生成 hdf5-config.cmake → find_package(HDF5) 命中 hdf5::hdf5-shared/static 目标。
        self.requires("hdf5/1.14.6")
        self.requires("zlib/1.3.1.1")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # matio 与 hdf5 的动静态必须一致，否则上游 thirdParties.cmake 的
        # HDF5_USE_STATIC_LIBRARIES 与实际链接库不匹配 → undefined reference。
        self.options["hdf5"].shared = self.options.shared

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        # ★ 这个 if 块是本路线的关键（同 hdf5/netcdf 先例）。
        # os=OHOS 时 conan 默认把 CMAKE_SYSTEM_NAME 设成 "HarmonyOS"，而 cmake 装的平台文件叫
        # Modules/Platform/OHOS.cmake（内容就一行 include(Platform/Linux)），**没有 HarmonyOS.cmake**。
        # 名字对不上时 cmake 不会报错退出，只打一句 "System is unknown to cmake" 就继续，
        # 把一批平台变量留空——其中 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空，
        # 于是链接命令里没有 -Wl,-soname, → 产物没有 DT_SONAME、也不生成版本软链。
        # 无 SONAME 会**传染给下游**：链接器把本库的绝对路径写进消费方的 DT_NEEDED（expat→fontconfig 实证）。
        # 必须**带 os 守卫**：无条件设会在 os=Linux 等 profile 上把 cmake 正确的平台识别顶掉。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            # 不设则 CMAKE_SYSTEM_PROCESSOR 为 "unknown"，上游按它分支的判断会走错支。
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # 64 位默认可能装到 lib64/，而 conan cpp_info.libdirs 与 test_package 找 lib/。
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # 必须跟随 options.shared，不能写死：写死会让消费方的 `-o shared=False` 静默失效
        # （conan 算出不同 package_id，内容却仍是动态库，下游链接才炸；opencascade 7.9.3 实撞）。
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # matio 上游 CMake 选项（cmake/options.cmake）
        tc.variables["MATIO_WITH_HDF5"] = "ON"
        tc.variables["MATIO_WITH_ZLIB"] = "ON"
        tc.variables["MATIO_MAT73"] = "ON"
        # 上游官方测试：cmake/test.cmake 在 build 时调用 test/convert_at_to_ctest.py，
        # 把 test/tests/*.at 的 autotest 套件转换成 ctest 用例（与 `make check` 同源），
        # 需要 Python3 解释器（OHOS 设备上 /data/service/hnp/bin/python3 存在）。
        tc.variables["MATIO_BUILD_TESTING"] = "ON"
        # 上游选项名（cmake/options.cmake）：MATIO_SHARED 才是 matio 自己的动静态开关。
        tc.variables["MATIO_SHARED"] = self.options.shared
        tc.variables["MATIO_PIC"] = self.options.get_safe("fPIC", True)
        # 【--inject-dep-includes 生成】上游 thirdParties.cmake 的 HDF5 目标级联在
        # CMakeDeps 的 hdf5::hdf5 扁平目标下不命中 else 前的任何分支时，用大写
        # HDF5_INCLUDE_DIRS（CMakeDeps 只定义小写 hdf5_INCLUDE_DIRS）→ 空 include。
        # 补丁已加 hdf5::hdf5 分支；此处再注入 -I 兜底 zlib 等 find_package 模块模式。
        _incs = []
        for _ref, _d in self.dependencies.items():
            for _p in _d.cpp_info.includedirs:
                _incs.append("-I" + _p)
        _incflags = " ".join(dict.fromkeys(_incs))
        for _k in ("CMAKE_C_FLAGS", "CMAKE_CXX_FLAGS"):
            _old = tc.variables.get(_k, "")
            tc.variables[_k] = (str(_old) + " " + _incflags).strip()
        # 【--inject-dep-libdirs 生成】上游若用裸库名链接（而非导入目标），
        # cmake 原样传 -lxxx，没有 -L 就 unable to find library。
        _ldirs = []
        for _ref, _d in self.dependencies.items():
            for _p in _d.cpp_info.libdirs:
                _ldirs.append("-L" + _p)
        _ldflags = " ".join(dict.fromkeys(_ldirs))
        for _k in ("CMAKE_EXE_LINKER_FLAGS", "CMAKE_SHARED_LINKER_FLAGS",
                   "CMAKE_MODULE_LINKER_FLAGS"):
            _old = tc.variables.get(_k, "")
            tc.variables[_k] = (str(_old) + " " + _ldflags).strip()
        tc.generate()
        # 依赖由 CMakeDeps 自动接线，不必逐个手工补 -DX_DIR=... / 预设 find 缓存变量。
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游官方测试（TEST_QUALITY_SPEC §3.1 CMake 项目）──
        # MATIO_BUILD_TESTING=ON 时上游把 test/tests/*.at（3338 个 AT_SETUP）转成 ctest 跑，
        # 与 autotools 路线的 `make check` 完全同源同覆盖；失败即 conan create 失败。
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
        # 代码签名是**鸿蒙专有**动作，工具在 OHOS 设备的 /data/service/hnp/bin 下；
        # 在别的 profile 上它们不存在，self.run() 会失败崩掉 conan create（opencascade 评审实撞），
        # 故非 OHOS 直接跳过。
        if self.settings.os != "OHOS":
            return
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报
        # Permission denied / Operation not permitted。签名是内容哈希，链接后再改字节就失效；
        # 复制不会破坏签名。① lib/ 的 .so ② bin/ 的 ELF（matio 装了 matdump CLI，必须签）。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        # 代码签名工具定位：CI 标准位置在 /data/service/hnp/bin（hdf5/netcdf 先例），
        # 部分设备实际装在 /usr/local/bin 并已在 PATH 中。用 shutil.which 按 PATH
        # 解析，找不到再回退 CI 标准路径，两个环境都能签。
        import shutil
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy") \
            or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") \
            or "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["matio"]
        self.cpp_info.set_property("cmake_file_name", "matio")
        self.cpp_info.set_property("cmake_target_name", "matio::matio")
        self.cpp_info.set_property("pkg_config_name", "matio")
