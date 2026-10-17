#!/usr/bin/env python3
"""Conan recipe — liblsl 1.18.0.b2（Lab Streaming Layer，CMake + C++17）。

liblsl 提供 C/C++ API，用于跨设备的时间同步数据流传输（LSL 协议）。
上游构建系统为 CMake，无外部二进制依赖：

  * ``lslboost``  —— 上游随源码包内嵌的 Boost 子集（header-only，109 个文件）
  * ``pugixml``   —— 上游用 ``FetchContent(GIT_REPOSITORY ... GIT_TAG v1.15)`` 拉取
  * ``Catch2``    —— 仅上游单元测试需要，上游用 ``FetchContent(... GIT_TAG v3.4.0)`` 拉取

后两者是 **configure 期的 git clone**，在 OHOS worker 上不可靠（configure 期不保证
有 git / 可访问 github.com）。本配方在 ``source()`` 里用 conan 的 ``get()`` 下载同一
版本的 tarball，再经 ``FETCHCONTENT_SOURCE_DIR_<NAME>`` 交给 FetchContent（见
``generate()``）——版本与上游 CMakeLists.txt 里 pin 的 GIT_TAG 严格一致，且下载走
conandata.yml 的 URL（CI 的镜像回退/pre-下载机制能覆盖到）。

OHOS 适配要点（**无源码补丁**，全部在 generate() 里用 CMake 变量解决）：

1. **SONAME / RUNPATH 全空**。conan 的 CMakeToolchain 把 ``os=OHOS`` 映射成
   ``CMAKE_SYSTEM_NAME=HarmonyOS``，而 CMake 4.1.2 **没有** ``Platform/HarmonyOS.cmake``
   （只有 ``Platform/OHOS.cmake``，它不被这个 system name 命中）→ 平台模块回落成
   generic，于是 ``CMAKE_SHARED_LIBRARY_SONAME_*_FLAG`` / ``*_RUNTIME_*_FLAG`` /
   ``CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN`` 全部为空：
     - 产物无 SONAME → 消费者链接时 DT_NEEDED 退化成路径；
     - 完全无法写入 RUNPATH → ``bin/lslver`` 在裸环境找不到 ``../lib/liblsl.so.2``。
   修法：``CMAKE_USER_MAKE_RULES_OVERRIDE_{C,CXX}`` 注入一份补齐这些变量的小规则文件
   （先例 ``archives/c/curl/8.15.0.1``）。自证：``readelf -d`` 显示
   ``SONAME=liblsl.so.2``、``RUNPATH=$ORIGIN;$ORIGIN/../lib``。

2. **``cmake --install`` 改写 RUNPATH 会破坏 OHOS ELF 代码签名**（``.note.ohos.ident``），
   装出来的 ``.so``/可执行文件 dlopen/exec 报 ``Operation not permitted``（EACCES）。
   修法：``CMAKE_BUILD_WITH_INSTALL_RPATH=ON``，让构建产物直接带上最终 RUNPATH，
   install 阶段与构建阶段 RPATH 相同 → 不再有 RPATH_CHANGE 改写。
   自证：安装前后对包内每个 ``.so``/可执行文件做 sha256 对比（必须逐字节一致）。

3. **版本号**：源码来自 GitHub tag tarball，不含 ``.git``，
   ``cmake/ProjectVersion.cmake`` 会退化成内置 fallback（1.17.7）——与包版本不符。
   上游自带强制覆盖入口 ``LSL_VERSION_OVERRIDE``，用它把 ``PROJECT_VERSION``/
   ``LSL_VERSION_FULL`` 钉到 ``1.18.0.b2``；同时显式给出 ``lslgitrevision``/
   ``lslgitbranch``，让 ``lsl_library_info()`` 的内容字符串可读（否则是 ``git:/branch:/``）。

构建期自限并行度（``tools.build:jobs``，默认 2）：设备 ``os.cpu_count()``=20，而
容器 affinity 与之不等（本批实测在 8~20 之间波动），且 ``conan create`` 没有 jobs
旋钮，不自限会真开 20 路。
"""

import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)


