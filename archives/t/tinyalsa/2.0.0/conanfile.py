#!/usr/bin/env python3
"""Conan recipe for tinyalsa 2.0.0（HarmonyOS OHOS 适配）.

tinyalsa 是直接对接 Linux 内核 ALSA UAPI 的小型 C 库：**零运行依赖**——只用
内核 UAPI 头 `<sound/asound.h>`（由 OHOS SDK sysroot 提供，实测
`sysroot/usr/include/sound/asound.h`）与 `libdl`，不链接 alsa-lib。

构建入口（manifest `build.system: cmake`）：上游同时提供 make / cmake / meson
三个入口，本包选 **CMake**——
  * CMakeLists 自带完整 install 规则（头文件 + 库），不需要安装脚本；
  * 不触碰 `src/Makefile`、`utils/Makefile` 里硬编码的
    `CC = $(CROSS_COMPILE)gcc`（conan-center 对 make 入口补的
    fix-hardcoded-gcc 补丁对本入口不需要）；
  * 上游 make 入口会递归 `doxygen/`（设备无 doxygen，只打 warning），
    CMake 入口不构建文档。

两处环境适配都在**配方层**，上游源码零改动（本 PR 无 patches）：
  1. 设备与 CI worker 的 CMake 4.1 已移除 "<3.5 兼容"，上游
     `cmake_minimum_required(VERSION 3.1)` 直接报
     `Compatibility with CMake < 3.5 has been removed from a future version`
     ⇒ 配置时传 CMake 官方逃生口 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
  2. 上游 `tests/` 只接了 Bazel（`BUILD` 的 `cc_test` + `@googletest`），
     CMake / meson 都没有测试入口 ⇒ `build()` 内由配方生成一个 CMake 子工程，
     编译同一份 `tests/src/*.cc` 并经 `ctest` 运行（层 1，见
     `docs/TEST_QUALITY_SPEC.md §3`）。子工程的两个文件写在 build 目录
     （CMakeLists.txt / gtest_main.cpp），**不改上游任何文件**；
     gtest 主函数由 `gtest_main.cpp` 提供，与上游 `BUILD` 里链接的
     `@googletest//:gtest_main` 等价（conan 的 gtest 包 `cpp_info.libs`
     只声明 `gtest`，未导出 `gtest_main`）。

设备依赖判据（决定哪些上游用例可跑，结论逐字打进日志）：
  `/dev/snd` 控制节点探针可打开 ⇒ 全量用例都跑；打不开（本设备 `/dev/snd`
  目录与 `controlC*` 全部 EACCES）⇒ 只跑与设备无关的子集，其余按**环境限制
  记 SKIP（不写 PASS）**，并保留一次全量试跑作为归因证据（`ignore_errors`，
  不参与构建判据）。
"""
import errno
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, save)

# 配方生成的测试子工程：上游 tests/ 只有 Bazel 入口，这里补 CMake 入口。
_UPSTREAM_TESTS_CMAKE = """\
# 由 tinyalsa 配方 build() 写入 build 目录（不进上游源码、不进提交面）。
# 编译的是上游 tests/ 下的同一份 .cc，未改任何上游测试文件。
cmake_minimum_required(VERSION 3.15)
project(tinyalsa_upstream_tests LANGUAGES CXX)

if(NOT DEFINED TINYALSA_SRC OR NOT DEFINED TINYALSA_LIB
   OR NOT DEFINED TINYALSA_GTEST_FILTER)
    message(FATAL_ERROR
        "TINYALSA_SRC / TINYALSA_LIB / TINYALSA_GTEST_FILTER 必须由配方传入")
endif()

find_package(gtest REQUIRED CONFIG)

add_executable(tinyalsa_upstream_tests
    "${TINYALSA_SRC}/tests/src/mixer_test.cc"
    "${TINYALSA_SRC}/tests/src/pcm_in_test.cc"
    "${TINYALSA_SRC}/tests/src/pcm_loopback_test.cc"
    "${TINYALSA_SRC}/tests/src/pcm_out_test.cc"
    "${TINYALSA_SRC}/tests/src/pcm_params_test.cc"
    "${TINYALSA_SRC}/tests/src/pcm_test.cc"
    "${CMAKE_CURRENT_SOURCE_DIR}/gtest_main.cpp")

target_include_directories(tinyalsa_upstream_tests PRIVATE
    "${TINYALSA_SRC}/include"
    "${TINYALSA_SRC}/tests/include")

# 直接链 build 目录里刚构建出来的 libtinyalsa（与被测产物同源）
target_link_libraries(tinyalsa_upstream_tests PRIVATE
    "${TINYALSA_LIB}" gtest::gtest)

enable_testing()
add_test(NAME tinyalsa_upstream
         COMMAND tinyalsa_upstream_tests "--gtest_filter=${TINYALSA_GTEST_FILTER}")
set_tests_properties(tinyalsa_upstream PROPERTIES TIMEOUT 300)
"""

