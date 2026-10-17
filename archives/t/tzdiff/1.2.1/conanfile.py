#!/usr/bin/env python3
"""Conan recipe for tzdiff 1.2.1.

tzdiff 是纯 POSIX sh 脚本：以本地时间为基准，逐小时并排显示多个时区的时间。
上游只有一个 `tzdiff` 脚本 + man 页，无编译、无测试套件。

OHOS 适配（两处运行期假设在鸿蒙 PC 上不成立）：
- 上游 `cd /usr/share/zoneinfo`：鸿蒙 PC 没有展开的 Olson 目录，musl 只读
  打包格式 /etc/zoneinfo/tzdata；但 musl 接受绝对路径 TZ=<TZif 文件>。
  → 补丁让 zoneinfo 目录可由 TZDIR 覆盖、TZ 传绝对路径（参数本身是绝对路径时原样使用）；package() 从
  tzdata/2026.3（IANA TZif 数据）复制 zoneinfo 到 share/zoneinfo，
  bin/tzdiff wrapper 在 TZDIR 未设置时指向这份随包数据。
- 上游 GNU 分支用 `date --date=...`：toybox date 没有 --date 长选项，
  且 -d 不接受 ISO 'T' 分隔。→ 补丁改用 GNU/toybox 共同子集 `date -d`，
  -t 参数里的 'T' 转成空格。
补丁不含平台宏；Linux/GNU 行为不变（TZDIR 缺省仍是 /usr/share/zoneinfo）。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TzdiffConan(ConanFile):
    name = "tzdiff"
    version = "1.2.1"
    description = "Display timezone differences with localtime in CLI"
    license = "BSD-2-Clause"
    homepage = "https://github.com/belgianbeer/tzdiff"
    url = "https://github.com/belgianbeer/tzdiff"
    topics = ("timezone", "zoneinfo", "cli", "shell")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 仅在打包时复制 IANA zoneinfo 数据，不向消费者传递
        self.requires("tzdata/2026.3", visible=False)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def _tzdata_zoneinfo(self):
        root = self.dependencies["tzdata"].package_folder
        hits = glob.glob(os.path.join(root, "lib", "python*", "site-packages", "tzdata", "zoneinfo"))
        if len(hits) != 1:
            raise ConanException(f"tzdata zoneinfo not found under {root}: {hits}")
        return hits[0]

    def package(self):
        libexec = os.path.join(self.package_folder, "libexec", "tzdiff")
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "tzdiff", src=self.source_folder, dst=libexec, keep_path=False)
        os.chmod(os.path.join(libexec, "tzdiff"), 0o755)
        copy(self, "tzdiff.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        # IANA TZif 数据（去掉 Python 包装文件）
        copy(self, "*", src=self._tzdata_zoneinfo(),
             dst=os.path.join(self.package_folder, "share", "zoneinfo"),
             excludes=("*.py", "__pycache__/*", "*/__pycache__/*", "*.pyc"))

        # wrapper：解析自身真实位置 → TZDIR 缺省指向随包 zoneinfo → sh 执行主脚本
        # shebang 用 /bin/sh（与上游一致；E037：鸿蒙可能没有 /usr/bin/env）
        os.makedirs(bindir, exist_ok=True)
        wrapper = os.path.join(bindir, "tzdiff")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/bin/sh\n")
            f.write('case "$0" in\n')
            f.write('  */*) self_path=$0 ;;\n')
            f.write('  *) self_path=$(command -v -- "$0") || exit 127 ;;\n')
            f.write('esac\n')
            f.write('real_path=$(readlink -f -- "$self_path" 2>/dev/null) || real_path=$self_path\n')
            f.write('prefix=$(CDPATH= cd -- "$(dirname -- "$real_path")/.." && pwd) || exit 1\n')
            f.write(': "${TZDIR:=$prefix/share/zoneinfo}"\n')
            f.write('export TZDIR\n')
            f.write('exec sh "$prefix/libexec/tzdiff/tzdiff" "$@"\n')
        os.chmod(wrapper, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
