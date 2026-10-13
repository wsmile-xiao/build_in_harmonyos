#!/usr/bin/env python3
"""Conan test_package — cllayerinfo 2.3.3（消费者视角）

被测物是命令行工具 bin/cllayerinfo，因此消费者测试必须**真实执行该二进制**并断言其
输出，而不是链接某个库（R34 / 规则 12：禁止空壳断言）。

用例设计复刻上游 tests/testsuite-standard.at:103 的
"AT_SETUP([Our dummy layer through cllayerinfo])"：上游用自带的 libdummylayer.so
经 OPENCL_LAYERS 让 cllayerinfo 打印层信息，同时用 OCL_ICD_VENDORS 提供 dummy ICD。
这里在消费者侧独立编译这两件等价物：

  test_layer.c -> libtestlayer.so   dummy OpenCL 层（clGetLayerInfo / clInitLayer）
  test_icd.c   -> libtesticd.so     dummy OpenCL ICD，写成 vendors/dummy.icd

为什么 ICD 不可省：ocl_icd_loader.c 的 __initClIcd 里
    if (_num_icds == 0) { goto abort; }   /* 没有可用 ICD 就直接返回 */
    __initLayers();                       /* 这里才去读 OPENCL_LAYERS */
即「没有 ICD 就没有层」，单给 OPENCL_LAYERS 是无效的。

三条用例（与 MANIFEST.yml 的 assertion_count 对应）：
  1. 无 ICD、无层      → 工具应正常退出（退出码 0）：二进制可执行、初始化路径健壮；
  2. 有 ICD、无层      → 输出不得出现任何层信息：证明断言不是恒真；
  3. 有 ICD、有 dummy 层 → 输出必须含 CL_LAYER_API_VERSION: 100 与
                          CL_LAYER_NAME: dummylayer：证明工具真的驱动了层枚举协议。
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ClLayerInfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 仅测试期需要：消费者侧 dummy 层与 dummy ICD 要用 CL 头文件
        # （被测包本身不依赖它）
        self.requires("opencl-headers/2026.05.29")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return

        tool = os.path.join(
            self.dependencies[self.tested_reference_str].cpp_info.bindir,
            "cllayerinfo")
        if not os.path.isfile(tool):
            raise ConanException(f"被测二进制不存在：{tool}")

        layer = self._find_lib("libtestlayer")
        vendors = self._make_vendor_dir()
        absent = os.path.join(self.build_folder, "no-such-layer.so")
        cases = []

        # 用例 1：无 ICD、无层 → 仍应正常退出（退出码 0），且不得打印层信息。
        # 注意 ConanFile.run() 的 env 参数只接受环境名列表，故这里用命令内联的
        # POSIX 环境变量前缀指定 OPENCL_LAYERS / OCL_ICD_VENDORS。
        out_no_icd = self._run_tool(tool, None, absent, "cllayerinfo-no-icd.out")
        cases.append({
            "case": "no_icd_no_layer_exit0",
            "expected_exit": 0,
            "passed": "CL_LAYER_NAME" not in out_no_icd,
        })

        # 用例 2：有 dummy ICD、无层 → 不得打印层信息
        out_icd_only = self._run_tool(tool, vendors, absent, "cllayerinfo-icd-only.out")
        if "CL_LAYER_NAME" in out_icd_only:
            raise ConanException(
                "未配置任何层却打印了层信息，断言失去意义：\n" + out_icd_only)
        cases.append({"case": "icd_without_layer_prints_nothing",
                      "expected": "输出不含 CL_LAYER_NAME",
                      "passed": "CL_LAYER_NAME" not in out_icd_only})

        # 用例 3：dummy ICD + dummy 层 → 必须打印该层的 API 版本与名字
        output = self._run_tool(tool, vendors, layer, "cllayerinfo-with-layer.out")
        self.output.info(f"cllayerinfo 输出（dummy 层）:\n{output}")

        expected = ["CL_LAYER_API_VERSION: 100", "CL_LAYER_NAME: dummylayer"]
        missing = [item for item in expected if item not in output]
        if missing:
            raise ConanException(
                "cllayerinfo 未按层协议打印期望内容，缺：" + ", ".join(missing)
                + f"\n实际输出:\n{output}")
        cases.append({"case": "enumerate_dummy_layer", "expected": expected,
                      "passed": not missing})

        passed = sum(1 for c in cases if c["passed"])
        marker = {
            "executed": True,
            "passed": passed == len(cases),
            "command": f'{tool} (OCL_ICD_VENDORS={vendors}, OPENCL_LAYERS={layer})',
            "discovered": len(cases),
            "passedCount": passed,
            "cases": [c["case"] for c in cases],
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))

    def _run_tool(self, tool, vendors, layers, out_name):
        """执行被测二进制并把 stdout/stderr 一并捕获，返回输出文本。"""
        out_file = os.path.join(self.build_folder, out_name)
        self.run(f'OCL_ICD_VENDORS="{vendors}" OPENCL_LAYERS="{layers}" '
                 f'"{tool}" > "{out_file}" 2>&1')
        with open(out_file, encoding="utf-8", errors="replace") as fh:
            return fh.read()

    def _make_vendor_dir(self):
        """生成 vendors 目录：dummy.icd 的首行是 dummy ICD 库的绝对路径。"""
        icd = self._find_lib("libtesticd")
        vendor_dir = os.path.join(self.build_folder, "vendors")
        os.makedirs(vendor_dir, exist_ok=True)
        with open(os.path.join(vendor_dir, "dummy.icd"), "w", encoding="utf-8") as fh:
            fh.write(icd + "\n")
        self.output.info(f"OCL_ICD_VENDORS 目录：{vendor_dir} -> {icd}")
        return vendor_dir

    def _find_lib(self, stem):
        """按名字定位消费者侧编译出的 MODULE 库，不猜 CMake 输出目录。"""
        for root, _dirs, files in os.walk(self.build_folder):
            for name in files:
                if name.startswith(stem) and name.endswith(".so"):
                    return os.path.join(root, name)
        raise ConanException(f"消费者侧 {stem}.so 未构建成功")