class LiblslConan(ConanFile):
    name = "liblsl"
    version = "1.18.0.b2"
    description = ("Lab Streaming Layer (LSL) C/C++ library — "
                   "networked, time-synchronized data streaming")
    license = "MIT"
    homepage = "https://github.com/sccn/liblsl"
    url = "https://github.com/sccn/liblsl"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tests": [True, False],
        "with_benchmarks": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_tests": False,
        "with_benchmarks": False,
    }

    def export_sources(self):
        # 本版本无补丁，但保留导出落点：后续在 conandata.yml 的 patches 表里
        # 追加条目即可生效（G1 也要求该落点存在）。
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_tests:
            # benchmark 用例编译在上游测试可执行文件里，没有测试就没有 benchmark
            self.options.rm_safe("with_benchmarks")

    def validate(self):
        # 上游 CMakeLists.txt 要求 cmake_minimum_required(VERSION 3.23)（设备为 4.1.2），
        # 且源码是 C++17（profile 的 compiler.cppstd=17 与上游 CMAKE_CXX_STANDARD 17 一致）。
        check_min_cppstd(self, 17)

    def layout(self):
        cmake_layout(self, src_folder=".")

    # ── 源码 + 构建期依赖 ───────────────────────────────────────────────

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游 FetchContent 的两个 git 依赖，改为同版本 tarball 下载到源码树内，
        # 由 generate() 通过 FETCHCONTENT_SOURCE_DIR_<NAME> 指过去。
        # 始终下载（不随 option 变化）：conan 的 source() 按 recipe revision 缓存，
        # 若按 option 决定下载内容，"先无测试构建、后有测试构建"会命中缺文件的缓存。
        for name, key in (("pugixml", "pugixml"), ("Catch2", "catch2")):
            get(self, **self.conan_data[key], strip_root=True,
                destination=os.path.join(self.source_folder, "_vendor", name))

    # ── 生成工具链 ─────────────────────────────────────────────────────

    def _jobs(self):
        # 设备 os.cpu_count()=20 而 affinity=8；conan create 无 jobs 旋钮，
        # 未自限会真开 20 路（共享设备上互相拖慢并放大内存峰值）。
        jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)
        return jobs or 2

    def generate(self):
        tc = CMakeToolchain(self)

        # ── 版本号（见模块 docstring 第 3 点）──
        # 必须是 cache_variables：上游 CMakeLists.txt 在 **project() 之前** 就调用
        # lsl_version_from_git() 定版本，而 toolchain 文件是在 project() 里才被读的
        # —— 只写 tc.variables 会静默退化成内置 fallback（实测产出
        # liblsl.so.1.17.7）。cache_variables 经 CMakePresets/命令行 -D 传入，
        # 在 project() 之前就可见。
        tc.cache_variables["LSL_VERSION_OVERRIDE"] = str(self.version)
        tc.cache_variables["lslgitrevision"] = "v{}".format(self.version)
        tc.cache_variables["lslgitbranch"] = "conan"

        # ── 库类型 / 安装布局 ──
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["LSL_BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["LSL_INSTALL"] = "ON"
        tc.variables["LSL_UNIXFOLDERS"] = "ON"
        # 上游默认会 build 一个 lslver 版本查询工具（R38 的 commands.json 对应物）
        tc.variables["LSL_TOOLS"] = "OFF"

        # ── 上游单元测试（可选，默认关；CI 只建库 + test_package）──
        tc.variables["LSL_UNITTESTS"] = "ON" if self.options.with_tests else "OFF"
        # with_tests=False 时 configure() 已移除 with_benchmarks，故用 get_safe
        tc.variables["LSL_BENCHMARKS"] = (
            "ON" if self.options.get_safe("with_benchmarks", False) else "OFF")
        # 不依赖系统 Catch2（worker 上没有），走 FetchContent 的本地源目录
        tc.variables["LSL_TESTS_PREFER_SYSTEM_CATCH2"] = "OFF"

        # ── FetchContent 的本地源目录（替代 configure 期 git clone）──
        # 用 tc.variables（写进 conan_toolchain.cmake）而不是 tc.cache_variables：
        # 后者只出现在 CMakePresets/命令行里，一旦有人只给
        # -DCMAKE_TOOLCHAIN_FILE=... 手工 configure 就会静默丢失这些修正
        # （FetchContent 会退回联网 git clone）。这里让工具链文件自足。
        tc.variables["FETCHCONTENT_SOURCE_DIR_PUGIXML"] = os.path.join(
            self.source_folder, "_vendor", "pugixml")
        tc.variables["FETCHCONTENT_SOURCE_DIR_CATCH2"] = os.path.join(
            self.source_folder, "_vendor", "Catch2")
        # 决不允许 FetchContent 再去联网/克隆
        tc.variables["FETCHCONTENT_FULLY_DISCONNECTED"] = "ON"

        # ── OHOS 平台修正（见模块 docstring 第 1、2 点）──
        if self.settings.os in ("Linux", "OHOS"):
            rules = os.path.join(self.generators_folder, "ohos-cmake-rules.cmake")
            save(self, rules, "\n".join([
                "# 补齐 CMake 在 CMAKE_SYSTEM_NAME=HarmonyOS 下缺失的 ELF 链接规则：",
                "# 没有 Platform/HarmonyOS.cmake 时这些变量全为空 ->",
                "#   无 SONAME（DT_NEEDED 退化）且无法写 RUNPATH（bin/lslver 裸环境找不到 .so）。",
                "# C 与 CXX 在同一文件里都给，因为 lslver 是 C 可执行文件、库本体是 C++。",
                'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP ":")',
                'set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG "-Wl,-rpath-link,")',
                'set(CMAKE_SHARED_LIBRARY_RPATH_LINK_CXX_FLAG "-Wl,-rpath-link,")',
                'set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "$ORIGIN")',
                'set(CMAKE_EXECUTABLE_RUNTIME_C_FLAG "-Wl,-rpath,")',
                'set(CMAKE_EXECUTABLE_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
                "",
            ]))
            tc.variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
            tc.variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules
            # install 阶段不得改写 ELF（会破坏 OHOS 代码签名）：
            # 构建期就带上最终 RPATH，两侧一致 -> 无 RPATH_CHANGE。
            tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"
            # 必须显式给 RUNPATH：上游 CompilerSettings.cmake 的
            # `elseif(UNIX AND NOT ANDROID)` 在 HarmonyOS 下不成立 —— CMake 的
            # UNIX 变量由 Platform/<系统>-Initialize.cmake 设置，没有
            # Platform/HarmonyOS-Initialize.cmake 就没人 set(UNIX 1)（实测
            # CMakeCache 里根本没有 UNIX 条目），于是 CMAKE_INSTALL_RPATH 保持为空、
            # bin/lslver 找不到 ../lib/liblsl.so.2。取值与上游 Linux 分支一致。
            tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN;$ORIGIN/../lib"

        tc.generate()

    # ── 构建 / 打包 ────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        jobs = self._jobs()
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j{}".format(jobs)])
        if self.options.with_tests:
            # 真跑上游 Catch2 用例（ctest 的每个 add_test 就是一个测试可执行文件，
            # 内部再用 Catch2 展开成 N 个 TEST_CASE）。
            #
            # ① 测试目录是 <build>/testing 而不是 <build> 本身：上游只在
            #    testing/CMakeLists.txt 里 enable_testing()，CTestTestfile.cmake 因此
            #    只在 build/testing/ 下生成 —— 在 <build> 跑 ctest 会打印
            #    "No tests were found!!!" 并且 **rc=0**（实测），是一条「零用例假绿」。
            #    这里额外用 --no-tests=error 把它变成硬失败。
            # ② 必须串行（不传 -j）：liblsl 的测试共用同一段监听端口带
            #    （ports.BasePort 默认 16572），并发跑两个 liblsl 进程会互相抢占端口，
            #    而 ports.AllowRandomPorts 默认 true 会让抢不到端口的 outlet 静默改随机
            #    端口，resolve_over_tcp 用例的固定端口探测随即打空（本机实测 3/3 假失败，
            #    串行则 3/3 全绿）。
            # ③ 这里必须显式给 LD_LIBRARY_PATH：CMAKE_BUILD_WITH_INSTALL_RPATH=ON 让
            #    构建产物直接带**安装后**的 RUNPATH（$ORIGIN;$ORIGIN/../lib），而构建树里
            #    测试可执行文件在 <build>/testing/、liblsl.so.2 在 <build>/、Catch2 在
            #    <build>/_deps/catch2-build/src/ —— 构建树的目录布局与安装布局不同。
            #    （安装后的 bin/ 里 RUNPATH 是正确的，另有裸环境 smoke 单独验证。）
            build_dir = self.build_folder
            if self.conf.get("tools.build:skip_test", default=False, check_type=bool):
                self.output.info(
                    "tools.build:skip_test=True：只构建上游测试可执行文件，不执行 ctest")
            else:
                test_dir = os.path.join(build_dir, "testing")
                ld_paths = ":".join(
                    [build_dir, os.path.join(build_dir, "_deps", "catch2-build", "src")])
                self.run(
                    'LD_LIBRARY_PATH="{0}:$LD_LIBRARY_PATH" ctest --test-dir "{1}" '
                    "--output-on-failure --no-tests=error".format(ld_paths, test_dir),
                    env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["lsl"]
        # 包内确实带一个可执行文件（bin/lslver，上游 TargetOther.cmake 无条件安装），
        # 所以显式声明 bindirs：①消费者在 VirtualRunEnv 下能直接用 lslver；
        # ②与软件级 commands.json（R38）配套——不声明会被静态闸判成
        # 「纯库包不应有 commands.json」。
        self.cpp_info.bindirs = ["bin"]
        # 安装出的 CMake 包配置文件是 lib/cmake/lsl/LSLConfig.cmake（NAMESPACE LSL::），
        # 让 CMakeDeps 生成同名 target，消费者可用 find_package(LSL CONFIG) + LSL::lsl。
        self.cpp_info.set_property("cmake_file_name", "LSL")
        self.cpp_info.set_property("cmake_target_name", "LSL::lsl")
