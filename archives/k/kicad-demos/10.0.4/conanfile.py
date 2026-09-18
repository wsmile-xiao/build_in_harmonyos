#!/usr/bin/env python3
"""Conan recipe for kicad-demos 10.0.4 (pure data package)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get


class KicadDemosConan(ConanFile):
    name = "kicad-demos"
    version = "10.0.4"
    description = ("Official KiCad demonstration projects collection: "
                   "schematics, PCB layouts, simulation and scripting examples")
    license = "GPL-3.0-only"
    homepage = "https://gitlab.com/kicad/code/kicad"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"

    # 纯数据/资源包：无编译、无链接，但保留 settings 以满足 CI L0 门禁的
    # 显式 settings 声明要求（与 linux-firmware-brcm 先例同款）。
    settings = "os", "compiler", "build_type", "arch"

    # demos 集合中各工程的静态文件清单（构建期防漂移校验）。
    # 数据来源：上游 10.0.4 tag demos/ 目录实测计数。
    _demo_dirs = {
        "cm5_minima": 107,
        "complex_hierarchy": 17,
        "ecc83": 20,
        "interf_u": 23,
        "jetson-agx-thor-baseboard": 22,
        "kit-dev-coldfire-xilinx_5213": 50,
        "microwave": 3,
        "multichannel": 15,
        "openair-max": 11,
        "pic_programmer": 13,
        "python_scripts_examples": 5,
        "royalblue54L_feather": 50,
        "simulation": 98,
        "sonde xilinx": 14,
        "stickhub": 32,
        "tiny_tapeout": 55,
        "video": 47,
        "vme-wren": 128,
    }
    _expected_total = 710  # 18 个工程目录文件总数（顶层 CMakeLists.txt 另行断言）

    _resource_dir = os.path.join("share", "kicad", "demos")

    def export_sources(self):
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯数据包无编译步骤。构建期校验上游目录清单与文件计数，防止
        # 下载内容或目录结构静默漂移（adobe-source-han-serif-cn 先例范式）。
        demos_root = os.path.join(self.source_folder, "demos")
        if not os.path.isfile(os.path.join(demos_root, "CMakeLists.txt")):
            raise ConanInvalidConfiguration(
                "kicad-demos 10.0.4 inventory drift: missing top-level demos/CMakeLists.txt"
            )
        missing = [d for d in self._demo_dirs
                   if not os.path.isdir(os.path.join(demos_root, d))]
        if missing:
            raise ConanInvalidConfiguration(
                f"kicad-demos 10.0.4 inventory drift: missing demo dirs {missing}"
            )
        total = 0
        drift = []
        for demo, expected in self._demo_dirs.items():
            root = os.path.join(demos_root, demo)
            actual = sum(len(files) for _, _, files in os.walk(root))
            if actual != expected:
                drift.append(f"{demo}: expected {expected}, got {actual}")
            total += actual
        if drift:
            raise ConanInvalidConfiguration(
                "kicad-demos 10.0.4 inventory drift: " + "; ".join(drift)
            )
        if total != self._expected_total:
            raise ConanInvalidConfiguration(
                f"kicad-demos 10.0.4 total file count {total} != {self._expected_total}"
            )

    def package(self):
        demos_root = os.path.join(self.source_folder, "demos")
        copy(self, "*", src=demos_root,
             dst=os.path.join(self.package_folder, self._resource_dir))
        # KiCad 主仓 GPLv3 LICENSE（demos 目录随主仓分发）
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.resdirs = [self._resource_dir]
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        demos_root = os.path.join(self.package_folder, self._resource_dir)
        self.runenv_info.define_path("KICAD_DEMOS_DIR", demos_root)

    def package_id(self):
        self.info.clear()
