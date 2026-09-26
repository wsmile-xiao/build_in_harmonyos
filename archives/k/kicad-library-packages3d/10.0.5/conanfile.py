#!/usr/bin/env python3
"""Conan recipe for kicad-library-packages3d 10.0.5 (pure data package)."""

import hashlib
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get


class KicadLibraryPackages3dConan(ConanFile):
    name = "kicad-library-packages3d"
    version = "10.0.5"
    description = ("Official KiCad 3D model library: STEP models of electronic "
                   "components for the KiCad 3D viewer (Pcbnew and the "
                   "Footprint Editor) and MCAD integration")
    license = "CC-BY-SA-4.0"
    homepage = "https://gitlab.com/kicad/libraries/kicad-packages3D"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"

    # 纯数据/资源包：无编译、无链接，但保留 settings 以满足 CI L0 门禁的
    # 显式 settings 声明要求（与 kicad-demos 先例同款）。
    settings = "os", "compiler", "build_type", "arch"

    # 上游 10.0.5 tag 实测清单（构建期防漂移校验）。
    # 数据来源：Ubuntu/Debian 10.0.5-1 再打包归档（与上游 tag 逐文件一致）
    # 解包实测计数；再打包仅移除 1 个不参与安装的 .fcstd 源文件
    # （Button_Switch_SMD.3dshapes/SW_SPST_FSMSM.fcstd），故辅助 48 / 总 7293。
    # KiCad 10 起模型库仅含 STEP（VRML .wrl 已从上游库中移除）。
    _expected_dir_count = 105     # *.3dshapes 家族目录数
    _expected_step_count = 7245   # .step 文件总数
    _expected_aux_count = 48      # 家族目录内辅助文件（CREDITS.md 等）
    _expected_total = 7293        # 家族目录内文件总数
    # 家族目录名集合摘要（排序后逐行拼接的 sha256）：
    # 任意目录增删/改名都会破坏该摘要。
    _dir_list_sha256 = ("3be1738c87507fd83fc93b2dc95a13c0"
                        "236a4b65cdbf412a65d4139b2a49f938")
    # 代表性封装族目录在位探针（覆盖常见元件族，全集由摘要覆盖）
    _spot_dirs = [
        "Button_Switch_SMD.3dshapes",
        "Capacitor_SMD.3dshapes",
        "Connector_PinHeader_2.54mm.3dshapes",
        "Connector_USB.3dshapes",
        "Crystal.3dshapes",
        "Diode_SMD.3dshapes",
        "Inductor_SMD.3dshapes",
        "LED_SMD.3dshapes",
        "Package_BGA.3dshapes",
        "Package_DFN_QFN.3dshapes",
        "Package_QFP.3dshapes",
        "Package_SO.3dshapes",
        "Package_TO_SOT_SMD.3dshapes",
        "Resistor_SMD.3dshapes",
        "TerminalBlock_Phoenix.3dshapes",
    ]

    _resource_dir = os.path.join("share", "kicad", "3dmodels")

    def export_sources(self):
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _family_dirs(source_root):
        """source_root 下的一级 *.3dshapes 家族目录（排序稳定输出）。"""
        return sorted(
            name for name in os.listdir(source_root)
            if name.endswith(".3dshapes")
            and os.path.isdir(os.path.join(source_root, name))
        )

    def build(self):
        # 纯数据包无编译步骤。构建期校验上游目录清单与文件计数，防止
        # 下载内容或目录结构静默漂移（kicad-demos 先例范式）。
        for marker in ("CMakeLists.txt", "LICENSE.md"):
            if not os.path.isfile(os.path.join(self.source_folder, marker)):
                raise ConanInvalidConfiguration(
                    "kicad-library-packages3d 10.0.5 inventory drift: "
                    f"missing top-level {marker}"
                )
        families = self._family_dirs(self.source_folder)
        missing = [d for d in self._spot_dirs if d not in families]
        if missing:
            raise ConanInvalidConfiguration(
                "kicad-library-packages3d 10.0.5 inventory drift: "
                f"missing spot dirs {missing}"
            )
        digest = hashlib.sha256("\n".join(families).encode("utf-8")).hexdigest()
        if digest != self._dir_list_sha256:
            raise ConanInvalidConfiguration(
                "kicad-library-packages3d 10.0.5 dir-list digest "
                f"{digest} != {self._dir_list_sha256}"
            )
        if len(families) != self._expected_dir_count:
            raise ConanInvalidConfiguration(
                "kicad-library-packages3d 10.0.5 dir count drift: "
                f"{len(families)} != {self._expected_dir_count}"
            )
        step = aux = total = 0
        for family in families:
            root = os.path.join(self.source_folder, family)
            for entry in os.listdir(root):
                path = os.path.join(root, entry)
                if os.path.isdir(path):
                    raise ConanInvalidConfiguration(
                        "kicad-library-packages3d 10.0.5 inventory drift: "
                        f"nested dir inside {family}"
                    )
                total += 1
                if entry.endswith(".step"):
                    step += 1
                else:
                    aux += 1
        if step != self._expected_step_count:
            raise ConanInvalidConfiguration(
                "kicad-library-packages3d 10.0.5 .step count drift: "
                f"{step} != {self._expected_step_count}"
            )
        if aux != self._expected_aux_count:
            raise ConanInvalidConfiguration(
                "kicad-library-packages3d 10.0.5 aux file count drift: "
                f"{aux} != {self._expected_aux_count}"
            )
        if total != self._expected_total:
            raise ConanInvalidConfiguration(
                "kicad-library-packages3d 10.0.5 total file count drift: "
                f"{total} != {self._expected_total}"
            )

    def package(self):
        # 与上游 CMake install 一致：*.3dshapes 家族目录整目录安装到
        # share/kicad/3dmodels（上游 KICAD_PACKAGES_3D）。
        copy(self, "*.3dshapes/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, self._resource_dir))
        # 上游 CC-BY-SA 4.0 LICENSE（含电子设计豁免条款）
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.resdirs = [self._resource_dir]
        self.cpp_info.libs = []
        models_root = os.path.join(self.package_folder, self._resource_dir)
        self.runenv_info.define_path("KICAD3D_MODEL_DIR", models_root)

    def package_id(self):
        self.info.clear()
