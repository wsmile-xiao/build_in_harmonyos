#!/usr/bin/env python3
"""Conan recipe — inxi 3.3.38-1（系统信息查看工具，纯 Perl）

inxi 是纯 Perl 单文件脚本（inxi/inxi），零第三方依赖（仅标准库模块
Cwd/Data::Dumper/File::stat/Getopt::Long/POSIX），无编译：直接安装
inxi 脚本为 bin/inxi。

上游源码包目录为 inxi/（非 inxi-<ver>/），strip_root 需处理。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class InxiConan(ConanFile):
    name = "inxi"
    version = "3.3.38-1"
    description = "inxi — full featured system information script（纯 Perl）"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/smxi/inxi"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    # OHOS profile 要求四项 settings（L0p 门禁）；纯 Perl 但需与 profile 对齐
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # 上游 tarball 顶层仅 inxi/ 目录 → strip_root=True 直接解压到 source_folder
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 Perl 脚本，无编译
        pass

    def package(self):
        src = self.source_folder
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        # inxi shebang 为 #!/usr/bin/env perl（系统 perl 在 PATH），写新文件+chmod
        # （写新文件+chmod 同时绕开 HMDFS copy 丢执行位，同 markdown 模式）
        with open(os.path.join(src, "inxi"), "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        dst = os.path.join(bin_dst, "inxi")
        with open(dst, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(dst, 0o755)
        # License
        for lic_name in ("COPYING", "LICENSE", "LICENSE.txt", "LICENSE.md"):
            lic = os.path.join(src, lic_name)
            if os.path.isfile(lic):
                copy(self, lic_name, src=src,
                     dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
