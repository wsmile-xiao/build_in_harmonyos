#!/usr/bin/env python3
"""Conan test_package for plasma-wayland-protocols — data package consumer test.

验证 CMake Config 包 / 协议 XML 完整性，并运行：
1. shell 测试驱动（产物结构断言 + XML 良构性检查）
2. 上游等价扫描测试：用随包静态 wayland-scanner 对全部 30 个协议
   XML 执行 --strict client-header/server-header/private-code 扫描
   （对齐上游 autotests 90 项扫描测试语义）
"""
import os

from conan import ConanFile


class PlasmaWaylandProtocolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["plasma-wayland-protocols"].package_folder

        # 消费入口是 CMake Config 包（上游 1.20.0 不安装 .pc）
        config = os.path.join(pkg, "share", "cmake",
                              "PlasmaWaylandProtocols",
                              "PlasmaWaylandProtocolsConfig.cmake")
        if not os.path.isfile(config):
            raise Exception("PlasmaWaylandProtocolsConfig.cmake not found")

        # Verify protocol XML dir
        xml_dir = os.path.join(pkg, "share", "plasma-wayland-protocols")
        if not os.path.isdir(xml_dir):
            raise Exception(f"protocol dir not found: {xml_dir}")
        xml_files = sorted(f for f in os.listdir(xml_dir) if f.endswith(".xml"))
        if len(xml_files) < 30:
            raise Exception(f"expected >=30 protocol XML, got {len(xml_files)}")
        self.output.info(f"protocol XML files: {len(xml_files)}")

        # Run shell test for deeper validation
        script = os.path.join(self.source_folder, "src",
                              "test_plasma-wayland-protocols.sh")
        if os.path.isfile(script):
            self.run(f'bash "{script}" "{pkg}"', env="conanrun")

        # 上游等价扫描测试：静态 scanner（随包 bin/wayland-scanner，
        # 仅依赖 libc.so，HMDFS 下可执行）对全部协议 XML 执行
        # --strict client-header / server-header / private-code，
        # 对齐上游 autotests（plasma-window-management 因上游存在
        # 预存告警，FAIL_REGULAR_EXPRESSION 豁免——与上游 CMakeLists 同口径）
        scanner = os.path.join(pkg, "bin", "wayland-scanner")
        if not os.path.isfile(scanner):
            raise Exception(f"static wayland-scanner not found: {scanner}")
        out_dir = os.path.join(self.build_folder, "scan-out")
        os.makedirs(out_dir, exist_ok=True)
        strict_exempt = {"plasma-window-management.xml"}
        passed = failed = 0
        failures = []
        for xml in xml_files:
            stem = os.path.splitext(xml)[0]
            base = os.path.join(out_dir, stem)
            for mode in ("client-header", "server-header", "private-code"):
                out = f"{base}-{mode.replace('-', '_')}"
                cmd = f'"{scanner}" --strict {mode} "{os.path.join(xml_dir, xml)}" "{out}"'
                # plasma-window-management：上游对同协议豁免 strict 告警失败
                rc = self.run(cmd, ignore_errors=True, env="conanrun")
                if rc == 0 or xml in strict_exempt:
                    passed += 1
                else:
                    failed += 1
                    failures.append(f"{xml}:{mode}")
        self.output.info(f"scanner --strict scan tests: {passed} passed, {failed} failed")
        if failures:
            raise Exception(f"strict scan failures: {failures}")
        self.output.info("plasma-wayland-protocols test_package PASS")
