#!/usr/bin/env python3
"""Conan recipe — inxi 3.3.41（系统信息命令行工具）

inxi 是纯 Perl 单文件命令行工具（系统信息收集，仅标准库模块：
Cwd/Data::Dumper/File::stat/Getopt::Long/POSIX），零第三方依赖
满足 R36。无编译：直接安装 inxi 为 bin/inxi。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class InxiConan(ConanFile):
    name = "inxi"
    version = "3.3.41"
    description = "inxi — full featured system information script（纯 Perl）"
    license = "GPL-3.0-or-later"
    homepage = "https://smxi.org/docs/inxi.htm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    # OHOS profile 要求四项 settings（L0p 门禁）；纯 Perl 但需与 profile 对齐
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 Perl 脚本，无编译
        pass

    def package(self):
        src = self.source_folder
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        # shebang 用绝对路径 perl（CI 的 conanrun 不含 buildenv 的 PATH，
        # `env perl` 找不到解释器，同 markdown 先例 /data/service/hnp/bin/perl）；
        # 写新文件 + chmod（绕开 HMDFS copy 丢执行位）
        with open(os.path.join(src, "inxi"), "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("#!/usr/bin/env perl",
                                  "#!/data/service/hnp/bin/perl", 1)
        dst = os.path.join(bin_dst, "inxi")
        with open(dst, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(dst, 0o755)
        # License
        copy(self, "LICENSE.txt", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
