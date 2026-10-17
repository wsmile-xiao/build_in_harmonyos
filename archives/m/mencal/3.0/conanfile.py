#!/usr/bin/env python3
"""Conan recipe for mencal 3.0 — menstruation calendar CLI (pure Perl).

上游形态：单文件 Perl 脚本（发行物仅 mencal + 两份许可证 + README），
无 configure/make/cmake，故 build() 只做安装树装配（G1 要求存在 def build()，
R34 禁空 stub —— 此处是真实装配逻辑，不是占位）。

shebang 适配（patches/0001-mencal.patch）：
- 设备与 CI worker 均无 /usr/bin/perl，上游 `#!/usr/bin/perl -w` 直接执行
  rc=126 "bad interpreter: No such file or directory"（本机实测）；
- 改 `#!/usr/bin/env perl`：/usr/bin/env 存在（toybox），perl 在 HNP
  `/data/service/hnp/bin/perl`（短 PATH 可得，先例 abi-compliance-checker 已 published）；
- `-w` 无法随 env shebang 保留：toybox env 不支持 -S（实测 rc=125），
  且实测去 -w 前后 stdout/stderr 行为一致，故直接去掉。

settings 保留四项（os/arch/compiler/build_type）：PF8/L0p 交叉编译矩阵前提，
本包虽无编译器参与，四项齐全才不被配方静态闸拦。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
    copy, save,
)
from conan.tools.layout import basic_layout


class MencalConan(ConanFile):
    name = "mencal"
    version = "3.0"
    description = "Mencal - menstruation calendar command-line tool (pure Perl)"
    license = "GPL-2.0-or-later"
    homepage = "https://kyberdigi.cz/projects/mencal/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # 补丁守卫：shebang 未被改写即失败，防「补丁静默不生效」假绿
        src_script = os.path.join(self.source_folder, "mencal")
        with open(src_script, "rb") as f:
            head = f.readline().decode("ascii", errors="replace").strip()
        if head != "#!/usr/bin/env perl":
            raise RuntimeError(
                f"shebang patch not applied, first line is: {head!r}")

        # 安装树装配：单文件脚本即全部产物（字节级拷贝，源为 latin-2 编码不转码）
        bin_dir = os.path.join(self.build_folder, "install", "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copyfile(src_script, os.path.join(bin_dir, "mencal"))
        os.chmod(os.path.join(bin_dir, "mencal"), 0o755)

    def package(self):
        copy(self, "mencal",
             src=os.path.join(self.build_folder, "install", "bin"),
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "LICENCE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        # R38 命令行工具：只有 bin/，无头文件无库（与真实产物一致）
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
