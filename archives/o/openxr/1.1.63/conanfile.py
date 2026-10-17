#!/usr/bin/env python3
"""Conan recipe for openxr 1.1.63 (OpenXR-SDK-Source) — CMake (C++17).

构建 OpenXR **loader**（libopenxr_loader.so）。loader 是应用与 XR 运行时之间的
那一层：应用链 loader，loader 通过 dlopen 去加载运行时。

与仓库里已有的 openxr/1.1.60 归档（legacy，无 conanfile.py）相比，本配方有三点
必须显式处理，否则会以「静默走错分支」或「configure 直接炸」收场：

1. **CMAKE_SYSTEM_NAME 是 HarmonyOS，不是 Linux。**
   Conan OHOS 工具链把 os=OHOS 映射成 CMAKE_SYSTEM_NAME=HarmonyOS
   （见 ci/conan/profiles/ohos-aarch64 顶部注释）。上游 src/CMakeLists.txt 用
   ``elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")`` 来定义 XR_OS_LINUX，HarmonyOS
   匹配不到 → XR_OS_LINUX 不定义。后果不是"少了点优化"，而是 loader 的
   dlopen/dlsym 封装（loader_platform.hpp）与 PlatformUtilsGetEnv
   （common/platform_utils.hpp）整段不编译，根本过不了编译；即使过了，
   manifest_file.cpp 的运行时发现也会从 XDG 分支掉到
   PlatformGetGlobalRuntimeFileName 分支。补丁 0002 把 HarmonyOS 并入 Linux
   分支。

2. **presentation backend 不需要任何补丁 —— 因为 presentation.cmake 压根不会被
   include。** 上游用 ``if(CMAKE_SYSTEM_NAME STREQUAL "Linux") include(presentation)``
   决定要不要做图形后端探测；在 HarmonyOS 下这个分支不可达，所以 1.1.60 归档里
   的 0003-src-cmake-presentation.cmake.patch（给 BACKENDS 列表加 "none"）在
   Conan 体系下是死代码。1.1.60 需要它，是因为那一版用自备 toolchain.cmake 把
   CMAKE_SYSTEM_NAME 设成了 Linux。本配方不移植该补丁，也不传
   PRESENTATION_BACKEND（传了只会收获一条 unused-variable 警告）。

3. **上游确实有可自动执行的回归套件，且本配方实跑。**
   `src/tests/loader_test`（vendored Catch2，6 个 TEST_CASE / 10 个 SECTION）
   是上游唯一的 ctest 目标（全树 `add_test` 只出现一次）。它要
   BUILD_LOADER + BUILD_API_LAYERS，并且 Catch2 目标只在
   BUILD_TESTS/BUILD_CONFORMANCE_TESTS 为真时才 add_subdirectory ——
   所以 BUILD_TESTS 必须开。BUILD_SDK_TESTS 必须关（hello_xr 需要图形后端）。

测试二进制与它 dlopen 出来的 api layer / test_runtime 都是刚链出来的 .so，
运行期要把依赖与工具链运行库目录塞进 LD_LIBRARY_PATH（同 ezstream/1.0.2、
aaphoto/0.45、xauth/1.1.4 的先例）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

# 上游 src/tests/loader_test/loader_test.cpp 里的 TEST_CASE 个数（1.1.63）。
# 用来把"上游回归套件真的全绿"钉成断言，而不是只看 ctest 退出码。
MIN_UPSTREAM_TESTS = 6

# OHOS SDK 的 lld 与 libc++_shared 所在目录（llvm/lib 下一层是 libc++ 的 .so）。
# profile 的 [buildenv] 已经把它放进 LD_LIBRARY_PATH，但那是给 conan 自己的
# shell 用的；测试二进制由本配方自己 exec，必须显式带上。
OHOS_LLVM_LIB = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"


class OpenXrConan(ConanFile):
    name = "openxr"
    version = "1.1.63"
    description = "OpenXR SDK loader (libopenxr_loader) for HarmonyOS PC"
    license = "Apache-2.0"
    homepage = "https://www.khronos.org/openxr/"
    url = "https://github.com/KhronosGroup/OpenXR-SDK-Source"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "this recipe is validated for OHOS only; upstream handles the "
                "other platforms"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # loader 本体：DYNAMIC_LOADER=ON 出 .so（应用侧要的是能 dlopen 运行时
        # 的共享 loader，A裸静态库在 XR 场景下没有意义）
        tc.variables["DYNAMIC_LOADER"] = "ON"
        tc.variables["BUILD_LOADER"] = "ON"
        # BUILD_TESTS 同时控制两件事：src/tests/ 子目录，以及 vendored Catch2
        # 的 add_subdirectory（src/CMakeLists.txt:626 是
        # `if(BUILD_TESTS OR BUILD_CONFORMANCE_TESTS)`）。关掉它 loader_test
        # 会因为找不到 Catch2::Catch2 而 configure 失败。
        tc.variables["BUILD_TESTS"] = "ON"
        # SDK 示例（hello_xr / list / list_json / c_compile_test）需要
        # XR_USE_PLATFORM_*，也就是需要 presentation backend；HarmonyOS 下
        # presentation.cmake 不参与，这些目标必然配置失败。loader_test 不受
        # BUILD_SDK_TESTS 管辖，所以关掉它不会丢上游测试。
        tc.variables["BUILD_SDK_TESTS"] = "OFF"
        # conformance 需要 xr_use_graphics_api_* + 真实运行时，且会把
        # BUILD_CONFORMANCE_CLI 拉起来（还依赖 python 脚本链）。关。
        tc.variables["BUILD_CONFORMANCE_TESTS"] = "OFF"
        # loader_test 的 add_dependencies 指向 XrApiLayer_test / api_dump /
        # core_validation；这三个来自 BUILD_API_LAYERS。
        tc.variables["BUILD_API_LAYERS"] = "ON"
        # 用随包 vendored jsoncpp（制品仓没有 jsoncpp 包，JSONCPP_FOUND 为假时
        # 上游的 cmake_dependent_option 本来也会落到 OFF，这里写出来是为了
        # 语义明确）
        tc.variables["BUILD_WITH_SYSTEM_JSONCPP"] = "OFF"
        tc.variables["BUILD_ALL_EXTENSIONS"] = "OFF"

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self._run_upstream_tests()

    # ------------------------------------------------------------------ 测试

    def _runtime_libdirs(self):
        """整张依赖图的 lib 目录 + 构建树里所有含 .so 的目录 + 工具链运行库目录。

        openxr 自己没有 conan 依赖，但 loader_test 的运行方式逼着我们把构建树
        也拼进来：上游生成的 test_runtime 清单里 library_path 用的是
        `$<TARGET_FILE_NAME:test_runtime>`，也就是一个**裸文件名**
        libtest_runtime.so（manifest_file.cpp 对不含 '/' 的 library_path 走
        "全局库搜索路径"）。loader_test 又靠这份清单来判断
        `g_has_installed_runtime`，判断不出来就把 6 个 TEST_CASE 里的 4 个
        SKIP 掉 —— ctest 依然退出 0，看着像"全绿"。

        libc++_shared.so 同理：dlopen 出来的 .so 的 DT_NEEDED 里有它，OHOS
        加载器没有兜底搜索路径。
        """
        dirs = []
        for dependency in self.dependencies.values():
            if dependency.package_folder:
                libdir = os.path.join(dependency.package_folder, "lib")
                if os.path.isdir(libdir):
                    dirs.append(libdir)
        for root, _subdirs, files in os.walk(self.build_folder):
            if any(name.endswith(".so") for name in files):
                dirs.append(root)
        if os.path.isdir(OHOS_LLVM_LIB):
            dirs.append(OHOS_LLVM_LIB)
        return [d for i, d in enumerate(dirs) if d not in dirs[:i]]

    def _run_upstream_tests(self):
        """实跑上游 ctest（唯一目标 loader_test，Catch2）。

        ctest 只回传一个退出码，失败时把 Testing/Temporary/LastTest.log 主动
        倒到构建控制台 —— CI 只保留约 4000 字符的日志尾部，不主动打印就永远
        看不到断言失败的原文（xauth 1.1.4 的教训）。
        """
        prior = os.environ.get("LD_LIBRARY_PATH")
        libdirs = self._runtime_libdirs()
        if libdirs:
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                libdirs + ([prior] if prior else [])
            )
        try:
            # 不用 conan.tools.cmake.CTest：CI worker 的 conan 发行版
            # (conan/tools/cmake/__init__.py) 并未导出该类，`from conan.tools.cmake
            # import CTest` 在 conanfile **加载期**就 ImportError，整个包连
            # build() 都进不去，CI 只能报「类别: 未知 / conanfile.py 加载失败」
            # （CI #53943 实证，openxr 11492 唯一的失败原因）。直接调 ctest，
            # --output-on-failure 与 CTest.test(output_on_failure=True) 语义一致，
            # 失败原文同样落到控制台。
            try:
                self.run("ctest --output-on-failure",
                         cwd=self.build_folder, env="conanbuild")
            except ConanException:
                self._dump_ctest_logs()
                raise
            self._assert_testsuite_bounds()
        finally:
            if prior is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = prior

    def _dump_ctest_logs(self):
        """按「诊断价值倒序」打印：最有价值的放最后，保证落在日志保留区内。"""
        log = os.path.join(self.build_folder, "Testing", "Temporary", "LastTest.log")
        if not os.path.isfile(log):
            return
        with open(log, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        self.output.error("----- LastTest.log (tail) -----")
        self.output.error(text[-3000:])

    def _assert_testsuite_bounds(self):
        """ctest 退出码为 0 只说明"没有失败"；它不区分"全跑过了"和"大半被 SKIP"。

        loader_test 的 6 个 TEST_CASE 里有 4 个开头就是
        `if (!g_has_installed_runtime) SKIP(...)`。g_has_installed_runtime 靠
        上游自己生成的 test_runtime 清单来置位，清单找不到就静默 SKIP：
        ctest 照样退出 0，日志里只有一行 "N skipped"，看起来像通过。这里把
        Catch2 的汇总行读回来，把"6 个 TEST_CASE 全部真的执行"钉死。
        """
        log = os.path.join(self.build_folder, "Testing", "Temporary", "LastTest.log")
        if not os.path.isfile(log):
            raise ConanException(
                "ctest reported success but {} is missing; cannot confirm the "
                "upstream suite actually ran".format(log)
            )
        with open(log, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        total, skipped = _parse_catch2_summary(text)
        if total is None:
            self.output.error("----- LastTest.log (tail) -----")
            self.output.error(text[-3000:])
            raise ConanException(
                "could not find a Catch2 summary line in LastTest.log; the "
                "upstream suite did not run"
            )
        if skipped:
            self.output.error("----- LastTest.log (tail) -----")
            self.output.error(text[-3000:])
            raise ConanException(
                "upstream loader_test SKIPPED {} of {} test case(s); the local "
                "test runtime was not visible to the loader, so those cases "
                "prove nothing".format(skipped, total)
            )
        if total < MIN_UPSTREAM_TESTS:
            self.output.error("----- LastTest.log (tail) -----")
            self.output.error(text[-3000:])
            raise ConanException(
                "upstream loader_test executed only {} test case(s), expected "
                "at least {}".format(total, MIN_UPSTREAM_TESTS)
            )
        self.output.info(
            "upstream loader_test: {} test case(s) executed, 0 skipped".format(total)
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["openxr_loader"]
        self.cpp_info.set_property("pkg_config_name", "openxr")
        # loader 用 dlopen 找运行时；Threads 在 OHOS bionic/musl 上并进 libc，
        # 只需 pkg-config 的 Libs 与 -pthread 一致
        self.cpp_info.system_libs = ["dl", "m"]
        self.cpp_info.includedirs = ["include"]


def _parse_catch2_summary(text):
    """解析 Catch2 v3 的汇总行，返回 (test_case 总数, 其中 skipped 数)。

    两种格式都要认：
      * 全绿：``All tests passed (N assertions in M test cases)``
      * 有 skip/失败：``test cases: M | P passed | F failed | S skipped``
        （列数与顺序随 Catch2 版本略有出入，所以逐列按关键字抓）
    抓不到返回 (None, 0)。
    """
    import re

    table = re.search(
        r"test cases:\s*(?P<total>\d+)(?P<rest>[^\n]*)", text
    )
    if table:
        total = int(table.group("total"))
        skipped = 0
        match = re.search(r"(\d+)\s+skipped", table.group("rest"))
        if match:
            skipped = int(match.group(1))
        return total, skipped

    green = re.search(r"in\s+(\d+)\s+test cases", text)
    if green:
        return int(green.group(1)), 0
    return None, 0
