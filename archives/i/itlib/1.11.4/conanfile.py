#!/usr/bin/env python3
"""Conan recipe — itlib 1.11.4 (header-only C++ 单头工具库集合).

itlib（github.com/iboB/itlib）是一组 std-like 单头 C++ 库：交付物为
`include/itlib/*.hpp`（32 个头，共 87 KB 归档），**0 运行依赖**
（W0-2 实查：`conan list itlib/* -r=ohpcd` = 0，本配方 requires / build_requirements 双零，
上游 CMakeLists 也只有 INTERFACE 目标、无任何 find_package 外部库）。

平台适配点（3 个补丁，全部见 conandata.yml / notes.md）：
  1. include/itlib/generator.hpp、include/itlib/transparent_umap.hpp：
     缺 `typename` 的从属类型名在 **clang 15（OHOS 工具链 15.0.4）** 下是硬错误
     （P0634R3「Down with typename!」在 clang 16 才完整落地；上游 CI 只跑
      ubuntu(gcc)/windows(msvc)/macos(AppleClang≥16)，所以看不见）。两处补
     `typename` 是严格更符合标准的写法，所有编译器等价。
  2. test/t-time_t-11.cpp：硬编码 `std::locale("en_US.UTF8")`，而 bionic + ICU74 的
     `newlocale(LC_ALL_MASK, "en_US.UTF8")` 返回 NULL（只认 `.UTF-8` 连字符形态），
     构造直接抛 `collate_byname<...>::collate_byname failed to construct`。只改 locale
     名字串为 `en_US.UTF-8`，断言与用例数一字不动。

上游测试面（R51 上游测试三步法；2026-09-27 返修按 §7.3「候选数法最大值」更正口径）：
  * **N（上游用例总数）= 源码宏数 130**：`grep -rn "TEST_CASE(" test/` → 130
    （`test/*.cpp` 127 + `t-atomic_shared_ptr_storage.inl` 3），与框架注册数 128
    同为「测试用例数」单位故取最大值；130 → 128 差额 = −5（上游自带预处理守卫在本
    平台不成立、未编译）+3（`.inl` 的 3 个宏被 -11/-20 两个 TU 各注册一次），
    逐项归因见 `reports/test-report.md` 与 `notes.md`；N′（实跑）= 125、NOT_RUN = 5。
  * 程序口径（**不作 N**）：`t-*.cpp` ×44 + `bft-*.cpp` ×3 == `ctest -N` 注册数 47；
    断言口径 4487、消费者口径 91（分栏不进上游分母），均按「四口径不混用」单列。
  * build() 里 configure + build + ctest 实跑（层 1 必做），任一失败即 conan create 失败，
    另加「CTest 注册数必须 == 47」的硬断言（防 `ctest` 空跑假绿；该常量比的是**程序口径**，
    不是 N）。
"""
import hashlib
import os
import re

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
)


