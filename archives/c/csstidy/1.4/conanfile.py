#!/usr/bin/env python3
"""Conan recipe — csstidy 1.4 (C++ CLI, direct compile, no build system).

CSSTidy 解析并优化 CSS，官方 C++ 稳定版以单可执行 CLI 形式分发
（14 个 .cpp 平铺在源码包 csstidy/ 子目录，无 configure/make，
FreeBSD ports 以 `c++ *.cpp -o csstidy` 直接编译）。
产物是命令行工具，非库：R38 → 软件级 commands.json 声明。
"""
import os
import zipfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import download, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CsstidyConan(ConanFile):
    name = "csstidy"
    version = "1.4"
    description = "CSSTidy — CSS parser and optimiser (command-line tool)"
    license = "GPL-2.0-or-later"
    homepage = "https://csstidy.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"csstidy supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def _extract_official_zip(self, archive, dest):
        """容错解压官方 zip。

        官方 csstidy-source-1.4.zip 的 central directory 以反斜杠
        （'csstidy\\xxx.cpp'）记录条目名，而 local file header 用正斜杠
        （'csstidy/xxx.cpp'）。Python 3.11.4+ zipfile 严格校验会拒绝读取，
        conan tools.unzip 则会静默丢弃这些条目（实测仅解出 9 个根文件、
        全部 csstidy/*.cpp 丢失，构建必然失败）。这里逐条按规范化名解出，
        内容与官方归档逐字节一致（已对 42 个文件做 SHA-256 比对验证）。
        """
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                name = info.filename.replace("\\", "/")
                # 以重建的 ZipInfo 打开：避免 zipfile 对 central/local 名称
                # 不一致的严格检查（直接 zf.read(info.filename) 会被拒）
                entry = zipfile.ZipInfo(name, date_time=info.date_time)
                entry.compress_type = info.compress_type
                entry.comment = info.comment
                entry.extra = info.extra
                entry.create_system = info.create_system
                entry.create_version = info.create_version
                entry.extract_version = info.extract_version
                entry.flag_bits = info.flag_bits
                entry.volume = info.volume
                entry.internal_attr = info.internal_attr
                entry.external_attr = info.external_attr
                entry.header_offset = info.header_offset
                entry.CRC = info.CRC
                entry.compress_size = info.compress_size
                entry.file_size = info.file_size
                data = zf.open(entry).read()
                target = os.path.join(dest, *name.split("/"))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "wb") as fh:
                    fh.write(data)

    def source(self):
        # tools.download 会按 conandata sha256 校验官方归档（L0o/PF7 合规），
        # tools.get() 的 unzip 会静默丢源文件，故下载后走容错解压
        archive = os.path.join(self.source_folder, "csstidy-source-1.4.zip")
        download(self, url=self.conan_data["sources"]["url"],
                 filename=archive,
                 sha256=self.conan_data["sources"]["sha256"])
        self._extract_official_zip(archive, self.source_folder)
        os.remove(archive)

    def build(self):
        apply_conandata_patches(self)

        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict)
        cxx = comp.get("cpp", "c++") if comp else "c++"

        # 源码平铺于源码包 csstidy/ 子目录；直接编译全部 .cpp（FreeBSD 先例）
        src = os.path.join(self.source_folder, "csstidy")
        out = os.path.join(self.build_folder, "csstidy")
        self.run(f"{cxx} -O2 -fPIC -o {out} *.cpp", env="conanbuild", cwd=src)

    def package(self):
        copy(self, "csstidy", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        # CLITool：无库可链；二进制已放入 bin/
        self.output.info("csstidy is a CLI tool — no library to link")