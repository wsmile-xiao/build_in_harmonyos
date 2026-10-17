#!/usr/bin/env python3
"""Conan recipe — libminc 2.5.0 (cmake)

libminc = MINC 医学影像文件格式库（MINC1 走 netcdf，MINC2 走 HDF5）。
上游 CMakeLists 用**模块模式** find_package：
  - find_package(ZLIB REQUIRED)                    → CMake 自带 FindZLIB
  - set(HDF5_NO_FIND_PACKAGE_CONFIG_FILE ON)
    find_package(HDF5 REQUIRED COMPONENTS C)       → CMake 自带 FindHDF5（显式禁 config）
  - if(LIBMINC_MINC1_SUPPORT) find_package(NETCDF REQUIRED) → 上游自带 FindNETCDF.cmake
    （find_path/find_library，只搜 /usr/include 等硬编码路径）

本仓库 CMakeToolchain 恒定写 CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON，CMakeDeps 生成的
<dep>-config.cmake 会被 config 模式抢先命中——config 只定义 hdf5::hdf5 这类扁平 target，
不定义上游要消费的 HDF5_INCLUDE_DIRS / HDF5_LIBRARY / ZLIB_LIBRARY / NETCDF_INCLUDE_DIR
变量（libmatio/netcdf 同族实测），configure 虽过但编译期才炸。

处置（clucene-core/aevol 同型）：
  1) 对 zlib/hdf5/netcdf 设 cmake_find_mode="none"——CMakeDeps 不生成 config，
     find_package 全部回落模块模式；
  2) 用 tc.variables 预设各 Find 模块的 cache 变量（ZLIB_LIBRARY/ZLIB_INCLUDE_DIR、
     NETCDF_LIBRARY/NETCDF_INCLUDE_DIR、HDF5_ROOT——FindHDF5 的全部查找段都以
     HINTS ${HDF5_ROOT} 起步，见设备 cmake-4.1 Modules/FindHDF5.cmake:666-1118）；
  3) 再注入依赖 -I/-L 全量兜底（libmatio 生成模式），链接不依赖 config 文件。
"""
from conan import ConanFile
from conan.tools.files import get
import os
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches


