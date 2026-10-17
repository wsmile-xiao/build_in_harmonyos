#!/usr/bin/env python3
"""Conan recipe — ruy 0.0.0-git20230215.21a85fe (Google ruy, CMake, C++14).

上游事实（对 commit 21a85fe 官方 tarball 实测审计，282524 bytes，
sha256 e151a5b55059a6e83ded001787e1a8889ba1e5e4eaa5bc836b9b660e7e1cb519）：

  * 纯 CMake 项目，顶层 `project(ruy CXX)` + `set(CMAKE_CXX_STANDARD 14)`。
    自研 CMake 规则函数（cmake/ruy_cc_library.cmake 等，由 bazel_to_cmake 生成）。
  * 产出的库目标共 30 个（见 package_info）：ruy_frontend / ruy_trmul /
    ruy_context / ruy_tune / ruy_kernel_arm / ruy_kernel_avx 系 / ruy_pack_* 系 /
    ruy_profiler_* 等。**x86_64 判据只影响编译选项（-mavx* 等），不裁剪库目标**，
    因此该 30 项清单在 aarch64 上同样成立（已静态核对 ruy/CMakeLists.txt 第
    693/765/837 行，三处 if(...x86_64...) 均只 set(COPTS)，其后紧跟的是无条件
    的 ruy_cc_library(...)）。
  * 外部依赖只有 cpuinfo（公共头 include/ruy/... 不引用它，但 ruy_cpuinfo 库链接它）。
  * 许可证 Apache-2.0，上游文件名为 `LICENSE`。
  * 上游自带 install(EXPORT ruyTargets ... DESTINATION lib/cmake/ruy)，会与
    CMakeDeps 生成的 ruy-config.cmake 在 lib/cmake/ 下同名碰撞 ⇒ package() 移除。
  * 上游 example/ 由 ruy_cc_binary 定义，该函数**没有任何 install 规则**
    （已逐行核对 cmake/ruy_cc_binary.cmake）⇒ example 目标会被编译但不会进包，
    包内不存在 bin/，故本包不声明也不提供命令行工具。

上游测试（在 build() 内真实执行，结果进入 CI 日志）：
  * `enable_testing()` 仅在 `NOT RUY_MINIMAL_BUILD` 时被调用；而
    `RUY_MINIMAL_BUILD` 的默认值取自 `RUY_MINIMAL_BUILD_DEFAULT_VALUE`，
    该值在 ruy 作为**顶层项目**时为 OFF（CMakeLists.txt 第 23-28 行）。
    conan 以 ruy 源码根为项目根，因此 ruy 就是顶层项目。
  * 由此 ctest 注册 **33 条** ruy_cc_test：ruy/CMakeLists.txt 32 条 +
    ruy/profiler/CMakeLists.txt 1 条（profiler 目录经 ruy_add_all_subdirs()
    自动纳入，其 ruy_cc_test 无任何条件守卫）。
  * **本配方不设 RUY_MINIMAL_BUILD=True**——这一点与 Conan Center 的 ruy 配方
    相反：CCI 设其为 True，而 ruy_cc_test() 的第一句就是
    `if(RUY_MINIMAL_BUILD) return()`，会让 33 个测试一条都不注册、
    enable_testing() 也不被调用，即"零上游测试"。那对本仓库的
    L1c（上游测试真实执行）是无法接受的，故此处保持默认 OFF。

OHOS 适配要点：
  * **vendor googletest**：tarball 里 third_party/googletest 是未 checkout 的
    子模块（空目录），上游对它的引用带 EXISTS 保护 ⇒ 测试会被静默跳过、
    测试目标在链接期找不到 gtest 目标。source() 阶段把 v1.14.0 放到该路径
    即可让 add_subdirectory("third_party/googletest") 生效。
    同时设 INSTALL_GTEST=OFF，防止 googletest 的 install 规则把它的头文件与
    库混进 ruy 的安装产物；设 BUILD_GMOCK=OFF（ruy 全树不引用 gmock，已实测
    grep 无命中），省一份编译量。
  * **CMake 平台名**：CMake 不识别 HarmonyOS，`CMAKE_SYSTEM_NAME` 会退化成
    宿主值、`CMAKE_SYSTEM_PROCESSOR` 变成 unknown。强制 Linux/aarch64
    （同仓库先例 archives/c/cpuinfo）。
  * **构建步骤输出必须绑定日志文件**（不改上游、只改本配方）：conan 的
    ConanFile.run() 会把 recipe 进程自身的输出流继承给构建子进程，在 OHOS 上
    clang 于第一个编译单元静默退出（make 只报 `Error 1`、零诊断）。见
    _run_bound_step()。
  * **构建目录改名**：上游根目录的 Bazel `BUILD` 文件与 cmake_layout 默认的
    `build` 目录，在 HMDFS（大小写不敏感，官方知识库 E193）上指向同一 inode，
    导致 conan create 在 generate 阶段抛 NotADirectoryError 直接失败。
    改为 `build_folder="build_dir"`（官方 E470 的既定解法）。详见 layout()。
  * 单 job：HMDFS 上 make jobserver fifo 被内核拒绝（EPERM），固定 -j1。

两个补丁（都不是 OHOS 专属）：
  * 0001 把 cmake_minimum_required() 从 project() 之后移到文件开头——
    上游把它写在 project(ruy CXX) 的下一行（见 ruy issue #328）。
  * 0002 去掉 ruy_cc_library 里 add_library() 硬编码的 STATIC，
    否则本仓库要求的 shared 选项无法生效。
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rmdir)


class RuyConan(ConanFile):
    name = "ruy"
    version = "0.0.0-git20230215.21a85fe"
    description = ("ruy: a matrix multiplication library covering the needs of "
                   "neural-network inference engines (GEMM kernels, packed paths "
                   "and quantized integer paths)")
    license = "Apache-2.0"
    homepage = "https://github.com/google/ruy"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("matrix", "multiplication", "gemm", "neural-network",
              "tensorflow", "quantization")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # 依赖写成**裸 ref**（不带 @user/channel）。
        # 仓库模板注释里的 R27 写的是「All dependencies MUST use @ohpcd/stable
        # format」，但 ohpcd 制品仓实际发布的是裸 ref —— 写成
        # `cpuinfo/<ver>@ohpcd/stable` 会在依赖解析阶段直接报
        # "Unable to find in remotes"。该模板注释是模板自身的缺陷，以已合入包
        # 的实际写法为准（先例：archives/f/ffmpeg/8.1.2、archives/g/gnuit/4.9.5
        # 的注释「CI 制品仓为裸 ref（无 @user/channel），勿写 @ohpcd/stable」、
        # archives/g/gcr-base/3.41.2「带 @ohpcd/stable 会报 Unable to find in
        # remotes」、archives/k/kxl/1.2.4）。
        #
        # 选 cpuinfo 这个版本号是因为它是制品仓内的**唯一**版本
        # （registry id=6510，0.0-git20250905.877328f，2025-09-05 快照）。
        # 平台版 cpuinfo 声明了 cmake_target_name = "cpuinfo::cpuinfo"，
        # 而 ruy 顶层 CMakeLists 的判据是
        #     if (NOT TARGET cpuinfo::cpuinfo) ... find_package(cpuinfo REQUIRED)
        # 故该依赖可被直接对接，无需改动 ruy 的 CPU 探测路径。
        self.requires("cpuinfo/0.0-git20250905.877328f")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 14)

    def layout(self):
        # 构建目录名必须避开默认的 "build"。
        # 上游仓库根目录有一个 Bazel 用的 `BUILD` 文件（283 字节，本包未改动它，
        # 它只服务 Bazel，CMake 路径完全不引用）。而 HMDFS 是**大小写不敏感**的
        # 文件系统（官方知识库 E193：BOO 与 boo 共享同一 inode，行为同 macOS
        # APFS/HFS+）。conan 会把源码树复制到构建根下，于是 `BUILD` 落在
        #   <build_root>/BUILD
        # 而 cmake_layout 默认要创建 `<build_root>/build/Release`，在该 FS 上
        # `build` 解析到的就是那个 `BUILD` 文件，mkdir 直接失败：
        #   NotADirectoryError: [Errno 20] Not a directory: '.../b/build/Release'
        # conan create 在 generate 阶段（尚未开始编译）即中断。
        # 真机实测 2026-09-29；reliable 包没有 BUILD 文件所以从未暴露。
        #
        # 解法即官方知识库 E470 的既定方案（来源 PR !7190）：
        #   cmake_layout(self, build_folder="build_dir")
        cmake_layout(self, build_folder="build_dir")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # vendor googletest 到 third_party/googletest（上游在此处有一个空的
        # submodule 目录，先移除再解压）。详见模块 docstring。
        gtest = self.conan_data["googletest"]
        dest = os.path.join(self.source_folder, "third_party", "googletest")
        if os.path.isdir(dest):
            rmdir(self, dest)
        get(self, url=gtest["url"], sha256=gtest["sha256"],
            destination=dest, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 显式保持 OFF：这是 33 条上游 ctest 得以注册的前提（见 docstring）。
        tc.cache_variables["RUY_MINIMAL_BUILD"] = "OFF"
        # 用 conan 提供的 cpuinfo，而不是 third_party/cpuinfo 子模块
        # （后者在 tarball 里同样是空目录，且 RUY_IS_TOPLEVEL 时会 FATAL_ERROR）。
        tc.variables["RUY_FIND_CPUINFO"] = "ON"
        # 上游默认值即 RUY_IS_TOPLEVEL，此处显式声明意图
        tc.variables["RUY_ENABLE_INSTALL"] = "ON"
        # Windows 共享库需要；对 OHOS/Linux 无副作用（与 CCI 配方一致）
        tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = "ON"
        # googletest：不装、不构建 gmock（ruy 全树无 gmock 引用）
        tc.cache_variables["INSTALL_GTEST"] = "OFF"
        tc.cache_variables["BUILD_GMOCK"] = "OFF"
        # OHOS：避免 CMake 编译器探测阶段就去调用链接器
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        # OHOS：CMake 不认 HarmonyOS，会退化成 unknown，架构分支全部走空
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            arch = str(self.settings.arch)
            if arch in ("armv8", "armv8.3", "armv9", "aarch64", "arm64", "arm64e"):
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            elif arch in ("x86_64", "x86"):
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = arch
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = arch
        tc.generate()
        # ruy 通过 find_package(cpuinfo REQUIRED) 找依赖 ⇒ 需要 conan 生成的 config
        CMakeDeps(self).generate()

    def build(self):
        # R9 / 知识图谱 E074：/storage/Users/... 走 HMDFS，make -j>1 需要在
        # TMPDIR 建 jobserver fifo，会被内核拒绝（EPERM），随后并行子任务集体
        # 报 "Error 1" 且看不到编译器输出。官方铁律：所有 make 调用固定单 job。
        # 必须在 CMake(self) 之前定义。
        self.conf.define("tools.build:jobs", 1)
        cmake = CMake(self)
        cmake.configure()
        # OHOS 真机实测（同 archives/r/reliable/1.3.5，2026-09-27）：conan 的
        # ConanFile.run() 会把 recipe 进程自身的输出流继承给构建子进程。在这种
        # 形态下 clang 会在第一个真正编译的翻译单元上静默退出——非 0 退出且一行
        # 诊断都不打印，make 只能报
        #   make[2]: *** [CMakeFiles/...: .obj] Error 1
        # 处置：把每个构建步骤的输出绑定到 build_folder/logs/<step>.log，跑完再
        # 回显进 conan 输出——既让编译恢复正常，又使 CI 侧 L1b/L1c 需要的编译与
        # ctest 痕迹留在 conan create 日志里（全部重定向而不同显会让证据消失）。
        self._run_bound_step(
            "build", lambda stream: cmake.build(stdout=stream, stderr=stream))
        # 33 条上游 ctest（32 + profiler 1）真实执行，通过率即 PR 里
        # "上游测试用例通过率"的依据。
        self._run_bound_step(
            "ctest", lambda stream: cmake.test(stdout=stream, stderr=stream))
        self._report_upstream_tests()

    def _run_bound_step(self, label, step):
        """执行一个构建步骤，并把该步骤的输出绑定到独立日志文件。

        ``step(stream)`` 内调用 CMake helper（configure/build/test 均支持
        ``stdout=``/``stderr=``）。输出不继承 conan 输出流时 OHOS 上的 clang
        才能正常编译，原因见 build() 内的实测记录。
        """
        log_dir = os.path.join(self.build_folder, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "{}.log".format(label))
        try:
            with open(log_path, "w", encoding="utf-8", errors="replace") as stream:
                step(stream)
        except ConanException:
            with open(log_path, encoding="utf-8", errors="replace") as handle:
                tail = handle.read().splitlines()[-80:]
            self.output.error(
                "build step '{}' failed; last lines of {}:".format(label, log_path))
            self.output.error("\n".join(tail))
            raise
        # 回显进 conan 输出：CI 的 L1b/L1c 门禁会在 conan create 日志里 grep
        # 编译痕迹与 ctest 痕迹，把输出全部关进文件会让这些证据消失。
        with open(log_path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
        self.output.info("--- {}.log ({} lines) ---".format(label, len(lines)))
        for start in range(0, len(lines), 500):
            self.output.info("\n".join(lines[start:start + 500]))

    def _report_upstream_tests(self):
        """从 build_folder/logs/ctest.log 汇总真实 ctest 结果并结构化输出。

        ctest 的汇总行为 ``100% tests passed, 0 tests failed out of 33``。
        解析真实计数（而不是假设 33 全过）可以识别"零测试/静默跳过"这类假成功。
        """
        log_path = os.path.join(self.build_folder, "logs", "ctest.log")
        if not os.path.isfile(log_path):
            return
        with open(log_path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        summary = re.search(
            r"(\d+)%\s+tests passed,\s+(\d+)\s+tests failed out of\s+(\d+)", text)
        if not summary:
            self.output.warn(
                "ctest summary line not found in {} — upstream tests may not "
                "have been registered".format(log_path))
            return
        percent, failed, total = (int(summary.group(1)),
                                  int(summary.group(2)),
                                  int(summary.group(3)))
        passed = total - failed
        result = {
            "status": "passed" if (failed == 0 and total > 0) else "failed",
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "total": total,
            "passed": passed,
            "failed": failed,
            "percent": percent,
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        print(marker, flush=True)
        self.output.info(marker)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream_result.json"),
                      "w", encoding="utf-8") as handle:
                handle.write(json.dumps(result, ensure_ascii=False, indent=1))
        except OSError:
            pass
        if result["status"] != "passed":
            raise ConanException(
                "ruy upstream ctest did not fully pass: "
                "passed={}/{} failed={}".format(passed, total, failed))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 上游自带 install(EXPORT ruyTargets) 会写出 lib/cmake/ruy/*.cmake，
        # 与 CMakeDeps 生成的 ruy-config.cmake 同名碰撞 ⇒ 移除。
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        # 防御性清理：ruy_cc_binary 无 install 规则，example 本不该进包；
        # 若上游未来补上规则，这里也能保证包内不出现 bin/（ruy 是库，非 CLI 工具）。
        rmdir(self, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # 30 个库目标，顺序沿用 Conan Center 配方（被依赖者靠前）。
        # 静态库的链接顺序敏感，故使用显式列表而非 collect_libs()。
        self.cpp_info.libs = [
            "ruy_frontend",
            "ruy_context",
            "ruy_trmul",
            "ruy_thread_pool",
            "ruy_blocking_counter",
            "ruy_prepare_packed_matrices",
            "ruy_ctx",
            "ruy_allocator",
            "ruy_prepacked_cache",
            "ruy_tune",
            "ruy_wait",
            "ruy_apply_multiplier",
            "ruy_block_map",
            "ruy_context_get_ctx",
            "ruy_cpuinfo",
            "ruy_denormal",
            "ruy_have_built_path_for_avx",
            "ruy_have_built_path_for_avx2_fma",
            "ruy_have_built_path_for_avx512",
            "ruy_kernel_arm",
            "ruy_kernel_avx",
            "ruy_kernel_avx2_fma",
            "ruy_kernel_avx512",
            "ruy_pack_arm",
            "ruy_pack_avx",
            "ruy_pack_avx2_fma",
            "ruy_pack_avx512",
            "ruy_system_aligned_alloc",
            "ruy_profiler_instrumentation",
            "ruy_profiler_profiler",
        ]
        self.cpp_info.set_property("cmake_file_name", "ruy")
        self.cpp_info.set_property("cmake_target_name", "ruy::ruy")
        self.cpp_info.set_property("pkg_config_name", "ruy")
        # OHOS 侧 clang 驱动不隐式链接 libm/libpthread，静态库消费者须显式带上。
        # R32：os 判断必须是 in ("Linux", "OHOS")，不能 == "Linux"。
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
