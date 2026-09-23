#!/usr/bin/env python3
"""Conan recipe for boot-info-script 0.78.

boot-info-script 是 Boot-Repair 生态的纯 bash 脚本工具，用于收集系统启动
环境信息（bootloader/分区/内核模块等）并生成报告。上游仅提供一个
bootinfoscript 脚本（#!/bin/bash），无 C/C++ 编译、无测试套件。

OHOS 适配:
- 纯 bash 脚本类（CI 能力矩阵: bash 脚本类 ✅ 正常；同 acme.sh 先例）；
- build() 无编译动作；
- package() 将 bootinfoscript 装入 libexec/boot-info-script/，并在 bin/ 下
  生成 wrapper（#!/usr/bin/env sh）以规避 OHOS 无 /bin/bash 的 shebang
  问题——wrapper 通过 command -v bash 定位真实 bash（fallback 到
  /data/service/hnp/bin/bash）后显式执行主脚本；
- 测试: test_package 校验 wrapper、PATH 调用、版本输出与帮助输出（同
  acme.sh 测试范式，覆盖上游缺失的测试）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class BootInfoScriptConan(ConanFile):
    name = "boot-info-script"
    version = "0.78"
    description = "Inspect boot environment and generate a boot info report"
    license = "MIT"
    homepage = "https://github.com/arvidjaar/bootinfoscript"
    url = "https://github.com/arvidjaar/bootinfoscript"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        libexec = os.path.join(self.package_folder, "libexec", "boot-info-script")
        bindir = os.path.join(self.package_folder, "bin")
        licenses_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(libexec, exist_ok=True)
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(licenses_dir, exist_ok=True)

        copy(self, "bootinfoscript", src=self.source_folder, dst=libexec, keep_path=False)
        os.chmod(os.path.join(libexec, "bootinfoscript"), 0o755)

        # 上游无独立 LICENSE 文件——许可文本（MIT）内嵌于 bootinfoscript 头部
        # （Copyright (c) 2009-2018 ... Permission is hereby granted ...），
        # 提取为标准 LICENSE 文件作为正式许可载体（替代 README 兜底）。
        script_path = os.path.join(libexec, "bootinfoscript")
        mit_lines = []
        in_mit = False
        with open(script_path, encoding="utf-8", errors="replace") as f:
            for raw in f:
                stripped = raw.strip("# \r\n")
                if stripped.startswith("Copyright") and not in_mit:
                    in_mit = True
                if in_mit:
                    mit_lines.append(stripped)
                    if "IN THE SOFTWARE" in stripped:
                        break
        if mit_lines:
            license_path = os.path.join(licenses_dir, "LICENSE")
            with open(license_path, "w", encoding="utf-8", newline="\n") as lf:
                lf.write("\n".join(mit_lines) + "\n")

        # OHOS 无 /bin/bash（shebang 失效），wrapper 显式定位真实 bash 执行
        wrapper = os.path.join(bindir, "bootinfoscript")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/usr/bin/env sh\n")
            f.write('case "$0" in\n')
            f.write('  */*) wrapper_path=$0 ;;\n')
            f.write('  *) wrapper_path=$(command -v "$0") || exit 127 ;;\n')
            f.write('esac\n')
            f.write('script_dir=$(CDPATH= cd -- "$(dirname -- "$wrapper_path")" && pwd)\n')
            f.write('bash_path=$(command -v bash) || bash_path=/data/service/hnp/bin/bash\n')
            f.write('if [ ! -x "$bash_path" ]; then\n')
            f.write('  for cand in /data/service/hnp/bin/bash /system/bin/bash /usr/bin/bash /bin/bash; do\n')
            f.write('    if [ -x "$cand" ]; then bash_path=$cand; break; fi\n')
            f.write('  done\n')
            f.write('fi\n')
            f.write('exec "$bash_path" "$script_dir/../libexec/boot-info-script/bootinfoscript" "$@"\n')
        os.chmod(wrapper, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["libexec"]