class LibmincConan(ConanFile):
    name = "libminc"
    version = "2.5.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def export_sources(self):
        # G1 必查：补丁经 conandata 声明并导出（零补丁也要求显式调用）。
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def requirements(self):
        # MINC2 走 HDF5；MINC1 走 netcdf；zlib 两者都要。
        # zlib/hdf5/netcdf 全部取本仓 ohpcd 已发行版本；hdf5/netcdf 的 recipe
        # 自身静态链 zlib/1.3.1.1（DT_NEEDED 无 libz，实测），故这里 zlib 不设 shared，
        # 与依赖图既有形态一致（clucene-core 同型：ZLIB_LIBRARY 指 libz.a）。
        self.requires("hdf5/1.14.6")
        self.requires("netcdf/4.9.3")
        self.requires("zlib/1.3.1.1")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # 库与其 HDF5/netcdf 依赖的动静态必须一致，否则链接期 undefined reference
        # （libmatio 同型）。
        self.options["hdf5"].shared = self.options.shared
        self.options["netcdf"].shared = self.options.shared

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        # 依赖缓存变量（模块模式语义），并阻断 config 抢跑。
        # cmake_find_mode 是 cpp_info 属性（CMakeDeps 从 dep.cpp_info 读）；
        # ConanFileInterface 顶层无 set_property（2.29 实测），须挂在 cpp_info 上。
        for dep_name in ("zlib", "hdf5", "netcdf"):
            self.dependencies[dep_name].cpp_info.set_property("cmake_find_mode", "none")

        hdf5 = self.dependencies["hdf5"]
        netcdf = self.dependencies["netcdf"]
        zlib = self.dependencies["zlib"]

        tc = CMakeToolchain(self)
        # ★ os=OHOS 时 conan 默认把 CMAKE_SYSTEM_NAME 设成 "HarmonyOS"，而 cmake 的
        # 平台文件叫 Modules/Platform/OHOS.cmake，没有 HarmonyOS.cmake。名字对不上时
        # cmake 只打一句 "System is unknown to cmake" 就继续，平台变量（含 UNIX）留空，
        # 上游 CMakeLists 的 if(UNIX) 分支（-lm/-ldl 与 soversion 规则）整体不生效。
        # 必须**带 os 守卫**（libmatio/netcdf 先例）。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
            # harmonybrew 装有 zlib-ng 的 CMake config 包（~/.harmonybrew/lib/cmake/ZLIB/）。
            # 上游 find_package(ZLIB) 在 PREFER_CONFIG=ON 下会先命中它（cache 里
            # ZLIB_DIR 指 harmonybrew，链接命令带上 zlib-ng 的绝对路径，NEEDED
            # 写成 libz.so.1 —— CI 上不受控）。cmake_find_mode=none 只能挡 CMakeDeps
            # 自己的 config，挡不住系统已装的第三方 config 包；上游要大写 ZLIB::ZLIB
            # target + ZLIB_LIBRARY 变量，只能走 FindZLIB 模块 —— 把 harmonybrew
            # 前缀排除出 find 搜索面，config 失配回落模块，cache 预设（下）随即生效。
            # （hdf5 无此面：上游 HDF5_NO_FIND_PACKAGE_CONFIG_FILE=ON；netcdf 靠
            # 上游自带 FindNETCDF 模块，harmonybrew 无其 config。）
            _brew = os.path.join(os.path.expanduser("~"), ".harmonybrew")
            if os.path.isdir(_brew):
                tc.cache_variables["CMAKE_IGNORE_PREFIX_PATH"] = _brew
        # 上游 CMakeLists 给 minc2 设了 INSTALL_RPATH=<prefix>/lib。CMake 的 install
        # RPATH 处理**必然改写安装副本的 .dynstr/RUNPATH**（SKIP_INSTALL_RPATH 也只是
        # 把字符串清零，实测仍有 143 字节被清）——hnp clang 产物自带链接器签名
        # （.codesign 段），任何 ELF 字节改写都使签名失效，musl 加载器对坏签名副本
        # 报 `Error loading shared library ... Permission denied`（build-tree 副本
        # 完好可加载、包副本/复制副本均不可，sha256 不一致；§5.3 meson --destdir
        # 同族，判据=打包副本与 build-tree 副本 sha256 对比）。
        # 处置：CMAKE_SKIP_RPATH=ON 让 build 期就不写 RPATH——install 无事可做，
        # 两副本字节全等，签名完好。代价：build 树内测试可执行解析 libminc2 靠
        # generate() 里 VirtualBuildEnv 注入的 LD_LIBRARY_PATH（见下）。
        tc.variables["CMAKE_SKIP_RPATH"] = "ON"
        # 64 位默认可能装到 lib64/，conan cpp_info.libdirs 与 test_package 找 lib/。
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # 上游选项：LIBMINC_BUILD_SHARED_LIBS 默认 OFF，必须跟随 options.shared，
        # 不能写死（opencascade 同型）。
        tc.variables["LIBMINC_BUILD_SHARED_LIBS"] = self.options.shared
        # MINC1 格式（netcdf-based）支持：依赖已在架，全功能发行（Debian 同开）。
        tc.variables["LIBMINC_MINC1_SUPPORT"] = "ON"
        # ezminc（C++ 便利封装层）本版不启用：核心格式能力是 C 库的 MINC1/MINC2，
        # ezminc 是上层 C++ 封装，为最小化首版适配面而关闭（notes.md 有记录）。
        tc.variables["LIBMINC_BUILD_EZMINC"] = "OFF"
        # NIfTI 支持：上游默认 OFF 且 ON 时走 ExternalProject 现场拉取 nifti 源码
        # （构建期外网拉取不可复现），维持关闭。
        tc.variables["LIBMINC_USE_NIFTI"] = "OFF"
        # 上游 ctest 套件（testdir/，56 个注册用例）随 conan create 真实执行。
        tc.variables["BUILD_TESTING"] = "ON"
        # ── 模块模式 find_package 的 cache 变量预设 ──
        # ⚠️ 必须 tc.cache_variables（写 set(... CACHE PATH/FILEPATH)）：find_path/
        # find_library 只认 **cache**——普通变量预设会被无视，FindZLIB 会重新查找并
        # 命中设备 harmonybrew 的 zlib-ng（实测 NEEDED 被写成 libz.so.1，指向 CI
        # 不受控路径）。HDF5_ROOT/ZLIB_ROOT 是 Find 模块里的 HINTS 读取点，普通
        # 变量即可生效，但也一并进 cache 无副作用。
        # FindZLIB：预设后 find_path/find_library 见 cache 已有值即直接命中；
        # ZLIB::ZLIB target 由模块创建。
        tc.cache_variables["ZLIB_ROOT"] = zlib.package_folder
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = os.path.join(zlib.package_folder, "include")
        tc.cache_variables["ZLIB_LIBRARY"] = os.path.join(zlib.package_folder, "lib", "libz.a")
        # FindHDF5（HDF5_NO_FIND_PACKAGE_CONFIG_FILE=ON 已由上游设）：全部查找段
        # HINTS ${HDF5_ROOT}，指向包根即可命中 include/hdf5.h 与 lib/libhdf5.so。
        tc.cache_variables["HDF5_ROOT"] = hdf5.package_folder
        # 上游 FindNETCDF.cmake：find_path/find_library 无任何 root 语义，直接预设结果变量。
        tc.cache_variables["NETCDF_INCLUDE_DIR"] = os.path.join(netcdf.package_folder, "include")
        tc.cache_variables["NETCDF_LIBRARY"] = os.path.join(netcdf.package_folder, "lib", "libnetcdf.so")
        # 【--inject-dep-includes 生成】上游 find_package 模块模式之外的 -I 兜底：
        # 上游按变量消费依赖头文件，config 模式被阻断后模块已能填充；此处仍注入
        # 全量 include，保证任何分支漏接时编译也不炸（libmatio 生成模式）。
        _incs = []
        for _ref, _d in self.dependencies.items():
            for _p in _d.cpp_info.includedirs:
                _incs.append("-I" + _p)
        _incflags = " ".join(dict.fromkeys(_incs))
        for _k in ("CMAKE_C_FLAGS", "CMAKE_CXX_FLAGS"):
            _old = tc.variables.get(_k, "")
            tc.variables[_k] = (str(_old) + " " + _incflags).strip()
        # 【--inject-dep-libdirs 生成】裸库名链接需要 -L 才能找到 conan 包内库。
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
        CMakeDeps(self).generate()
        # CMAKE_SKIP_RPATH=ON 后 build 树内可执行（ctest 套件）不带 RUNPATH，
        # 依赖库解析靠 build 环境的 LD_LIBRARY_PATH：build 输出目录 + 各依赖 libdir。
        build_env = VirtualBuildEnv(self)
        _ld = [self.build_folder] if self.build_folder else []
        for _dep in self.dependencies.values():
            _base = getattr(_dep, "package_folder", None) or ""
            for _p in _dep.cpp_info.libdirs:
                if not os.path.isabs(_p) and _base:
                    _p = os.path.join(_base, _p)
                if os.path.isdir(_p):
                    _ld.append(_p)
        build_env.environment().append_path("LD_LIBRARY_PATH", os.pathsep.join(_ld))
        build_env.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游官方 ctest 套件（testdir/CMakeLists.txt 注册的用例）──
        # 失败即 conan create 失败；注册数与结果由报告统计（test-report.md）。
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libminc")
        self.cpp_info.set_property("cmake_target_name", "minc2")
        self.cpp_info.libs = ["minc2"]
        self.cpp_info.includedirs = ["include"]
        # 上游 PUBLIC 头直接 include hdf5.h/netcdf.h（minc2.h/minc.h），下游需要依赖头目录。
        hdf5 = self.dependencies["hdf5"]
        netcdf = self.dependencies["netcdf"]
        self.cpp_info.includedirs += list(hdf5.cpp_info.includedirs)
        self.cpp_info.includedirs += list(netcdf.cpp_info.includedirs)
        self.cpp_info.libdirs = ["lib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl"]
