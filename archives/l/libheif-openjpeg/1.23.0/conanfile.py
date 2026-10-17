#!/usr/bin/env python3
"""Conan recipe for libheif-openjpeg 1.23.0 — libheif 树内 OpenJPEG(JPEG 2000) 编解码后端插件模块。

交付面（自包含：插件模块无法脱离宿主运行）：

  * ``lib/libheif/libheif-j2kdec.so`` —— JPEG 2000 **解码**插件模块
    （上游 CMake 目标 ``heif-j2kdec``，源文件树内 ``libheif/plugins/decoder_openjpeg.cc``）
  * ``lib/libheif/libheif-j2kenc.so`` —— JPEG 2000 **编码**插件模块
    （上游 CMake 目标 ``heif-j2kenc``，源文件树内 ``libheif/plugins/encoder_openjpeg.cc``）
  * 宿主 ``lib/libheif.so``（同源同版本、``ENABLE_PLUGIN_LOADING=ON``）—— 两个插件以
    ``target_link_libraries(heif-<name> PRIVATE … heif)`` 依赖它，且运行期必须由它
    ``dlopen`` 插件才能注册 JPEG 2000 编解码器；仓库既有 ``archives/l/libheif/1.22.2``
    是 ``ENABLE_PLUGIN_LOADING=OFF`` 的 codec-free 核心（且版本不同、ABI 不匹配），
    装不了插件，故不能作为本包依赖
  * ``include/libheif/*.h``、``lib/pkgconfig/libheif.pc``、``lib/cmake/libheif/*``

上游证据（解包 libheif 1.23.0 后原文）：

  * ``CMakeLists.txt:264-279``
        plugin_option(OpenJPEG_ENCODER "OpenJPEG J2K encoder" OFF ON)
        plugin_option(OpenJPEG_DECODER "OpenJPEG J2K decoder" OFF ON)
        if (WITH_OpenJPEG_ENCODER OR WITH_OpenJPEG_DECODER) find_package(OpenJPEG 2) …
  * ``libheif/plugins/CMakeLists.txt:84-90``
        plugin_compilation(j2kdec OPENJPEG OPENJPEG_FOUND OpenJPEG_DECODER OPENJPEG_DECODER)
        plugin_compilation(j2kenc OPENJPEG OPENJPEG_FOUND OpenJPEG_ENCODER OPENJPEG_ENCODER)
  * ``libheif/plugins/CMakeLists.txt:2-45`` ``plugin_compilation()`` 在
    ``PLUGIN_LOADING_SUPPORTED_AND_ENABLED AND WITH_<OPT>_PLUGIN`` 时
    ``add_library(heif-${name} MODULE …)`` 并
    ``install(TARGETS heif-${name} LIBRARY DESTINATION <libdir>/libheif)``；
    否则退化为静态编入宿主（HAVE_<OPT>=1）。

为什么 encoder + decoder 都开（不是为凑数字放开开关）：

  1. 上游把「OpenJPEG 后端」定义为一对 ``OpenJPEG_DECODER``/``OpenJPEG_ENCODER``
     （``CMakeLists.txt:264-265`` 相邻两行、同一 ``find_package(OpenJPEG 2)`` 门控），
     本包包名就是该编解码库名（``openjpeg``）；只交付一半会让
     ``heif_context_get_encoder_for_format(heif_compression_JPEG2000)`` 无解；
  2. 父 tarball 内**没有 J2K 语料**（``tests/data/`` 无 J2K 样本，只有
     ``fuzzing/data/corpus/j2k*.heif`` 两个模糊测试输入），只有编码器在场才能对交付的
     解码器做真实往返验证——这正是上游 ``tests/encode_jpeg2000.cc`` 的 2 个用例做的事，
     也是 ``test_package`` 往返用例做的事（见 test_package/ 与 notes.md）。

依赖边界（外部依赖，非内树捆绑）：

  树内 ``find . -iname '*openjp*' -o -iname '*openjpeg*' -o -iname '*j2k*'`` 的全部命中只有
  ``cmake/modules/FindOPENJPH.cmake``（另一个后端：OpenJPH/HT-J2K）、树内适配层
  ``libheif/plugins/{decoder,encoder}_openjpeg.{cc,h}``、测试语料与用例——
  **没有 OpenJPEG 本体源码副本**。故复用仓库既有独立包 ``openjpeg/2.5.4``
  （``archives/o/openjpeg/2.5.4``，有 ``conanfile.py``/``conandata.yml``，manifest status=built，
  远端 ohpcd 有 binary，仓库内 5 个已合并包在用：imagemagick-full/leptonica/opencv/poppler/openslide）。

消费方对接（CMakeDeps，实测判据在 notes.md）：

  libheif 的 ``plugin_compilation()`` 用**全大写** ``OPENJPEG_FOUND`` /
  ``OPENJPEG_INCLUDE_DIRS`` / ``OPENJPEG_LIBRARIES`` 判断与链接
  （宏体在 ``libheif/plugins/CMakeLists.txt:2-45``：``:21`` 用 ``${varName}_INCLUDE_DIRS``、``:22`` 用
  ``${varName}_LIBRARIES``（``varName=OPENJPEG``）；两处后端注册在 ``:86,90``，把 ``OPENJPEG_FOUND`` 作为
  ``foundName`` 传入；上游另一处用的是正确大小写 ``OpenJPEG_FOUND``，见 ``CMakeLists.txt:374``），
  而 CMakeDeps 在 config 模式只 set
  与 ``find_package`` 同名大小写的 ``OpenJPEG_*``，且 CMakeToolchain 默认
  ``CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON``（config 优先）→ 必须显式要求 **module 形态**
  （生成 ``FindOpenJPEG.cmake``，其 module 模板会 ``set(OPENJPEG_FOUND 1)``）+
  ``cmake_additional_variables_prefixes=["OPENJPEG"]``（补 ``OPENJPEG_LIBRARIES`` /
  ``OPENJPEG_INCLUDE_DIRS``）。否则 ``OPENJPEG_FOUND`` 未定义、j2kdec/j2kenc 后端被
  静默跳过（假绿：包能建出来但没有插件）。设备实测（notes.md「CMakeDeps 探测」）：
  ``OpenJPEG_FOUND=1``、``OPENJPEG_FOUND=1``、
  ``OPENJPEG_LIBRARIES=OPENJPEG::OpenJPEG``、``OpenJPEG_VERSION=2.5.4``。

插件目录可移植性：上游把默认插件目录**编译期钉死**在 ``heif_version.h`` 的
``LIBHEIF_PLUGIN_DIRECTORY``（= 构建时的 ``${CMAKE_INSTALL_FULL_LIBDIR}/libheif``，
即本包在 Conan 缓存里的绝对路径），跨缓存/跨机不可移植。因此 ``package_info()`` 用
``runenv_info`` 导出 ``LIBHEIF_PLUGIN_PATH``，让 ``VirtualRunEnv``/``conanrun`` 环境自动
带上（上游 ``libheif/plugins_unix.cc:37`` 优先读该环境变量）。

三个 OHOS 必修项（都在 ``generate()``，上游源码零修改、无补丁）：

1. ``CMAKE_SYSTEM_NAME="Linux"``（**只在 OHOS**）：设备 ``uname -s`` = HarmonyOS，而 SDK 的
   cmake 只有 ``Modules/Platform/OHOS.cmake``、没有 ``HarmonyOS.cmake``；不显式指定时
   cmake 打一行 "System is unknown to cmake" 继续，把平台变量留空（含
   ``CMAKE_SHARED_LIBRARY_SONAME_C_FLAG``）→ 宿主 ``libheif.so`` 不写 SONAME →
   插件 MODULE 的 ``DT_NEEDED`` 落成含斜杠的路径 ``../libheif.so``（设备实测），
   加载器对含 ``/`` 的名字按 CWD 解析 → ``heif_init()`` dlopen 失败。
2. 装后重签插件（``package()`` 的 ``_resign_installed_plugins()``）：CMake 默认在
   ``cmake --install`` 时就地改写 RUNPATH，而 OHOS clang 链接期写了 ELF 签名
   （``.note.ohos.ident``/``.codesign``）→ 字节变即签名失效 → 装出来的插件 ``dlopen`` 报
   ``Permission denied``（**EACCES，不是 not found**），``heif_init`` code=11。
   只链同构建树 target 的目标（两个插件都链 ``heif``）才被改写；宿主安装前后 sha256 完全相同
   （只查宿主会误判）。处置用已合并先例（openh264/2.6.0、ffmpeg/8.1.2）的
   ``llvm-objcopy --remove-section .codesign`` + ``binary-sign-tool sign -selfSign 1``。
   ``package()`` 末尾再**真 dlopen** 两个插件（唯一能验签的 oracle），失败即硬失败。
3. ``_LIBCPP_ENABLE_EXPERIMENTAL`` 编译期宏：设备 libc++ 15004 在未定义它时定义
   ``_LIBCPP_HAS_NO_INCOMPLETE_RANGES``，屏蔽 C++20 ranges 算法，而 ``box.cc`` 用了
   ``std::ranges::all_of/find`` → 编译失败。
"""
import glob
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cmd_args_to_string
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


