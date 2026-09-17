#!/usr/bin/env python3
"""Conan recipe for openrct2 0.5.3 — OpenRCT2 游戏引擎（RollerCoaster Tycoon 2 开源重制版，C++）。

Upstream: https://github.com/OpenRCT2/OpenRCT2 (tag v0.5.3)
Build:   CMake（cmake_minimum 3.24），C++20。
         headless 服务器形态（DISABLE_GUI=ON）：产物 = bin/openrct2-cli
         （含 host 联机服务器/simulate/sprite/park 转换等全部命令行功能）+
         share/openrct2/ 数据（language/shaders/scenario_patches）。
         GUI 不建的依据：①仓内 sdl2/2.30.10 OHOS 定制版视频后端仅
         DUMMY/OFFSCREEN（无 X11/Wayland），GUI 运行时无真实渲染路径；
         ②音频层依赖冲突 flac→libogg/1.3.5 vs libvorbis→libogg/1.3.6
         （均在 UI 层），conan 图无法共解。详见 notes.md。
Deps:    icu4c/libzip/zstd/libcurl/freetype/fontconfig/libpng/openssl/
         zlib/nlohmann-json — 全部制品仓实测可用（conan install 验证过二进制）。
         quickjs-ng vendored（src/thirdparty/quickjs-ng）。
         gtest/1.17.0.1 test_requires（build 期测试框架，
         cmake_file_name=GTest 与上游 tests/CMakeLists find_package(GTest)
         直接匹配，不进包依赖图）。
Patches: 0001 conan 依赖集成（PKG_CHECK_MODULES → CMakeDeps find_package）；
         0002 headless install 守卫（g2.dat 等 GUI 资源）；0003-0019
         OHOS clang15/libc++15 C++20 兼容（stop_token 多余 include 删除、
         typename 依赖名、source_location polyfill、make_unique_for_overwrite、
         std::ranges→std:: 算法、聚合 CTAD 推导指引、<sstream> 补 include）；
         0020 OHOS 下 gtest 1.17 头文件 -Wsign-compare 降级（-Werror 保留）。
Type:    application（commands.json 软件级声明）。

上游测试: WITH_TESTS=ON 真实执行上游 tests/ 全量测试系（test/tests/，
         OpenRCT2Tests 单目标 + gtest_discover_tests）：
         - 源码静态 TEST 数 222；运行时 TEST_P 参数化展开后 274 用例
           （ReplayTests 19 个 parkrep、StringTest TrimData 26 组等）
         - 测试资产：replays/objects/openmusic 三个 zip（URL+sha256 均来自
           源码树 assets.json，与上游 CI 一致），build() 阶段下载校验组装
         - ctest 逐用例真实执行（本机 OHOS arm64 原生环境）
         - test_package 另行 headless 冒烟（openrct2-cli --version）
"""
import os

from conan import ConanFile

from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    get,
    apply_conandata_patches,
    download,
    unzip,
    export_conandata_patches,
    mkdir,
)