class ItlibConan(ConanFile):
    name = "itlib"
    version = "1.11.4"
    description = "itlib — a collection of std-like single-header C++ libraries"
    license = "MIT"
    homepage = "https://github.com/iboB/itlib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("header-only", "single-header", "cpp11", "containers")

    package_type = "header-library"
    implements = ["auto_header_only_mode"]

    settings = "os", "compiler", "build_type", "arch"

    # header-only：源码只读，build()/package() 直接从 source_folder 读取
    no_copy_source = True

    # 上游测试树在 build() 内实跑，期望注册数（test/t-*.cpp ×44 + test/bft-*.cpp ×3）
    EXPECTED_CTEST_ENTRIES = 47

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0-2 实查：0 运行依赖（conan list itlib/* -r=ohpcd = 0，上游无 find_package）
        pass

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # 上游 README/CMakeLists：库本体最低 C++11（t-*-11 用例族）
        # 注意本机 profile 无 `compiler` 项 ⇒ 必须走 get_safe("compiler.cppstd")，
        # 直接 self.settings.compiler.get_safe(...) 会抛 "'settings.compiler' value not defined"。
        if self.settings.get_safe("compiler.cppstd"):
            check_min_cppstd(self, 11)

    # ── 源码获取（全部走 conandata.yml ⇒ CI 的 mirror fallback + pre-download 生效）──
    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

        deps = os.path.join(self.source_folder, "_deps")
        # ① 上游 test/CMakeLists.txt 经 CPM.cmake 拉的三个包（本地解包，配置期零网络）
        for key, folder in (
            ("icm_sources", "icm-1.5.1"),
            ("doctest_util_sources", "doctest-util-0.1.2"),
            ("doctest_lib_sources", "doctest-lib-2.4.11"),
        ):
            get(self, **self.conan_data[key],
                destination=os.path.join(deps, folder), strip_root=True)

        # ② CPM.cmake 引导脚本（裸文件，不是压缩包 → 用 download + 本地 sha256 自校验）
        cpm = self.conan_data["cpm_source"]
        cpm_dir = os.path.join(deps, "cpm")
        os.makedirs(cpm_dir, exist_ok=True)
        cpm_file = os.path.join(cpm_dir, "CPM_0.35.6.cmake")
        download(self, url=cpm["url"], filename=cpm_file)
        with open(cpm_file, "rb") as fh:
            got = hashlib.sha256(fh.read()).hexdigest()
        if got != cpm["sha256"]:
            raise Exception(
                f"CPM.cmake sha256 不符: expect={cpm['sha256']} got={got} "
                f"(url={cpm['url']})")
        self.output.info(f"[source] CPM.cmake sha256 OK ({got[:16]}…)")

        # ③ 平台补丁（在 source() 内施加：conan 的 source() 每个 source 目录只跑一次，
        #    二次 conan create 不会重复 apply 导致 patch 反向失败）
        apply_conandata_patches(self)

    # ── 上游测试集成（R51 上游测试三步法）────────────────────────────────
    @staticmethod
    def _count_ctest_entries(build_folder):
        """从生成的 CTestTestfile.cmake 统计 ctest 注册项（不数源文件、不数宏）。

        CMake 生成的 CTestTestfile.cmake 用**位置参数**形态 `add_test(<name> <cmd>)`，
        不是 `add_test(NAME <name> ...)` —— 正则必须按前者取（首参即用例名）。
        """
        total = 0
        names = []
        for root, _dirs, files in os.walk(build_folder):
            if "CTestTestfile.cmake" not in files:
                continue
            with open(os.path.join(root, "CTestTestfile.cmake"),
                      encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            hits = re.findall(r'^\s*add_test\(\s*([^\s)]+)', text, flags=re.M)
            total += len(hits)
            names.extend(hits)
        return total, sorted(names)

    def generate(self):
        tc = CMakeToolchain(self)
        deps = os.path.join(self.source_folder, "_deps")
        # 上游测试树默认关（ITLIB_BUILD_TESTS 的默认值 = dev_mode = 非子目录时才 ON）；
        # 层 1 必做 ⇒ 显式打开，实跑上游 47 个 ctest 用例。
        tc.cache_variables["ITLIB_BUILD_TESTS"] = True
        # ① CPM 引导脚本：get_cpm.cmake 的 `if(CPM_SOURCE_CACHE)` 分支命中本地文件，
        #    不再 file(DOWNLOAD) 直连 GitHub（itlib 与 doctest-util 两处 get_cpm 同解）。
        tc.cache_variables["CPM_SOURCE_CACHE"] = deps
        # ② 三个 CPM 包全部用「手工 override」指向本地解包目录：
        #    CPMAddPackage 里 `CPM_<name>_SOURCE` 优先级最高（CPM.cmake 606 行），
        #    走 SOURCE_DIR 分支 ⇒ 不进 FetchContent 下载、也不进 hash 缓存目录。
        tc.cache_variables["CPM_icm_SOURCE"] = os.path.join(deps, "icm-1.5.1")
        tc.cache_variables["CPM_doctest-util_SOURCE"] = os.path.join(deps, "doctest-util-0.1.2")
        tc.cache_variables["CPM_doctest-lib_SOURCE"] = os.path.join(deps, "doctest-lib-2.4.11")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # ── 反假绿硬断言：ctest 注册项必须等于程序口径清点的 47 ──────────
        # （"跑了多少" 与 "应该跑多少" 分开判：ctest rc=0 也可能 0 个用例；
        #  47 = 44 个 doctest 可执行 + 3 个 build-failure，是**程序口径**，
        #  不是 §7.3 的上游用例 N=130 —— 见 docstring 与 notes.md）
        n, names = self._count_ctest_entries(self.build_folder)
        self.output.info(f"[upstream-tests] ctest 注册项 = {n}（程序口径清点 47，"
                         f"test/t-*.cpp 44 + test/bft-*.cpp 3；上游用例 N=130 见 notes.md）")
        if n != self.EXPECTED_CTEST_ENTRIES:
            raise Exception(
                f"上游测试注册数不符: ctest={n} != 程序口径清点 47。"
                f"若 find_package(Threads) 未命中（缺线程测试 6 项）请先查该步；"
                f"已注册: {names}")

        # ── 层 1：上游官方测试 ────────────────────────────────────────
        # 沙箱 HOME（device-facts §一.11：上游测试不得写用户真实 HOME）；
        # 这里的 HOME 只作用于 ctest 子进程，不改设备环境。
        sandbox = os.path.join(self.build_folder, "test-home")
        os.makedirs(sandbox, exist_ok=True)
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = sandbox
        try:
            # 用 ctest() 而非 test()：test() 走 build target `test` 且尊重
            # tools.build:skip_test；ctest() 直接调 ctest，测试不可被 conf 静默跳过。
            cmake.ctest(cli_args=["--output-on-failure", "-j4"], env="conanbuild")
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "itlib")
        self.cpp_info.set_property("cmake_target_name", "itlib::itlib")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