# 交付面之外的上游后端开关：显式 OFF（不属交付面；开启会引入未适配/未发布的依赖，R36）。
_DISABLED_PLUGIN_OPTIONS = (
    "LIBDE265", "X265", "X264", "KVAZAAR", "UVG266", "VVDEC", "VVENC",
    "AOM_DECODER", "AOM_ENCODER", "DAV1D", "SvtEnc", "RAV1E",
    "JPEG_DECODER", "JPEG_ENCODER", "FFMPEG_DECODER", "OpenH264_DECODER",
    "OPENJPH_ENCODER", "LIBSHARPYUV",
)

# 父 tarball（libheif 1.23.0）全量注册面的「用例」口径读数 = 主 N。
# 取数命令与全部候选口径见 notes.md「上游测试清点」；本常数只用于算 NOT_RUN，不参与放行判据。
_PARENT_SURFACE_N = 217

# 交付的两个插件模块（上游目标名 → 产物名）。
_PLUGIN_MODULES = ("libheif-j2kdec.so", "libheif-j2kenc.so")

# Catch2 v3.7 汇总行（tests/catch_amalgamated.cpp:10023-10069 printTestRunTotals）：
# 全通过时只有一行 "All tests passed (A assertions in M test cases)"；
# 否则是 "test cases: T | P passed | F failed | S skipped"（值为 0 的列不打印）。
_CATCH_ALL_PASS_RE = re.compile(
    r"All tests passed \((\d+) assertions? in (\d+) test cases?\)")
