#!/usr/bin/env python3
"""Conan recipe for qla-tools 20140529 — QLogic FC/iSCSI HBA admin CLI tools.

Upstream is the Debian source package `qla-tools`: it ships four pure bash
scripts with `Architecture: all` and no build system (Debian packaging only
copies the scripts into usr/sbin/):

    ql-hba-snapshot          display QLogic HBA / target / LUN details
    ql-lun-state-online      bring offline LUNs back online
    ql-set-cmd-timeout       show / modify device command timeout
    ql-dynamic-tgt-lun-disc  dynamic target-LUN discovery and rescan

There is no compilation step. package() installs each script to bin/ under its
Debian command name (upstream `ql-xxx/ql-xxx.sh` -> `bin/ql-xxx`).

Runtime dependency: sg3-utils (sg_turs / sg_map) is used by
ql-dynamic-tgt-lun-disc. The OHOS package `libsgutils/1.46` provides those
commands, so it is declared as a requirement (upstream `Depends: sg3-utils`).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# 上游脚本目录 -> 安装后的命令名（与 Debian usr/sbin/ 下名称一致）
_SCRIPTS = (
    "ql-hba-snapshot",
    "ql-lun-state-online",
    "ql-set-cmd-timeout",
    "ql-dynamic-tgt-lun-disc",
)


class QlaToolsConan(ConanFile):
    name = "qla-tools"
    version = "20140529"
    description = "QLogic FC/iSCSI HBA administration tools (snapshot, LUN scan, LUN state, command timeout)"
    license = "GPL-2.0-or-later"
    homepage = "http://driverdownloads.qlogic.com"
    url = "https://salsa.debian.org/gris/qla-tools"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: settings.os 判断必须同时接受 Linux 与 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qla-tools {self.version} only supports Linux and OHOS, got os={self.settings.os}")

    def requirements(self):
        # 上游 Debian `Depends: sg3-utils` —— ql-dynamic-tgt-lun-disc 需要 sg_turs/sg_map。
        # OHOS 侧由 libsgutils/1.46 提供这两个命令。
        self.requires("libsgutils/1.46")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 shell 脚本包：无编译阶段，仅应用 OHOS 适配补丁（不得伪造编译日志）
        apply_conandata_patches(self)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for name in _SCRIPTS:
            src = os.path.join(self.source_folder, name, name + ".sh")
            if not os.path.isfile(src):
                raise ConanException(f"upstream script not found: {src}")
            dst = os.path.join(bindir, name)
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
        # GPL-2.0 许可证文本（上游每个脚本目录各带一份 COPYING）
        copy(self, "*/COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
