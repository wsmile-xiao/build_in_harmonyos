#!/usr/bin/env python3
"""Conan recipe for mrename 1.2 — mass rename shell utility."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# bin/mrename 包装脚本：解析自身真实路径，把 libexec 目录前置到 PATH
# （上游 mrename 通过 `find -exec mcpmv` 以 execvp 语义查找辅助脚本，
# 必须能在 PATH 中找到 mcpmv），再 exec 真实脚本。包可安装到任意前缀。
_WRAPPER = """#!/usr/bin/env sh
case "$0" in
  */*) wrapper_path=$0 ;;
  *) wrapper_path=$(command -v "$0") || exit 127 ;;
esac
script_dir=$(CDPATH= cd -- "$(dirname -- "$wrapper_path")" && pwd)
libexec_dir=$script_dir/../libexec/mrename
PATH=$libexec_dir:$PATH
export PATH
exec "$libexec_dir/mrename" "$@"
"""


class MrenameConan(ConanFile):
    name = "mrename"
    version = "1.2"
    description = ("Mass rename utility: batch copy or move files adding a "
                   "prefix and a progressive number to each filename")
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/mrename"
    url = ""
    topics = ("rename", "batch", "cli", "shell")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mrename targets POSIX systems only, got os={self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 纯 POSIX shell 脚本，无编译步骤。
        pass

    def package(self):
        libexec = os.path.join(self.package_folder, "libexec", "mrename")
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(libexec, exist_ok=True)
        os.makedirs(bindir, exist_ok=True)

        for script in ("mrename", "mcpmv"):
            copy(self, script, src=self.source_folder, dst=libexec,
                 keep_path=False)
            os.chmod(os.path.join(libexec, script), 0o755)

        # 上游未随源码分发独立的 LICENSE 文件，许可证声明位于 README 正文。
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        wrapper = os.path.join(bindir, "mrename")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_WRAPPER)
        os.chmod(wrapper, 0o755)

    def package_id(self):
        # 产物只有解释型脚本，与编译器/架构无关。
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["libexec"]
