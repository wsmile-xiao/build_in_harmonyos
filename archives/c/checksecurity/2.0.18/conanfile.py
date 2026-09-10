#!/usr/bin/env python3
"""Conan recipe for checksecurity 2.0.18 on HarmonyOS PC.

checksecurity 是 Debian 的系统安全检查脚本集（Perl + shell，无 C/C++
编译过程）。主脚本 bin/checksecurity（perl）驱动 /usr/share/checksecurity
下的 check-* 插件，读取 /etc/checksecurity.conf 配置后逐项检查系统安全
状态（磁盘占用/空口令/SUID 变化/开放 socket 等）。本配方将其打包为
conan application：安装脚本、插件、配置样例与 man 手册页。

OHOS 适配点：
- shebang 修复：#!/usr/bin/perl → #!/usr/bin/env perl（OHOS 无
  /usr/bin/perl，perl 5.42 由制品仓提供，经 PATH 解析）。
- 纯脚本包无编译，build() 仅应用补丁。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class ChecksecurityConan(ConanFile):
    name = "checksecurity"
    version = "2.0.18"
    package_type = "application"
    license = "GPL-2.0"
    homepage = "https://salsa.debian.org/debian/checksecurity"
    url = "https://salsa.debian.org/debian/checksecurity"
    description = "Debian system security check scripts (Perl/shell)"
    topics = ("security", "check", "debian", "perl")
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯脚本包无编译，仅应用 shebang 补丁
        apply_conandata_patches(self)

    def package(self):
        # 主脚本 → bin/
        copy(self, "checksecurity",
             src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        # 检查插件 → share/checksecurity/
        copy(self, "check-*",
             src=os.path.join(self.source_folder, "plugins"),
             dst=os.path.join(self.package_folder, "share", "checksecurity"))
        # 配置样例 → etc/checksecurity/
        copy(self, "*.conf",
             src=os.path.join(self.source_folder, "etc"),
             dst=os.path.join(self.package_folder, "etc", "checksecurity"))
        # man 手册页 → share/man/man8/
        copy(self, "*.8",
             src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.conf_info.define("user.checksecurity:exe",
                              os.path.join(self.package_folder, "bin", "checksecurity"))