#!/usr/bin/env python3
"""Conan recipe for conmux 0.12.0 — Console Multiplexor (pure-Perl application).

Source: autotest official GitHub repo, conmux subdirectory (R39 合规官方源).
Build: make install BUILD=<staging> — pure copy install, no compilation.
Runtime deps: perl (core), IO::Multiplex (perl-io-multiplex), URI::Escape (perl-uri).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


def _fix_shebang(path: str) -> None:
    """E049: conmux 脚本 shebang 硬编码 /usr/bin/perl，设备 perl 在
    /data/service/hnp/bin/perl —— 改为 /usr/bin/env 可移植解析。"""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    replaced = content.replace("#!/usr/bin/perl", "#!/usr/bin/env perl", 1)
    if replaced != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(replaced)
        os.chmod(path, 0o755)


class ConmuxConan(ConanFile):
    name = "conmux"
    version = "0.12.0"
    description = ("Console Multiplexor — 串口/控制台复用器（纯 Perl 应用，"
                   "IBM autotest 项目 conmux 子目录）")
    license = "GPL-2.0"
    homepage = "https://github.com/autotest/autotest"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # conmux 脚本运行时依赖 IO::Multiplex 与 URI::Escape（perl 模块）
        self.requires("perl-io-multiplex/1.16")
        self.requires("perl-uri/5.35")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # conmux 是 autotest 仓库的 conmux 子目录——将子目录内容提升到源码根。
        # 注意子目录内有个同名文件 conmux，须先整体改名避免 copy 路径冲突。
        conmux_sub = os.path.join(self.source_folder, "conmux")
        if os.path.isdir(conmux_sub):
            tmp = os.path.join(self.source_folder, ".conmux-sub")
            os.rename(conmux_sub, tmp)
            for item in os.listdir(tmp):
                src = os.path.join(tmp, item)
                dst = os.path.join(self.source_folder, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
            shutil.rmtree(tmp)
        apply_conandata_patches(self)

    def build(self):
        # 纯拷贝安装（Makefile 无编译目标）；BUILD=<staging> 前缀隔离
        staging = os.path.join(self.build_folder, "conmux-stage")
        self.run(f'make install BUILD="{staging}"', cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.build_folder, "conmux-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"conmux staging missing: {staging}")
        for root, _dirs, files in os.walk(staging):
            for f in files:
                src = os.path.join(root, f)
                rel = os.path.relpath(src, staging)
                dst = os.path.join(self.package_folder, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
        # 校验核心产物存在
        for required in ["usr/local/conmux/sbin/conmux",
                         "usr/local/conmux/sbin/conmux-registry",
                         "usr/local/conmux/bin/console",
                         "usr/local/conmux/bin/conmux-attach",
                         "usr/local/conmux/lib/Conmux.pm"]:
            if not os.path.isfile(os.path.join(self.package_folder, required)):
                raise ConanException(f"missing product: {required}")
        # E049: 修正脚本 shebang（#!/usr/bin/perl → /usr/bin/env perl）
        for sub in ("sbin", "bin"):
            d = os.path.join(self.package_folder, "usr", "local",
                             "conmux", sub)
            if os.path.isdir(d):
                for f in os.listdir(d):
                    p = os.path.join(d, f)
                    if os.path.isfile(p):
                        _fix_shebang(p)

    def package_info(self):
        # 可执行脚本在 bin/ 与 sbin/（commands.json 按 tool 类型声明）
        self.cpp_info.bindirs = [
            "usr/local/conmux/bin", "usr/local/conmux/sbin"]
        self.cpp_info.libdirs = []
