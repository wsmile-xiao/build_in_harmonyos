#!/usr/bin/env python3
"""Conan recipe — libhwy_test 1.3.0 (Google Highway 测试支持库 hwy_test, CMake).

本包是同一上游 tarball（google/highway 1.3.0，sha256 07b3c1ba…）内的子库
`hwy_test` 的独立打包名。上游在 CMakeLists.txt 中把它定义为一个独立库目标：

    set(HWY_TEST_SOURCES hwy/tests/hwy_gtest.h hwy/tests/test_util-inl.h
                         hwy/tests/test_util.cc  hwy/tests/test_util.h)
    add_library(hwy_test ${HWY_LIBRARY_TYPE} ${HWY_TEST_SOURCES})
    target_link_libraries(hwy_test PUBLIC hwy)

交付面（install 面）：
  * libhwy_test.a / libhwy_test.so（+ SOVERSION）
  * hwy/tests/{hwy_gtest.h,test_util.h,test_util-inl.h}
  * libhwy-test.pc（上游自带 pkg-config 模块，standalone 形态带 -DHWY_TEST_STANDALONE=1）
  * hwy 核心库与头文件 + hwy-config*.cmake：hwy_test 以 PUBLIC 方式依赖 hwy，
    消费者缺了它无法编译/链接（`hwy::hwy_test` 默认关闭）。因此本包自包含交付
    该依赖（与 archives/l/libhwy/1.3.0 同源同版本、产物二进制兼容），零外部依赖。

上游测试开关：`HWY_ENABLE_TESTS=ON` 是本包交付面的**必要条件**（上游把
`install(TARGETS hwy_test)` 与 libhwy-test.pc 都放在 `if (HWY_ENABLE_TESTS)` 内），
不是为凑数字打开的开关。`HWY_ENABLE_CONTRIB=OFF`：hwy_test 不依赖 contrib，
contrib 子库不属于本包交付面。

上游 N 清点（rule4，全部候选口径的读数与逐项归因见 notes.md）：
  * 用例口径（运行时展开，contrib 默认 ON）= HWY_EXPORT_AND_TEST_P 注册点 × 实测目标
    展开数 + TEST 用例数；本配方在 build() 里把各口径读数与被测二进制的实测展开数
    一起打成 HMBS_UPSTREAM_TEST_SURFACE 标记，供审方复核。
  * 本包交付面内只有 hwy/tests/test_util_test.cc（上游唯一直接测试 test_util 的用例），
    其余用例的测试对象是 hwy / hwy_contrib 的 SIMD 算子 → 按 NOT_RUN 记账。
"""
import glob
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibhwyTestConan(ConanFile):
    name = "libhwy_test"
    version = "1.3.0"
    description = ("Test support library of Google Highway: shared test utilities "
                   "(test_util) and the standalone GTest-compatible runner (hwy_gtest)")
    license = "Apache-2.0"
    homepage = "https://github.com/google/highway"
    url = "https://github.com/google/highway"

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

    # 交付面内唯一的上游用例（上游对 test_util 库自身的单元测试）
    _IN_SURFACE_TEST = "hwy/tests/test_util_test.cc"

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
        self.folders.build = "_build"
        self.folders.generators = "_build/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # CMake 没有 HarmonyOS 平台模块；选 Linux 分支让上游走 Linux/NEON 代码路径。
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
            # 编译器探测阶段跳过链接：部分 worker 缺 lld 需要的 libxml2 共享库。
            tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 交付面必需：install(TARGETS hwy_test) 与 libhwy-test.pc 都在 if(HWY_ENABLE_TESTS) 内
        tc.variables["HWY_ENABLE_TESTS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        # hwy_test 不依赖 contrib；contrib 子库不属于本包交付面
        tc.variables["HWY_ENABLE_CONTRIB"] = "OFF"
        tc.variables["HWY_ENABLE_EXAMPLES"] = "OFF"
        tc.variables["HWY_ENABLE_INSTALL"] = "ON"
        tc.variables["HWY_FORCE_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        # 上游自带轻量运行器，不下载 googletest（CI 沙箱无网络依赖）
        tc.variables["HWY_TEST_STANDALONE"] = "ON"
        tc.variables["HWY_WARNINGS_ARE_ERRORS"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 只构建交付面所需目标：hwy_test（及其 PUBLIC 依赖 hwy）与交付面内的上游用例
        # test_util_test；不构建 hwy/tests/、hwy/contrib/ 下其余 SIMD 用例（不在本包
        # 交付面，见 notes.md 的 N 台账）。
        cmake.build(target=["hwy", "hwy_test", "test_util_test"])
        if can_run(self):
            self._run_upstream_tests()

    # ------------------------------------------------------------------ 上游用例
    def _find_binary(self, name):
        hits = [p for p in glob.glob(os.path.join(self.build_folder, "**", name),
                                     recursive=True)
                if os.path.isfile(p) and os.access(p, os.X_OK)]
        if not hits:
            raise RuntimeError("built test binary not found: %s (build_folder=%s)"
                               % (name, self.build_folder))
        hits.sort(key=len)
        return hits[0]

    @staticmethod
    def _exec(exe, args, cwd):
        proc = subprocess.run([exe] + args, cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=1800)
        return proc.returncode, proc.stdout

    def _run_upstream_tests(self):
        """运行交付面内的上游用例 hwy/tests/test_util_test，并输出 HMBS 标记。"""
        exe = self._find_binary("test_util_test")
        out_dir = os.path.join(self.build_folder, "_upstream_test_evidence")
        os.makedirs(out_dir, exist_ok=True)

        rc_list, listed = self._exec(exe, ["--gtest_list_tests"], self.build_folder)
        names = [ln.strip() for ln in listed.splitlines() if ln.startswith("  ") and ln.strip()]
        discovered = len(names)
        rc_run, output = self._exec(exe, [], self.build_folder)
        with open(os.path.join(out_dir, "test_util_test.log"), "w", encoding="utf-8") as f:
            f.write("$ %s --gtest_list_tests\n%s\n$ %s\n%s\n" % (exe, listed, exe, output))
        # 逐字证据进构建日志（reports/conan-create.log 会被留档）
        self.output.info("HMBS_UPSTREAM_TEST_LIST=" + json.dumps(names, ensure_ascii=False))
        executed = len(re.findall(r"(?m)^=== ", output))
        # 上游 standalone 运行器在首个断言失败处 HWY_ABORT：executed 行里最后一条即失败项，
        # 未打印的注册项按未运行记账（不写成 PASS，也不把未运行算成失败）。
        ran_all = (rc_run == 0 and "Success." in output and discovered > 0
                   and executed >= discovered)
        if ran_all:
            passed, failed = discovered, 0
        else:
            passed = max(executed - 1, 0)
            failed = 1
        # 执行面计数（同一单位：上游用例数）
        upstream = {
            "status": "passed" if ran_all else "failed",
            "framework": "hwy-standalone-gtest-shim",
            "command": "%s (HWY_TEST_STANDALONE=1)" % os.path.basename(exe),
            "scope": self._IN_SURFACE_TEST,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        surface = self._upstream_surface_readings(discovered, exe)
        self.output.info("HMBS_UPSTREAM_TEST_SURFACE=" + json.dumps(surface, ensure_ascii=False))
        if upstream["status"] != "passed":
            self.output.error("upstream test failed:\n" + output[-4000:])
            raise RuntimeError("libhwy_test in-surface upstream test (test_util_test) failed")

    # ------------------------------------------------------- N 清点（rule4 候选口径）
    def _sites_of(self, rel):
        path = os.path.join(self.source_folder, rel)
        if not os.path.isfile(path):
            return None
        src = open(path, encoding="utf-8", errors="replace").read()
        return (len(re.findall(r"HWY_EXPORT_AND_TEST_P\s*\(", src)),
                len(re.findall(r"(?m)^\s*TEST\s*\(", src)))

    def _upstream_surface_readings(self, discovered_in_surface, exe):
        """清点同一 tarball 的全部候选 N 口径（本函数只做读数，不做归因结论）。"""
        readings = {"in_surface_discovered": discovered_in_surface}
        try:
            text = open(os.path.join(self.source_folder, "CMakeLists.txt"),
                        encoding="utf-8", errors="replace").read()
            base = re.search(r"set\(HWY_TEST_FILES\s*(.*?)\n\)", text, re.S).group(1).split()
            m = re.search(r"list\(APPEND HWY_TEST_FILES\s*(.*?)\n\)", text, re.S)
            contrib = m.group(1).split() if m else []
            base = [f for f in base if f.endswith(".cc")]
            contrib = [f for f in contrib if f.endswith(".cc")]

            def sites(files):
                e = t = 0
                for rel in files:
                    s = self._sites_of(rel)
                    if s:
                        e += s[0]
                        t += s[1]
                return e, t

            e_off, t_off = sites(base)
            e_on, t_on = sites(base + contrib)
            in_surface_sites = self._sites_of(self._IN_SURFACE_TEST) or (0, 0)
            mult = None
            if in_surface_sites[0] > 0:
                # 实测目标展开数 = 交付面内用例的发现数 / 该文件的导出注册点数
                mult = discovered_in_surface / float(in_surface_sites[0])
            readings.update({
                "test_source_files_hwy_tests": len(glob.glob(
                    os.path.join(self.source_folder, "hwy", "tests", "*.cc"))),
                "test_targets_contrib_off": len(base),
                "test_targets_contrib_on": len(base) + len(contrib),
                "registration_sites_contrib_off": e_off + t_off,
                "registration_sites_contrib_on": e_on + t_on,
                "target_multiplier_measured": mult,
                "expanded_cases_contrib_off": (e_off * mult + t_off) if mult else None,
                "expanded_cases_contrib_on": (e_on * mult + t_on) if mult else None,
                "in_surface_sites": {"export": in_surface_sites[0], "test": in_surface_sites[1]},
                "binary": os.path.basename(exe),
            })
        except Exception as exc:  # 读数失败不掩盖用例结论，只如实登记
            readings["error"] = repr(exc)
        return readings

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # hwy_test 以 PUBLIC 方式依赖 hwy，静态链接顺序固定为 -lhwy_test -lhwy
        # （不用 collect_libs：其返回顺序不保证，静态链接会因顺序错误报未定义符号）
        self.cpp_info.libs = ["hwy_test", "hwy"]
        self.cpp_info.set_property("cmake_file_name", "hwy")
        self.cpp_info.set_property("cmake_target_name", "hwy::hwy_test")
        self.cpp_info.set_property("pkg_config_name", "libhwy-test")
        if not self.options.shared:
            self.cpp_info.defines.append("HWY_STATIC_DEFINE")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
