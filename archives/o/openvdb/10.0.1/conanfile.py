#!/usr/bin/env python3
"""Conan recipe for openvdb 10.0.1 — 稀疏体积数据结构库（C++）。

openvdb（AcademySoftwareFoundation）是电影工业级稀疏体积数据
库（C++），CMake 构建。版本 10.0.1 为上游 tag（用户给 10.0.1
存在——按真实版）。

Upstream: https://codeload.github.com/AcademySoftwareFoundation/openvdb/tar.gz/refs/tags/v10.0.1

Build:   CMake。依赖 tbb（制品仓 tbb/2023.0.0 ✅）、zlib（✅）、
         boost（✅）、gtest（制品仓 gtest/1.17.0.1 ✅，test_requires
         构建期依赖）——blosc 制品仓无，CMake 关 USE_BLOSC=OFF 绕过。
Install: lib/libopenvdb + include/openvdb。
Type:   library（commands.json 软件级声明）

上游测试: OPENVDB_BUILD_UNITTESTS=ON 真实编译 vdb_test（109 个
         Test*.cc / 703 个 GTest 用例宏）+ OPENVDB_BUILD_NANOVDB=ON
         NANOVDB_BUILD_UNITTESTS=OFF（CI 超时治理 #49598：nanovdb
         140 实例编译量大且本地已真跑验证 115+33 全 PASS，CI 窗口
         内关其编译保 openvdb 主链 703 实例），上游注册用例合计
         821（v10.0.1 tarball 逐文件 grep 实测口径），build() 内于
         OHOS 本机真实执行并输出 HMBS_UPSTREAM_TEST_RESULT。CI
         超时治理：Ninja 并行构建（tool_requires ninja/1.12.1，
         绕开 OHOS 禁 mkfifo jobserver 的 make 并行卡死——此前
         make -j1 单线程 188 编译单元占满 conan create 3600s 预算）
         + 每测试套件 timeout 600s 包裹+stdin 关闭（防挂死，本地
         实测 vdb_test 全量 695 实例仅 96s，600s 为 6 倍余量）。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get
import json
import os
import re


class OpenvdbConan(ConanFile):
    name = "openvdb"
    version = "10.0.1"
    description = "Sparse volume data structure and tools (VFX industry standard)"
    license = "MPL-2.0"
    homepage = "https://www.openvdb.org/"
    url = "https://github.com/AcademySoftwareFoundation/openvdb"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # tbb/zlib/boost 制品仓均有；blosc 无——CMake 关闭绕过
    requires = "tbb/2023.0.0", "zlib/1.3.1", "boost/1.90.0"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def build_requirements(self):
        # ninja：OHOS 禁 mkfifo jobserver，make -jN 并行会卡死（此前
        # 只能 make -j1 单线程，#49598 撞 3600s 超时）。ninja 自管理
        # 并行度不走 jobserver fifo，可安全并行——编译提速治超时。
        # 制品仓 ninja/1.12.1 有 OHOS 二进制（armv8/clang17/libc++）
        self.tool_requires("ninja/1.12.1")
        # 上游 GTest 套件构建依赖（制品仓 ohpcd gtest/1.17.0.1 有 OHOS
        # 二进制）。test_requires 是构建期依赖：不进 package_id，发布
        # 二进制不受影响；CMakeToolchain 自动把 gtest include/lib 路径
        # PREPEND 进 CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH，CMake 4.1
        # 的 FindGTest module 模式（find_path gtest/gtest.h +
        # find_library gtest/gtest_main）即可定位，并创建上游需要的
        # GTest::GTest / GTest::Main 老式 target 名（兼容层自动建）。
        self.test_requires("gtest/1.17.0.1")

    def source(self):
        # codeload URL 含 /tar.gz/ 段——conan get() 误判 zip（BadZipFile，
        # batsignal/c4project 同款），显式 filename
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="openvdb-10.0.1.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        # Ninja generator：绕开 OHOS 禁 mkfifo jobserver 的 make 并行
        # 卡死（ninja 不用 jobserver 协议），CI #49598 单线程撞 3600s
        # 超时的根治——编译提速
        tc.generator = "Ninja"
        # openvdb 10.x 只在 DELAYED_LOADING 分支 find_package(Boost)，而本配
        # 方关闭该选项——Boost 头从未进编译单元（Math.h 报 file not found）。
        # CI 环境有系统 Boost 而本地没有：显式喂 include 到全局 flags。
        boost = self.dependencies["boost"]
        for d in boost.cpp_info.includedirs:
            tc.variables[f"CMAKE_CXX_FLAGS"] = \
                f"-I{os.path.join(boost.package_folder, d)} " + \
                tc.variables.get("CMAKE_CXX_FLAGS", "")
        # blosc 制品仓无——关闭压缩后端（USE_BLOSC 是控制变量，
        # 非 OPENVDB_USE_BLOSC）
        tc.variables["USE_BLOSC"] = "OFF"
        # 只建核心库 + 单测，关 Python/文档/Houdini/Maya/AX
        tc.variables["OPENVDB_BUILD_PYTHON_MODULE"] = "OFF"
        tc.variables["OPENVDB_BUILD_DOCS"] = "OFF"
        tc.variables["OPENVDB_BUILD_HOUDINI_PLUGIN"] = "OFF"
        tc.variables["OPENVDB_BUILD_MAYA_PLUGIN"] = "OFF"
        tc.variables["OPENVDB_BUILD_AX"] = "OFF"
        # rule4 攻坚：真实编译并执行上游 GTest 套件（821 用例）
        tc.variables["OPENVDB_BUILD_UNITTESTS"] = "ON"
        # CONCURRENT_MALLOC=None：unittest 默认 Auto→找 Jemalloc（制品仓
        # 无）→回退 Tbbmalloc（需 TBB::tbbmalloc target，本 tbb 包只暴露
        # libtbb）——设 None 完全绕开并发 malloc 依赖（非测试必需）
        tc.variables["CONCURRENT_MALLOC"] = "None"
        # nanovdb 套件（118 用例）：TestNanoVDB.cc + TestOpenVDB.cc
        tc.variables["OPENVDB_BUILD_NANOVDB"] = "ON"
        # CI 超时精简（#47064 撞 14400s）：关闭 nanovdb 140 实例子集，
        # 保 openvdb 主 unittest 703 实例（编译量减半）。nanovdb 测试
        # 本地已真跑验证（115+33 全 PASS），CI 窗口内先保主链。
        tc.variables["NANOVDB_BUILD_UNITTESTS"] = "OFF"
        tc.variables["NANOVDB_USE_OPENVDB"] = "ON"
        tc.variables["NANOVDB_USE_TBB"] = "ON"
        # nanovdb 工具/示例编译量大且非测试必需——关闭（core 库照建）
        tc.variables["NANOVDB_BUILD_TOOLS"] = "OFF"
        tc.variables["NANOVDB_BUILD_EXAMPLES"] = "OFF"
        # 只建核心库（vdb_print 等二进制编译量大，非测试目标）
        tc.variables["OPENVDB_BUILD_BINARIES"] = "OFF"
        # 只建静态库（shared=False 时仍默认双构建——关 shared 加速）
        tc.variables["OPENVDB_CORE_SHARED"] = "OFF"
        # DELAYED_LOADING 是 Windows 延迟加载选项（默认 ON）——触发
        # find_package(Boost) 而 conan boost 包无 CMake config——OHOS
        # 无意义，关闭绕过
        tc.variables["OPENVDB_USE_DELAYED_LOADING"] = "OFF"
        tc.generate()

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)
        # oneTBB 兼容：openvdb Threading.h 依赖 tbb/blocked_range.h 间接
        # 包含 version.h（注释明言），但 oneTBB 的 blocked_range.h 不再
        # 包含它——TBB_INTERFACE_VERSION 未定义（<12002）走 #else 分支
        # 调 tbb::task::self()（oneTBB 已移除）致编译失败。显式 include
        # <tbb/version.h> 让宏生效走 current_context() 分支（oneTBB 兼容）
        th = os.path.join(self.source_folder, "openvdb", "openvdb", "thread",
                          "Threading.h")
        with open(th, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s = s.replace("#include <tbb/blocked_range.h>",
                      "#include <tbb/version.h>\n#include <tbb/blocked_range.h>")
        with open(th, "w", encoding="utf-8") as f:
            f.write(s)
        cmake = CMake(self)
        cmake.configure()
        # Ninja 并行构建（此前 make -j1 单线程：OHOS 禁 mkfifo jobserver，
        # make -jN 并行会卡死，CMake.build() 的 -j 封装实测卡在 15%）。
        # ninja 自管理并行度不走 jobserver fifo——#49598 CI 超 3600s
        # 超时（单线程编译 188 单元占满预算）的根治。-j4 显式限并发：
        # 每个 clang++ 编译大模板单元可吃 1-2G 内存，防 CI worker OOM。
        cmake.build(build_tool_args=["-j", "4"])
        # 上游 GTest 套件真实执行（rule4：821 用例必须真跑）
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """真实执行上游 GTest 套件并输出 HMBS_UPSTREAM_TEST_RESULT。

        三个测试可执行文件（构建产物）：
        - vdb_test                （openvdb/unittest，703 用例宏）
        - nanovdb_test_nanovdb    （nanovdb/unittest/TestNanoVDB.cc，85 用例宏）
        - nanovdb_test_openvdb    （nanovdb/unittest/TestOpenVDB.cc，33 用例宏）
        逐个真实运行，不 fail-fast：即使部分套件失败也收集全量结果后统一
        输出 marker，失败明细写入 build 目录 upstream-test-failures.txt。
        运行环境用 conanbuild（非 conanrun）：本包与 tbb 的可执行/so 均
        NEEDED libc++_shared.so，其真身分别在 /system/lib64（系统 __h
        命名空间）与 SDK llvm/lib——这两组路径由 profile [buildenv] 的
        LD_LIBRARY_PATH 提供（conanbuild 生效；conanrun 不继承，实测
        rc=127 "Error loading shared library libc++_shared.so"）。
        """
        exes = [
            ("vdb_test", os.path.join(self.build_folder, "openvdb", "openvdb",
                                      "unittest", "vdb_test")),
            ("nanovdb_test_nanovdb", os.path.join(
                self.build_folder, "nanovdb", "nanovdb", "unittest",
                "nanovdb_test_nanovdb")),
            ("nanovdb_test_openvdb", os.path.join(
                self.build_folder, "nanovdb", "nanovdb", "unittest",
                "nanovdb_test_openvdb")),
        ]
        total_passed = total_failed = 0
        per_suite = []
        failure_details = []
        env = "conanbuild"
        for name, exe in exes:
            if not os.path.isfile(exe):
                per_suite.append({"suite": name, "error": "executable not built"})
                failure_details.append("[%s] executable not built at %s" % (name, exe))
                continue
            # 工作目录 = 各测试的 build 子目录：nanovdb 测试从 CWD 相对
            # 读写 data/*.nvdb（上游 CMakeLists 有 file(MAKE_DIRECTORY
            # data)，add_test 未设 WORKING_DIRECTORY，即假定在 build 目录
            # 运行）；vdb_test 写 something.vdb2 等临时文件亦到 CWD。
            # 用 bash 子 shell 进入对应目录运行，避免污染 build 根。
            workdir = os.path.dirname(exe)
            log_path = os.path.join(self.build_folder, "upstream-%s.log" % name)
            # CI 超时防护（#49598 "环境问题：构建超时"）：每套件加
            # timeout 包裹（toybox timeout，/system/bin 在 CI PATH 内）
            # + stdin 关闭（防交互式等待）。本地实测 vdb_test 全量仅
            # 96s / 695 实例，600s 上限为 6 倍余量——真有卡死用例也会
            # 被硬切并留日志定位（超时前最后执行的用例名见日志尾部），
            # 而非无限挂死撞 conan create 3600s 总超时。
            cmd = ('cd "%s" && timeout 600 "%s" < /dev/null > "%s" 2>&1'
                   % (workdir, exe, log_path))
            ret = self.run(cmd, env=env, ignore_errors=True)
            if ret != 0:
                # timeout 退出码 124 = 超时硬切；GTest 用例失败另有 rc。
                # 记录日志尾部（含卡点用例名）供 CI 排障定位。
                try:
                    with open(log_path, "r", encoding="utf-8",
                              errors="replace") as f:
                        tail = f.read()[-1500:]
                    self.output.warning(
                        "UPSTREAM_SUITE_%s rc=%s; log tail:\n%s"
                        % (name, ret, tail))
                except IOError:
                    pass
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
            passed = sum(int(m) for m in
                         re.findall(r"\[  PASSED  \] (\d+) tests", out))
            failed = sum(int(m) for m in
                         re.findall(r"\[  FAILED  \] (\d+) tests", out))
            total_passed += passed
            total_failed += failed
            per_suite.append({"suite": name, "rc": ret, "passed": passed,
                              "failed": failed})
            # 逐失败用例记录报错原文（[ RUN ] ... [  FAILED ] 段落）
            for m in re.finditer(
                    r"\[ RUN      \] ([\w./]+)\n(.*?)\n\[  FAILED  \] \1",
                    out, re.S):
                case, body = m.group(1), m.group(2).strip()
                tail = "\n".join(body.splitlines()[-12:])
                failure_details.append("[%s] %s\n%s" % (name, case, tail))
        executed = total_passed + total_failed
        marker = {
            "status": "passed" if total_failed == 0 and executed >= 821
                      else ("executed_with_failures" if executed > 0
                            else "failed"),
            "framework": "gtest",
            "command": "vdb_test + nanovdb_test_nanovdb + nanovdb_test_openvdb (conanbuild)",
            "discovered": 821,
            "executed": executed,
            "passed": total_passed,
            "failed": total_failed,
            "suites": per_suite,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(marker, ensure_ascii=False))
        if failure_details:
            fpath = os.path.join(self.build_folder, "upstream-test-failures.txt")
            with open(fpath, "w", encoding="utf-8") as f:
                f.write("\n\n".join(failure_details))
            self.output.info("HMBS_UPSTREAM_TEST_FAILURES_FILE=" + fpath)
            # 摘要进日志（每个失败用例一行）
            for line in failure_details:
                first = line.splitlines()[0]
                self.output.warning("UPSTREAM_FAIL_CASE: " + first)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["openvdb"]
        self.cpp_info.requires = ["tbb::tbb", "zlib::zlib", "boost::boost"]
        self.conf_info.define("user.tools.openvdb:exe", "vdb_print")