# 与上游 BUILD 的 @googletest//:gtest_main 等价（conan gtest 未导出 gtest_main）
_GTEST_MAIN = """\
#include <gtest/gtest.h>

int main(int argc, char **argv)
{
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
"""

# 与音频设备节点无关的用例：只依赖纯计算与“必然打不开的负向路径”。
# 其余用例都要在 SetUp/用例体里打开 /dev/snd（controlC* / pcmC*D*）。
_DEVICE_INDEPENDENT_FILTER = "MixerTest.OpenAndClose:PcmTest.FormatToBits"


class TinyalsaConan(ConanFile):
    name = "tinyalsa"
    version = "2.0.0"
    description = "A small library to interface with ALSA in the Linux kernel"
    license = "BSD-3-Clause"
    homepage = "https://github.com/tinyalsa/tinyalsa"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # 零运行依赖：只用内核 UAPI 头 + libdl，不链接 alsa-lib。
        pass

    def build_requirements(self):
        # 上游 tests/ 是 gtest 用例（C++17），只在 build() 内用，不进消费面。
        # 注意 Conan 2.x 的钩子名是 build_requirements()：**不会有**名为
        # `test_requirements()` 的方法被调用；`self.test_requires(...)` 是
        # conan 在调用钩子前注入的 TestRequirements 调用器（traits：
        # headers/libs=True、visible=False、test=True），不传染下游。
        self.test_requires("gtest/1.17.0")

    def layout(self):
        # build_folder 不能用默认的 "build"：上游带 Bazel 的 `BUILD` 文件，而本设备
        # 文件系统大小写不敏感（notes/device-facts.md §一.3），`build/` 会撞上已有
        # 的 `BUILD` 文件，makedirs 报 NotADirectoryError（实测 create 首轮即中）。
        cmake_layout(self, src_folder=".", build_folder="cmake-build")

    def export_sources(self):
        # 本包 conandata 的 patches 为空（上游源码零改动），此调用是 no-op；
        # 保留它是为了与全仓配方形态一致（conan-verify G1 的完整性检查认这两个调用）。
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # os=OHOS 下 conan 把 CMAKE_SYSTEM_NAME 映射成 CMake 不认识的 "HarmonyOS"
        # （tools/cmake/toolchain/blocks.py GenericSystemBlock 的 OHOS→HarmonyOS），
        # 设备 cmake 4.1.2 没有 Platform/HarmonyOS.cmake ⇒ 平台信息缺失：共享库
        # 不带 DT_SONAME、也只产出 libtinyalsa.so 而没有 .so.2/.so.2.0.0
        # （W3 L5a 实测 [fail] soname_gate_failed；实测 -DCMAKE_SYSTEM_NAME=Linux 后
        # 立即产出 libtinyalsa.so.2.0.0 + DT_SONAME=libtinyalsa.so.2）。
        # 走 cache_variables（-D 命令行），命中 GenericSystemBlock 的
        # `if(NOT DEFINED CMAKE_SYSTEM_NAME)` 守卫——与全仓 370 个配方同一解法。
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # 上游默认 BUILD_SHARED_LIBS=ON；本包按 shared 选项交付。
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # utils/examples 是面向音频设备的人工演示工具：本包按纯库交付
        # （与 conan-center 默认 with_utils=False 一致；装 bin/ 还会触发
        # R38/L0k 的 commands.json 与 PF9 包级路径要求）。
        tc.variables["TINYALSA_BUILD_UTILS"] = "OFF"
        tc.variables["TINYALSA_BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        # conandata 的 patches 为空 ⇒ no-op（与 export_sources 同理，形态一致性）
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMake 4.x 移除 <3.5 兼容，上游第 1 行 cmake_minimum_required(VERSION 3.1)
        # 直接报错。该判断发生在 CMakeLists 解析阶段、**早于** toolchain 文件加载，
        # 所以必须走 -D 命令行（tc.variables/cache_variables 写在 toolchain 里不生效，
        # 实测首轮即因此失败）——CMake 官方给的逃生口就是 -DCMAKE_POLICY_VERSION_MINIMUM=3.5。
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()
        self._run_upstream_tests()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["tinyalsa"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl"]

    # ------------------------------------------------------------------
    # 层 1：上游 tests/ 的 gtest 套件（docs/TEST_QUALITY_SPEC.md §3）
    # ------------------------------------------------------------------

    @staticmethod
    def _probe_snd_device():
        """探测 ALSA 设备节点可访问性，返回 (是否可用, 逐项读数)。

        读数原样进日志，是“设备依赖用例为什么不能跑”的一手证据。
        """
        nodes = ("/dev/snd", "/dev/snd/controlC0", "/dev/snd/controlC1",
                 "/dev/snd/controlC2")
        notes = []
        for node in nodes:
            try:
                fd = os.open(node, os.O_RDONLY)
            except OSError as exc:
                notes.append("%s: errno=%s(%s) %s"
                             % (node, exc.errno,
                                errno.errorcode.get(exc.errno, "?"), exc.strerror))
            else:
                os.close(fd)
                return True, "%s: 可打开" % node
        return False, " | ".join(notes)

    def _built_library(self):
        for cand in ("libtinyalsa.so", "libtinyalsa.a"):
            path = os.path.join(self.build_folder, cand)
            if os.path.isfile(path):
                return path
        raise ConanException(
            "build 目录里找不到 libtinyalsa.so/.a，上游构建产物异常")

    @staticmethod
    def _slug(text):
        keep = []
        for ch in text:
            keep.append(ch if (ch.isalnum() or ch in "-_") else "-")
        return "".join(keep).strip("-") or "all"

    def _list_file(self, extra_args=""):
        return os.path.join(
            self.build_folder,
            "gtest-list-%s.txt" % self._slug(extra_args or "all"))

    def _count_tests(self, binary, extra_args=""):
        """用 --gtest_list_tests 清点注册用例数（gtest 自己的口径）。"""
        list_file = self._list_file(extra_args)
        self.run('"%s" --gtest_list_tests %s > "%s"'
                 % (binary, extra_args, list_file))
        with open(list_file, "r", encoding="utf-8", errors="replace") as fh:
            # 列表形态：套件行 "Suite." 顶格，用例行缩进
            return sum(1 for line in fh if line[:1].isspace() and line.strip())

    def _run_upstream_tests(self):
        tests_root = os.path.join(self.build_folder, "upstream-tests")
        save(self, os.path.join(tests_root, "CMakeLists.txt"), _UPSTREAM_TESTS_CMAKE)
        save(self, os.path.join(tests_root, "gtest_main.cpp"), _GTEST_MAIN)

        device_ok, device_detail = self._probe_snd_device()
        gtest_filter = "*" if device_ok else _DEVICE_INDEPENDENT_FILTER
        self.output.info("[upstream-tests] /dev/snd 探针: %s" % device_detail)
        self.output.info("[upstream-tests] gtest_filter=%s" % gtest_filter)

        tests_build = os.path.join(tests_root, "build")
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        self.run('cmake -S "%s" -B "%s" -DCMAKE_TOOLCHAIN_FILE="%s"'
                 ' -DCMAKE_SYSTEM_NAME="Linux" -DCMAKE_BUILD_TYPE="%s"'
                 ' -DTINYALSA_SRC="%s" -DTINYALSA_LIB="%s"'
                 ' -DTINYALSA_GTEST_FILTER="%s"'
                 % (tests_root, tests_build, toolchain, self.settings.build_type,
                    self.source_folder, self._built_library(), gtest_filter))
        jobs = self.conf.get("tools.build:jobs", default=1)
        self.run('cmake --build "%s" --parallel %s' % (tests_build, jobs))

        binary = os.path.join(tests_build, "tinyalsa_upstream_tests")
        total = self._count_tests(binary)
        ran = self._count_tests(binary, "--gtest_filter=%s" % gtest_filter)
        skipped = total - ran
        self.output.info("[upstream-tests] 清点 total=%s ran=%s skipped=%s"
                         % (total, ran, skipped))

        if skipped:
            skip_file = self._list_file()
            suite = ""
            with open(skip_file, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    if not line[:1].isspace():
                        suite = stripped.rstrip(".")
                        continue
                    name = "%s.%s" % (suite, stripped)
                    if not self._name_matches(name, gtest_filter):
                        self.output.info("[upstream-tests] SKIP(设备依赖/环境限制，"
                                         "不计 PASS) %s" % name)

        # 构建判据：只跑可运行子集，任何失败都让 conan create 失败
        self.run('ctest --test-dir "%s" --output-on-failure' % tests_build)

        if not device_ok:
            # 诊断段：全量试跑一次，逐字留证（设备依赖用例预期全部失败），
            # ignore_errors 隔离，不参与构建判据。
            self.output.info("[upstream-tests] 诊断段：全量试跑（不参与构建判据，"
                             "设备依赖用例预期失败，用于 SKIP 归因）")
            self.run('LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "%s"'
                     % (self.build_folder, binary), ignore_errors=True)

        self.output.info("UPSTREAM_TESTS total=%s ran=%s passed=%s skipped=%s "
                         "failed_unexpected=0" % (total, ran, ran, skipped))

    @staticmethod
    def _name_matches(name, gtest_filter):
        """极简 gtest filter 判定：支持 '*' 与 ':' 分隔的精确/通配项。"""
        if gtest_filter == "*":
            return True
        for part in gtest_filter.split(":"):
            if not part:
                continue
            pattern = "".join(".*" if ch == "*" else ch for ch in part)
            if re.fullmatch(pattern, name):
                return True
        return False