class Openrct2Conan(ConanFile):
    name = "openrct2"
    version = "0.5.3"
    description = "Open source re-implementation of RollerCoaster Tycoon 2 (C++)"
    license = "GPL-3.0"
    homepage = "https://openrct2.io/"
    url = "https://github.com/OpenRCT2/OpenRCT2"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    test_requires = "gtest/1.17.0.1"

    requires = (
        "icu4c/78",
        "libzip/1.11.4",
        "zstd/1.5.7.1",
        "libcurl/8.5.0",
        "freetype/2.14.3",
        "fontconfig/2.18.1.1",
        "libpng/1.6.58",
        "openssl/3.5.6.1.1",
        "zlib/1.3.1.1",
        "nlohmann-json/3.11.2",
    )

    # 上游 tests/CMakeLists.txt: find_package(GTest REQUIRED) + GTest::gtest。
    # gtest/1.17.0.1 的 cmake_file_name=GTest / cmake_target_name=GTest::gtest
    # 直接匹配。test_requires 是 conan 2 为测试框架设计的依赖语义：
    # ① 不进包运行时依赖图（pkgid/包内容不变——测试是 build 期行为）；
    # ② CMakeDeps 按完整 cpp_info 生成 config 文件（试过 tool_requires +
    #    visible=True + build_context_activated：能生成 GTestConfig.cmake 但
    #    build context 下 LIBS/INCLUDE_DIRS 均为空——链接失败，conan 2.29.1
    #    对 tool_requires 包的 components cpp_info 不完整渲染）。

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="OpenRCT2-0.5.3.tar.gz")
        # ReplayTests TEST_P 数据：上游 CMake 在 install 期下载 replays.zip 到
        # build testdata/replays（DOWNLOAD_REPLAYS=ON + DESTDIR 语义），离线
        # conan 流程改为配方 source 期下载校验并放入源码树 testdata——
        # tests/CMakeLists 的 file(CREATE_LINK testdata) 会将其带入 build 目录。
        self._fetch_testdata_zip("replays")
        unzip(self, "replays.zip", os.path.join(self.source_folder, "test", "tests", "testdata"))
        # zip 内是散装 *.parkrep（无顶层目录），挪进 replays/ 子目录
        import shutil
        td = os.path.join(self.source_folder, "test", "tests", "testdata")
        mkdir(self, os.path.join(td, "replays"))
        for f in os.listdir(td):
            if f.endswith(".parkrep"):
                shutil.move(os.path.join(td, f), os.path.join(td, "replays", f))

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # OHOS 本机即目标（非交叉）：CMake 端 CMAKE_CROSSCOMPILING=False，
        # g2.dat 等图形资源由 openrct2-cli 本机生成后 install。
        # 下载数据资源关闭——离线打包，assets 由用户首次运行时获取。
        # 注意：测试资产（replays/objects/openmusic）由配方在 source/build
        # 阶段自行下载校验（见 _fetch_testdata_zip），不走 CMake install 期
        # 下载（DOWNLOAD_REPLAYS 依赖 DESTDIR 环境语义，conan 下不可控）。
        tc.variables["DOWNLOAD_TITLE_SEQUENCES"] = False
        tc.variables["DOWNLOAD_OBJECTS"] = False
        tc.variables["DOWNLOAD_OPENSFX"] = False
        tc.variables["DOWNLOAD_OPENMUSIC"] = False
        tc.variables["DOWNLOAD_REPLAYS"] = False
        # DiscordRPC 不可用——关闭
        tc.variables["DISABLE_DISCORD_RPC"] = True
        # headless 形态：只建 openrct2-cli（headless server/CLI）+ libopenrct2
        tc.variables["DISABLE_GUI"] = True
        # 上游测试系全量开启（rule4：真实执行）
        tc.variables["WITH_TESTS"] = True
        tc.variables["CMAKE_INSTALL_DOCDIR"] = "doc"
        tc.variables["CMAKE_INSTALL_DATADIR"] = "share"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # OHOS 坑：禁 mkfifo jobserver——直接 make -j1（catdoc/ccze/openvdb 同款）
        self.run("make -j1", env="conanbuild")
        # 上游测试真实执行（本机 OHOS arm64 原生可跑）
        self._run_upstream_tests()

    def _fetch_testdata_zip(self, key):
        meta = self.conan_data["testdata"][key]
        download(self, meta["url"], f"{key}.zip", sha256=meta["sha256"])

    def _run_upstream_tests(self):
        """真实执行上游测试系（ctest 逐用例）。

        环境组装（实测验证的目录契约）：
        - $BUILD/testdata — tests/CMakeLists configure 期 file(CREATE_LINK)
          自动创建的符号链接 → 源码 test/tests/testdata（replays 已在其中）
        - $BUILD/data — 测试二进制数据目录（Platform.Linux GetInstallPath
          搜索 {exeDir,cwd}/data）：language ← 源码 data/，object ←
          objects.zip + openmusic.zip(object/official/music 的
          openrct2.music.* parkobj，EverythingPark.park 引用)
        - LD_LIBRARY_PATH：conanbuild（工具链 llvm lib 的 libc++_shared.so）
          + conanrun（依赖包 libdirs）组合（#9606 同族坑）
        """
        build_dir = self.build_folder

        # 1) 测试数据目录
        testdata_link = os.path.join(build_dir, "testdata")
        if not os.path.exists(testdata_link):
            # configure 已创建；防御性兜底（HMDFS 符号链接可用）
            src_testdata = os.path.join(self.source_folder, "test", "tests", "testdata")
            self.run(f'ln -sfn "{src_testdata}" "{testdata_link}"')

        # 2) data 目录（language + objects）
        data_root = os.path.join(build_dir, "openrct2-test-data")
        mkdir(self, data_root)
        # language：直接符号链接源码 data/language（编译期必需数据，源码树内）
        src_data = os.path.join(self.source_folder, "data")
        if not os.path.exists(os.path.join(data_root, "language")):
            self.run(f'ln -sfn "{src_data}/language" "{data_root}/language"')
        # objects：objects.zip 全量 + openmusic.zip 的 object/ 部分
        obj_dir = os.path.join(data_root, "object")
        if not os.path.exists(obj_dir):
            self._fetch_testdata_zip("objects")
            unzip(self, "objects.zip", obj_dir)
            self._fetch_testdata_zip("openmusic")
            unzip(self, "openmusic.zip", os.path.join(build_dir, "openmusic-extract"))
            # openmusic zip 结构：object/official/music/*.parkobj
            import shutil
            shutil.copytree(
                os.path.join(build_dir, "openmusic-extract", "object"),
                obj_dir, dirs_exist_ok=True)
        data_link = os.path.join(build_dir, "data")
        self.run(f'ln -sfn "{data_root}" "{data_link}"')

        # 3) ctest 真实执行（逐用例独立进程；--output-on-failure 留失败原文）。
        # env 组合 conanbuild+conanrun：前者含工具链 llvm lib（libc++_shared.so），
        # 后者含依赖包 libdirs（#9606 同族坑，单用任一都会缺库）。
        self.run(
            f'ctest --test-dir "{build_dir}" --output-on-failure',
            env=["conanbuild", "conanrun"],
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["openrct2"]
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