_CATCH_CASE_TOTAL_RE = re.compile(r"test cases:\s*(\d+)")
_CATCH_COL_RE = {
    "passed": re.compile(r"(\d+) passed"),
    # 末尾还有 "failed as expected" 列，必须排除；否则 failed 列缺失时会误取它
    "failed": re.compile(r"(\d+) failed(?! as expected)"),
    "skipped": re.compile(r"(\d+) skipped"),
}
_CTEST_TEST_NAME_RE = re.compile(r"Test\s+#\d+:\s+(\S+)")


class LibheifOpenjpegConan(ConanFile):
    name = "libheif-openjpeg"
    version = "1.23.0"
    description = ("OpenJPEG (JPEG 2000) decoder+encoder backend plugin modules for libheif "
                   "1.23.0, built in-tree from libheif/plugins/{decoder,encoder}_openjpeg.cc as "
                   "the upstream CMake targets heif-j2kdec/heif-j2kenc "
                   "(libheif-j2kdec.so / libheif-j2kenc.so); ships the plugin-loading-enabled "
                   "libheif host they require")
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/strukturag/libheif"
    url = "https://github.com/strukturag/libheif"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 唯一直接依赖：仓库既有独立包（已发布到 ohpcd；W0 用 conan install --build=never 实测
        # 可取得，见 $TASK_DIR/w0-deps.txt）。插件模块链接它。
        self.requires("openjpeg/2.5.4")

    def validate(self):
        if not self.options.shared:
            # 插件以 MODULE 形态被宿主 dlopen，必须与宿主共享同一份 libheif 运行时；
            # 静态宿主会让插件自带一份副本（状态分裂）。上游 BUILD_SHARED_LIBS 默认 ON。
            raise ConanInvalidConfiguration(
                f"{self.ref}: 插件模块形态要求宿主 heif 为共享库（shared=True）")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # OpenJPEG 的 CMakeDeps 形态见模块 docstring「消费方对接」。
        deps = CMakeDeps(self)
        deps.set_property("openjpeg", "cmake_find_mode", "module")
        deps.set_property("openjpeg", "cmake_additional_variables_prefixes", ["OPENJPEG"])
        deps.generate()

        tc = CMakeToolchain(self)
        # R33：全部构建配置经 CMakeToolchain 下发，不依赖 shell 环境变量。
        # 宿主必须是共享库（插件 dlopen 语义；见 validate()）。
        tc.variables["BUILD_SHARED_LIBS"] = True

        if str(self.settings.os) == "OHOS":
            # ==== 必修 1：OHOS 平台文件缺失导致宿主无 SONAME → 插件 DT_NEEDED 写路径 ====
            # 设备 uname -s = HarmonyOS，而 SDK 的 cmake 只有 Platform/OHOS.cmake、
            # 没有 Platform/HarmonyOS.cmake；conan 默认把 OHOS 映射成
            # CMAKE_SYSTEM_NAME=HarmonyOS → cmake 打 "System is unknown to cmake" 继续，
            # 但平台变量留空（其中 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空）→ 宿主
            # libheif.so 不写 SONAME、也没有版本化文件名 → 插件 MODULE 的 DT_NEEDED
            # 落成构建树路径（含斜杠，按 CWD 解析）→ 装出来的包里 heif_init() dlopen 必失败
            # （历史证据：archives/l/libheif/1.18.2/notes.md「NEEDED 硬编码相对路径、未解决」）。
            # 显式钉成 Linux：平台文件存在 → SONAME 正常（libheif.so.1），插件 DT_NEEDED
            # 变成无斜杠的 libheif.so.1。设备实测：不加此行时 readelf -d
            # <build>/libheif/libheif.so 的 SONAME 段为空（只有 NEEDED libc++_shared/libc）。
            # 仓库同口径 693 个配方（如 archives/o/openjpeg2/2.5.4、archives/a/ableton-link/3.1.2）。
            # 注意：本包不另起子工程 configure，故无需向子工程二次传该变量。
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"

            # 设备 libc++ 把 C++20 ranges 算法藏在 _LIBCPP_HAS_NO_INCOMPLETE_RANGES 后面，
            # 而上游 box.cc 用了 std::ranges::all_of/find（C++20）→ 不开这个宏必然编译失败
            # （设备实测：conan create 报 box.cc:4155/4156/4166 "no member named … in
            # namespace 'std::ranges'"，见 notes.md「OHOS libc++ ranges」）。
            # 判据链（设备实测）：__config:39 _LIBCPP_VERSION=15004；
            # __config:254-256 在 !_LIBCPP_ENABLE_EXPERIMENTAL && !_LIBCPP_BUILDING_LIBRARY 时
            # 定义 _LIBCPP_HAS_NO_INCOMPLETE_RANGES；__algorithm/ranges_all_of.h:25 整个头体被
            # 该宏屏蔽。只需编译期宏，不需要 -lc++experimental（本包不碰 <format> 运行期符号）；
            # 公共 API 头（libheif/api/**）0 处 std::ranges → 不需要向消费者传播。
            # 同族先例：archives/l/libpqxx/8.0.1、archives/c/cdo/2.6.3、archives/m/mrc/1.3.17。
            tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None
        # 插件装在 <prefix>/lib/libheif（package_info() 的 LIBHEIF_PLUGIN_PATH 依赖该布局）；
        # 不显式钉住会随 GNUInstallDirs 在 64 位平台选 lib64。同族先例 archives/o/openjpeg2。
        tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        # --- 交付面：OpenJPEG 后端，且以独立插件模块形态构建 ---
        tc.variables["ENABLE_PLUGIN_LOADING"] = True
        tc.variables["WITH_OpenJPEG_DECODER"] = True
        tc.variables["WITH_OpenJPEG_DECODER_PLUGIN"] = True
        tc.variables["WITH_OpenJPEG_ENCODER"] = True
        tc.variables["WITH_OpenJPEG_ENCODER_PLUGIN"] = True

        # --- 交付面之外的上游后端全部显式关闭 ---
        for option in _DISABLED_PLUGIN_OPTIONS:
            tc.variables[f"WITH_{option}"] = False
        tc.variables["WITH_UNCOMPRESSED_CODEC"] = False
        tc.variables["WITH_WEBCODECS"] = False
        tc.variables["WITH_HEADER_COMPRESSION"] = False

        # --- 非交付面（示例/工具/文档/模糊测试/覆盖率）：不构建 ---
        tc.variables["WITH_EXAMPLES"] = False
        tc.variables["WITH_EXAMPLE_HEIF_THUMB"] = False
        tc.variables["WITH_EXAMPLE_HEIF_VIEW"] = False
        tc.variables["WITH_GDK_PIXBUF"] = False
        tc.variables["BUILD_DEVELOPMENT_TOOLS"] = False
        tc.variables["BUILD_DOCUMENTATION"] = False
        tc.variables["WITH_FUZZERS"] = False
        tc.variables["ENABLE_COVERAGE"] = False

        # --- 上游测试：交付面内可编译的用例真跑（R51 / AGENTS §3.5），不是为凑数字放开开关 ---
        tc.variables["BUILD_TESTING"] = True

        # 符号可见性保持上游默认 ON（只导出公开 API；已合并的 archives/l/libheif/1.22.2 同口径）。
        # 代价：依赖内部符号的 12 个注册项（含 jpeg2000.cc 的 30 个 J2K 用例）无法编译，
        # 按 NOT_RUN 记账并逐项归因（见 notes.md）。不为凑数字把它关掉。
        tc.variables["WITH_REDUCED_VISIBILITY"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            # 并行度：设备 affinity 8、conan 却按 os.cpu_count()=20 取默认（会 2.5x 超订）；
            # 而 conan-verify 的干净轮固定用 `conan create`，既不带 `-c tools.build:jobs`
            # 又有 **3600s 硬超时**（`scripts/ohc/conan_verify.py:751`，`--timeout` 不生效），
            # 清缓存轮是无增量全量构建 → `-j1` 实测 ~50 min，贴上限。取 2：与编排的槽位纪律
            # （2 槽 × j2 = 4 路 ≤ affinity 8）一致，且 CI 同值。同族先例
            # archives/o/openjpeg2/2.5.4（对 OHOS define jobs=1）。
            self.conf.define("tools.build:jobs", 2)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests(cmake)

    # ------------------------------------------------------------- 上游测试
    def _run_upstream_tests(self, cmake):
        """跑上游 CTest 注册面，并按 Catch2「用例」单位打印机器可读台账。

        ① ``ctest``：上游自己的测试入口（tests/CMakeLists.txt 的 add_test；
           ENABLE_PLUGIN_LOADING 时上游给每个测试设了
           ENVIRONMENT LIBHEIF_PLUGIN_PATH=<build>/libheif/plugins，插件因此可被装载）。
           失败即抛错——不允许"测试红了还出包"。
        ② 逐测试二进制再跑一次 Catch2，取「用例」粒度的汇总行：本包申报的上游 N 就是用例
           单位，只有同一单位才能记账（TOTAL = PASS + FAIL + SKIP + NOT_RUN）。
           两个动作都是真实执行，日志留在 build 目录，不随包交付。
        """
        ctest_log = os.path.join(self.build_folder, "ctest-upstream.log")
        with open(ctest_log, "w") as handle:
            cmake.ctest(cli_args=["--output-on-failure"], stdout=handle, stderr=handle)
        with open(ctest_log, "r", errors="replace") as handle:
            ctest_output = handle.read()
        ctest_total = re.search(r"Total Tests:\s*(\d+)", ctest_output) or \
            re.search(r"tests passed.*out of\s+(\d+)", ctest_output)
        self.output.info("HMBS_UPSTREAM_CTEST=" + json.dumps({
            "log": "ctest-upstream.log",
            "registered": int(ctest_total.group(1)) if ctest_total else None,
            "command": "ctest --output-on-failure",
        }))

        plugin_dir = os.path.join(self.build_folder, "libheif", "plugins")
        tests_dir = os.path.join(self.build_folder, "tests")
        ledger = []
        totals = {"cases": 0, "passed": 0, "failed": 0, "skipped": 0, "assertions": 0}
        for name in self._registered_tests():
            binary = os.path.join(tests_dir, name)
            if not os.path.isfile(binary):
                self.output.warning(f"上游测试二进制缺失: {binary}")
                continue
            log = os.path.join(self.build_folder, f"upstream-test-{name}.log")
            # LIBHEIF_PLUGIN_PATH 显式给出（ctest 走 ENVIRONMENT 属性，这里直接跑要自己带）；
            # LD_LIBRARY_PATH 由 conanrun 环境提供（openjpeg 依赖 + 构建树）。
            self.run(
                f'LIBHEIF_PLUGIN_PATH="{plugin_dir}" '
                f"{cmd_args_to_string([binary])} > {cmd_args_to_string([log])} 2>&1 || true",
                env=["conanbuild", "conanrun"],
            )
            with open(log, "r", errors="replace") as handle:
                entry = self._parse_catch2(name, handle.read())
            if entry is None:
                self.output.warning(f"未能从 {name} 的 Catch2 输出解析汇总行")
                continue
            ledger.append(entry)
            for key in totals:
                totals[key] += entry.get(key, 0)

        self.output.info("HMBS_UPSTREAM_TEST_LIST=" + json.dumps(sorted(ledger, key=lambda e: e["binary"])))
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "framework": "catch2-3.7+ctest",
            "command": "ctest --output-on-failure；再逐 <build>/tests/<binary> 取 Catch2 汇总行",
            "unit": "test_case",
            "binaries": len(ledger),
            "cases": totals["cases"],
            "passed": totals["passed"],
            "failed": totals["failed"],
            "skipped": totals["skipped"],
            "assertions": totals["assertions"],
            "not_run": _PARENT_SURFACE_N - totals["cases"],
        }))

    def _registered_tests(self):
        """上游 ctest 注册的测试名（= 测试可执行文件名，位于 <build>/tests/）。"""
        log = os.path.join(self.build_folder, "ctest-list.log")
        self.run(f"ctest -N > {cmd_args_to_string([log])} 2>&1 || true",
                 env=["conanbuild", "conanrun"])
        with open(log, "r", errors="replace") as handle:
            return _CTEST_TEST_NAME_RE.findall(handle.read())

    @staticmethod
    def _parse_catch2(binary, output):
        match = _CATCH_ALL_PASS_RE.search(output)
        if match:
            assertions, cases = int(match.group(1)), int(match.group(2))
            return {"binary": binary, "cases": cases, "passed": cases,
                    "failed": 0, "skipped": 0, "assertions": assertions}
        total = _CATCH_CASE_TOTAL_RE.search(output)
        if not total:
            return None
        entry = {"binary": binary, "cases": int(total.group(1)),
                 "passed": 0, "failed": 0, "skipped": 0, "assertions": 0}
        tail = output[total.start():]
        line = tail.split("\n")[0]
        for key, pattern in _CATCH_COL_RE.items():
            found = pattern.search(line)
            if found:
                entry[key] = int(found.group(1))
        assertions = re.search(r"assertions:\s*(\d+)", tail)
        if assertions:
            entry["assertions"] = int(assertions.group(1))
        return entry

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 交付面自检：插件模块必须真落在 <pkg>/lib/libheif/。否则本包会变成
        # "库在、功能不在"的空壳（上游对未找到的后端只打一行 message 就继续，静默降级）。
        plugin_dir = os.path.join(self.package_folder, "lib", "libheif")
        missing = [name for name in _PLUGIN_MODULES
                   if not glob.glob(os.path.join(plugin_dir, name + "*"))]
        if missing:
            raise ConanException(
                f"{self.ref}: 交付面自检失败——{plugin_dir} 下缺少插件模块 {missing}"
                f"（实际内容：{sorted(os.listdir(plugin_dir)) if os.path.isdir(plugin_dir) else '目录不存在'}）")
        if not glob.glob(os.path.join(self.package_folder, "lib", "libheif.so*")):
            raise ConanException(f"{self.ref}: 交付面自检失败——缺少宿主 lib/libheif.so")

        # 必需：`cmake --install` 就地改写 RUNPATH → OHOS ELF 签名失效 → dlopen EACCES
        # （详见 ``_resign_installed_plugins``）。重签放在自检之前，保证下面 dlopen 的是最终产物。
        self._resign_installed_plugins(plugin_dir)
        self._assert_plugins_loadable(plugin_dir)

    def _resign_installed_plugins(self, plugin_dir):
        """装后重签插件模块（OHOS 必需）。

        因果链（本任务设备实测，逐条可复跑）：① OHOS 的 clang 在链接期把 ELF 签名写进
        ``.note.ohos.ident`` / ``.codesign``；② CMake 默认 ``BUILD_WITH_INSTALL_RPATH=OFF``，
        ``cmake --install`` 会**就地改写** RUNPATH → 插件字节变（实测 sha256
        ``86158e32…`` → ``488821aa…``，``cmp -l`` 231 字节差，RUNPATH 由有变无）→
        签名失效；③ 装载被拒：``dlopen: … Permission denied``（**EACCES，不是 not found**），
        ``heif_init`` 返回 code=11，``heif_have_decoder_for_format(JPEG2000)==0``。
        被改写的只有**链了同构建树 target** 的目标（两个插件都链 ``heif``）；宿主
        ``libheif.so.1.23.0`` 安装前后 sha256 **完全相同** —— 只查宿主会误判成"没问题"。

        处置：装后重签（同族已合并先例 ``archives/o/openh264/2.6.0``、``archives/f/ffmpeg/8.1.2``）。
        只签实体文件、跳过软链（对同一目标重复签无意义）。
        """
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            raise ConanException(
                f"{self.ref}: 缺少装后重签工具 {objcopy} / {signer}；OHOS 上不重签会导致"
                f"装出来的插件 dlopen 报 Permission denied")
        # 只签**实体文件**（软链解引用后去重）：本设备 MODULE 产物是不带版本号的普通文件
        # （`libheif-j2kdec.so`），但换平台/换上游写法可能出现 `.so.N` + 软链，两种都覆盖。
        targets = set()
        for module in _PLUGIN_MODULES:
            for entry in glob.glob(os.path.join(plugin_dir, module + "*")):
                real = os.path.realpath(entry)
                if os.path.isfile(real):
                    targets.add(real)
        for path in sorted(targets):
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
            self.output.info(f"已重签插件: {os.path.basename(path)}")

    def _assert_plugins_loadable(self, plugin_dir):
        """用**构建树的上游测试可执行文件**对**安装副本**做真实装载判定（硬判据）。

        为什么不是解释器里的 ``ctypes.CDLL``（本包原实现，CI 红的根因）：

        * 原实现 ``self.run(<python> check_plugin_dlopen.py …)`` 在设备上通过
          （采信轮输出 ``HMBS_PLUGIN_DLOPEN_OK``），但 **CI worker 上必然失败**——
          worker 的 conan 跑在 HNP 解释器 ``/data/service/hnp/bin/python3`` 下，
          该域对**用户目录下任意 .so** 的 ``dlopen`` 一律回 ``EACCES``，与签名状态无关。
          同族先例 ``archives/b/barvinok/0.41.9``（build #33869：连已发布的
          release 签名 ``libgmp`` 都被拒，原文"a platform boundary … not a recipe
          failure"）；本包 build #54215 / #56625 / #56627 三次 CI **逐字同报**
          ``OSError: Error loading shared library …/p/lib/libheif.so: Permission denied``。
        * **同一次构建**的 ``build()`` 阶段上游 ctest 逐字跑通（``encode_jpeg2000`` 2/2、
          37/8/6/23 与设备完全一致）——即"被 **exec** 起来的进程"dlopen 用户目录 .so
          是允许的，被拒的只是解释器进程。⇒ 判据必须是 **exec 形态**，不是解释器形态。

        新判据（同一次 ``conan create`` 内，构建树测试可执行文件 → 安装副本）：
        ``LD_LIBRARY_PATH=<本包 lib>+<依赖 lib>`` 跑 ``tests/encode_jpeg2000``
        （上游 ``add_test(NAME encode_jpeg2000 COMMAND ./encode_jpeg2000)``，无参数、
        cwd = tests 目录），并把 ``LIBHEIF_PLUGIN_PATH`` 指到**安装副本插件**：

        * **宿主**：该可执行文件 ``NEEDED libheif.so.1``，按 ELF 规定先查
          ``LD_LIBRARY_PATH`` 再查自己的 ``DT_RUNPATH`` ⇒ 装出来的宿主真被装载
          （本机反证：往 ``LD_LIBRARY_PATH`` 放一个坏的 ``libheif.so.1`` 立刻
          ``rc=127 / Error loading shared library``，证明构建树 RUNPATH 不会兜底）；
        * **插件**：``heif_init()`` 按 ``LIBHEIF_PLUGIN_PATH`` 绝对路径 **dlopen**
          装出来的两个插件（本机负控制：指向不存在目录 ⇒ ``rc=42``、2/2 用例失败，
          证明换不掉、也不会退回构建树插件）；
        * **功能**：真 J2K 编码往返跑通（``rc=0`` / 16 assertions）⇒ 宿主 + 插件 +
          后端全链路可用。

        ``binary-sign-tool`` 没有 ``verify`` 子命令，"签名有效"没有独立 oracle ——
        **真装载就是唯一 oracle**；test_package 侧再由 conanrun 覆盖同一链路。
        """
        test_bin = os.path.join(self.build_folder, "tests", "encode_jpeg2000")
        if not os.path.isfile(test_bin):
            raise ConanException(
                f"{self.ref}: 交付面装载自检缺前置件 {test_bin}"
                "（BUILD_TESTING 未构建上游测试可执行文件，无法做 exec 形态装载判定）")
        libdirs = [os.path.join(self.package_folder, "lib")]
        for dep in self.dependencies.values():
            if dep.package_folder:
                libdirs.extend(os.path.join(dep.package_folder, d) for d in dep.cpp_info.libdirs)
        cmd = 'LD_LIBRARY_PATH="{}" LIBHEIF_PLUGIN_PATH="{}" "{}"'.format(
            os.pathsep.join(libdirs), plugin_dir, test_bin)
        self.run(cmd, cwd=os.path.dirname(test_bin))
        self.output.info(
            "HMBS_INSTALLED_RUNTIME_LOAD_OK (exec-time NEEDED host + heif_init dlopen plugins)")

    def package_info(self):
        # 交付的宿主库（消费者链接的就是它；插件模块是运行期产物，不在 libdirs 里）。
        self.cpp_info.libs = ["heif"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libheif")
        self.cpp_info.set_property("cmake_target_name", "libheif::libheif")
        self.cpp_info.set_property("pkg_config_name", "libheif")
        # 插件模块装在 <pkg>/lib/libheif/；上游把默认插件目录编译期钉死成构建时的绝对路径，
        # 跨缓存/跨机不可移植，故显式导出 LIBHEIF_PLUGIN_PATH
        # （VirtualRunEnv / self.run(env="conanrun") 会自动带上）。
        self.runenv_info.define(
            "LIBHEIF_PLUGIN_PATH",
            os.path.join(self.package_folder, "lib", "libheif"),
        )
