#!/usr/bin/env python3
"""Conan recipe — reliable 1.3.5 (Más Bandwidth 可靠 UDP 协议库, CMake).

上游事实（对 v1.3.5 官方 tarball 实测审计，35375 bytes，
sha256 e4b6f1c4955fb8a26e4d5a051c3f37559c8c86ca925b2519dfcbfa1ed554aa17）：

  * 纯 CMake 项目，导出单个目标 `reliable`（默认静态库；传
    -DBUILD_SHARED_LIBS=ON 得到动态库）。
  * **零外部依赖**：只用 C 标准库 + libm（reliable.c 内 5 处 fabs、
    1 处 pow，用于 rtt/jitter/bandwidth 统计）。
  * `RELIABLE_BUILD_TESTS` 的默认值等于 `RELIABLE_TOP_LEVEL`，即**作为
    顶层项目构建时**，tests / example / soak / stats / fuzz / fuzz_target
    六个 target 全部默认开启。作为包构建时这会把示例程序一并编出来，
    但上游没有给它们写 install 规则，因此不会进入 package/。
  * `project(... LANGUAGES C CXX)` 声明了 CXX：即使不构建任何 C++ 目标，
    CMake 也会探测 C++ 编译器（OHOS 侧 clang++ 存在，无影响）。
  * 上游许可证文件名拼写为 `LICENCE`（不是 LICENSE），SPDX 为 BSD-3-Clause。
  * 上游把 reliable.pc 装到 lib/pkgconfig；其 prefix 是构建机绝对路径，
    且 CMakeDeps 消费者不使用 pkgconfig，故从包内删除。
  * 上游**没有** install(EXPORT)：包内不存在上游自带的 CMake config，
    因此与 Conan CMakeDeps 生成的 reliable-config.cmake 不会碰撞，
    消费者直接 find_package(reliable CONFIG REQUIRED) 即可。

上游测试（在 build() 内全部真实执行，结果进入 CI 日志）：
  * ctest 注册 4 项：test / fuzz / soak / fuzz_target。
  * `test` 二进制由 test.cpp 驱动，调用 reliable.c 内嵌的可靠传输测试
    套件 `reliable_test()`（编译时 RELIABLE_ENABLE_TESTS=1），其中含
    14 个 RUN_TEST 子用例、87 个 check() 断言；全部通过后打印
    "*** ALL TESTS PASSED ***"。

OHOS 适配要点：
  * 零外部依赖 → 不存在依赖链阻塞，也不涉及依赖必须带 @ohpcd/stable 的问题。
  * `system_libs = ["m"]`：静态库消费者需显式链接 libm。同仓库纯 C 库先例
    archives/z/zxcvbn-c/2.6 亦按 `os in ("Linux", "OHOS")` 声明。
  * **不加任何补丁、不改一行上游源码**：上游本身即 Linux/musl 友好，
    OHOS 同为 clang 生态，预期零改动可构建（见 notes.md 的验证记录）。
  * **构建步骤输出必须绑定日志文件**（不改上游、只改本配方）：conan 的
    ConanFile.run() 会把 recipe 进程自身的输出流继承给构建子进程，在 OHOS 上
    clang 于第一个编译单元静默退出（make 只报 `Error 1`、零诊断）。详见
    build() 内实测记录与 notes.md 踩坑 #14。
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rmdir)

import os


class ReliableConan(ConanFile):
    name = "reliable"
    version = "1.3.5"
    description = ("Reliable UDP protocol library: packet acks, fragmentation and "
                   "reassembly, plus rtt / jitter / packet loss / bandwidth statistics")
    license = "BSD-3-Clause"
    homepage = "https://github.com/mas-bandwidth/reliable"
    url = "https://github.com/mas-bandwidth/reliable"
    topics = ("network", "udp", "reliability", "protocol", "packet-loss")

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

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 显式打开上游测试：这是"上游测试用例"的权威来源，build() 内会跑 ctest。
        tc.variables["RELIABLE_BUILD_TESTS"] = "ON"
        tc.variables["RELIABLE_SANITIZE"] = "OFF"
        # OHOS：避免 CMake 编译器探测阶段就去调用链接器
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R9 / 知识图谱 E074：本机 /storage/Users/... 走 HMDFS，make -j>1 需要
        # 在 TMPDIR 建 jobserver fifo，会被内核拒绝（EPERM），表现为
        #   make: jobserver mkfifo: .../GMfifoNNNNN: Operation not permitted
        # 之后并行子任务集体报 "Error 1" 且看不到编译器输出。
        # 官方铁律：所有 make 调用固定单 job。必须在 CMake(self) 之前定义。
        self.conf.define("tools.build:jobs", 1)
        cmake = CMake(self)
        # configure 不编译任何工程代码（CMake 自己会把 try_compile 的输出收进
        # 构建目录内的日志），真机三次实测均正常，故保持直连输出。
        cmake.configure()
        # OHOS 真机实测（2026-09-27）：conan 的 ConanFile.run() 会把 recipe 进程
        # 自身的输出流（stdout/stderr）继承给构建子进程。在这种形态下 clang 会在
        # **第一个真正编译的翻译单元**上静默退出——非 0 退出且一行诊断都不打印，
        # 于是 make 只能报
        #   make[2]: *** [CMakeFiles/reliable.dir/build.make:79: ...obj] Error 1
        # 构建日志里搜不到任何 error:/fatal 行（与上游源码、编译旗标、环境变量、
        # 沙盒拒绝 /bin/sh 均无关，这些都已逐项实测排除）。
        # 同一条命令行：在终端手工执行 → 成功；由 python subprocess 捕获输出执行
        # → 成功；把输出重定向到文件执行（cmake --build ... > log 2>&1）→ 成功。
        # 即失败只与"子进程输出流被 recipe 进程继承"这一形态绑定。
        # 处置：把每个构建步骤的输出绑定到 build_folder/logs/<step>.log，跑完再
        # 回显进 conan 输出——既让编译恢复正常，又使 CI 侧 L1b/L1c 需要的编译与
        # ctest 痕迹留在 conan create 日志里（全部重定向而不同显会让证据消失）。
        # 同族已合入先例：archives/l/libfishcamp/1.2（CMake，同症状同解法）、
        # archives/l/libgtop-tools/2.41.3、archives/l/libexmdbpp/1.11。
        self._run_bound_step(
            "build", lambda stream: cmake.build(stdout=stream, stderr=stream))
        # 上游 4 个 ctest 条目（test / fuzz / soak / fuzz_target）真实执行。
        # 通过率即为 PR 里"上游测试用例通过率"的依据。
        self._run_bound_step(
            "ctest", lambda stream: cmake.test(stdout=stream, stderr=stream))

    def _run_bound_step(self, label, step):
        """执行一个构建步骤，并把该步骤的输出绑定到独立日志文件。

        ``step(stream)`` 内调用 CMake helper（configure/build/test 均支持
        ``stdout=``/``stderr=``）。输出不继承 conan 输出流时 OHOS 上的 clang
        才能正常编译，原因见 build() 内的真机实测记录。
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

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENCE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 上游 reliable.pc 的 prefix 指向构建机路径，且 CMakeDeps 消费者不使用它
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["reliable"]
        self.cpp_info.set_property("cmake_file_name", "reliable")
        self.cpp_info.set_property("cmake_target_name", "reliable::reliable")
        # reliable.c 使用 fabs/pow，静态库消费者须显式链接 libm
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
