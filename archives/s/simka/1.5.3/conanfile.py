#!/usr/bin/env python3
"""Conan recipe — simka 1.5.3 (CMake, application).

simka（GATB / Genscale, INRIA）是基于 minimizer 分区的 k-mer 计数与比较工具。

形态一手核（archives/s/simka/1.5.3/notes.md 有完整证据）：
  上游顶层 CMakeLists.txt **没有 add_library、没有 install(HEADER)**，只有 5 个
  add_executable（simka / simkaCount / simkaCountProcess / simkaMerge / simkaMinCore），
  产物全部落在 bin/ ⇒ 这是命令行工具，不是库 ⇒ package_type="application"，
  按 R38/PF8 必须带软件级 commands.json，且不需要 cpp_info.libs。

构建期硬依赖是 vendored 子模块 thirdparty/gatb-core（官方 tag 归档里是空目录），
conandata.yml 用双源按 .gitmodules 锁定的 commit 把它补齐。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rmdir


class SimkaConan(ConanFile):
    name = "simka"
    version = "1.5.3"
    description = ("Fast and flexible k-mer counter and comparison tool based on "
                   "minimizer-partitioning (GATB core)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/GATB/simka"
    url = "https://github.com/GATB/simka"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # gatb-core 的链接行里写死了 `z`（set(gatb-core-libraries ... z ...)），
        # 且其 5 个源文件 #include <zlib.h>（BankFasta / BagFile / IteratorFile / Leon）。
        # 不注入系统路径，按 R26/R18 走 Conan 依赖（zlib/1.3.2 已发布，见 notes W0 证据）。
        self.requires("zlib/1.3.2")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # 列表形态：第一项是 simka 本体（官方 tag 归档），第二项按 .gitmodules 锁定的
        # commit 补齐 thirdparty/gatb-core（GitHub 的 tag 归档不含 submodule 内容）。
        for item in self.conan_data["sources"]:
            get(self, **item, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # 上游顶层写的是 cmake_minimum_required(VERSION 2.6)，CMake 4.x 已移除 <3.5
        # 的兼容（本机 cmake 4.1.2 实测 configure 直接失败）。
        # 必须用 cache_variables(-D)：tc.variables 写进 conan_toolchain.cmake，
        # 而它在 cmake_minimum_required() 之后才被加载，那时策略已经判完 ⇒ 无效。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # 上游全静态：gatb-core 产出 gatbcore-static / hdf5-static 两个静态库，
        # 且 zlib 是系统同名库（sysroot 里有 libz.so）⇒ 一律不出 .so（R26）。
        tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF"

        # 让上游写死的 `z` 与 <zlib.h> 命中 Conan 的 zlib 包，而不是 sysroot 里那份
        # （R26：不注入系统路径；路径全部来自 self.dependencies，不碰 shell 变量 R33）。
        zlib = self.dependencies["zlib"]
        zinc = [os.path.join(zlib.package_folder, d) for d in zlib.cpp_info.includedirs]
        zlib_dir = [os.path.join(zlib.package_folder, d) for d in zlib.cpp_info.libdirs]
        # EXTRALIBS_INC 会进 gatb-core-includes，被 simka 顶层 include_directories() 消费
        tc.cache_variables["EXTRALIBS_INC"] = ";".join(zinc)
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = " ".join("-L" + d for d in zlib_dir)
        tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = " ".join("-L" + d for d in zlib_dir)

        # 内嵌 HDF5 子项目的 zlib filter 显式关掉：CMakeFilters.cmake 只认它自己的
        # ${TGZPATH}/*.tgz 布局，走 find_package(ZLIB) 在交叉环境下不可控；
        # zlib 符号统一由上面的 Conan zlib 提供（simka 不读压缩 HDF5，功能无损失）。
        tc.cache_variables["HDF5_ENABLE_Z_LIB_SUPPORT"] = "OFF"
        tc.cache_variables["HDF5_BUILD_TOOLS"] = "OFF"
        tc.cache_variables["HDF5_BUILD_HL_LIB"] = "OFF"
        tc.cache_variables["HDF5_BUILD_CPP_LIB"] = "OFF"
        tc.cache_variables["HDF5_BUILD_EXAMPLES"] = "OFF"
        # gatb-core 顶层用 CPPUNIT_FOUND 守卫测试目录，且 simka 已设
        # GATB_CORE_EXCLUDE_TESTS/TOOLS/EXAMPLES=1；这里不额外打开任何可选件。
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游 INSTALL(DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/bin DESTINATION .) 既没写
        # USE_SOURCE_PERMISSIONS 也没写 PERMISSIONS ⇒ CMake 给普通文件套默认权限 644，
        # 5 个可执行文件进包后全部丢掉执行位（实测 -rw-r-----，消费者跑不起来）。
        # 这是上游打包段的通用缺陷（与平台无关），在 package() 里补回 +x，
        # 不去改上游 CMakeLists（R6 优先用配方层修，不生 patch）。
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in sorted(os.listdir(bindir)):
                path = os.path.join(bindir, name)
                if os.path.isfile(path):
                    os.chmod(path, 0o755)

        # 内嵌 HDF5 子项目的安装残留不是 simka 的产物（h5cc 是 HDF5 的编译器包装脚本，
        # lib/ 下只有 libhdf5.settings 与 hdf5-*.pc，没有真库文件）⇒ 剔掉，
        # 保持"工具包只有 bin/ + 上游声明的数据/脚本"这一发行布局。
        h5cc = os.path.join(bindir, "h5cc")
        if os.path.isfile(h5cc):
            os.remove(h5cc)
        rmdir(self, os.path.join(self.package_folder, "lib"))

        # 安装布局沿用上游 INSTALL 指令：bin/（5 个可执行文件）+ example/（示例数据集）
        # + simkaMin/、scripts/*.py|r（草图流水线）+ README.md、LICENSE，按原样保留。

    def package_info(self):
        # 纯工具包：只声明 bindirs，不声明 libs（产物里没有可供下游链接的库）。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
