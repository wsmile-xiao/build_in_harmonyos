#!/usr/bin/env python3
"""Conan recipe — daps 3.3.2-cleaned1 (DocBook Authoring and Publishing Suite)

daps 是 SUSE 的 DocBook 文档发布工具套件：bash 脚本套件（bin/daps 主程序 +
lib/ 下 bash 函数库）+ 94 个 XSLT 样式表 + XML 配置 + 少量 python 辅助工具，
通过 autotools 构建安装，无 C/C++ 编译产物。

路径 A 基础适配。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class DapsConan(ConanFile):
    name = "daps"
    version = "3.3.2-cleaned1"
    description = "daps — DocBook Authoring and Publishing Suite（文档发布工具套件）"
    license = "MIT"
    homepage = "https://github.com/openSUSE/daps"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # daps 的 Makefile 是 in-source 设计（etc/config.in 等相对路径），
        # 不能在独立 build 目录 out-of-source 构建
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # in-source 构建：configure + make 都在源码目录执行
        self.run("chmod +x configure install-sh missing", env="conanbuild")
        self.run(
            f"./configure --prefix={self.package_folder} "
            f"--disable-edit-rootcatalog",
            env="conanbuild",
        )
        self.run("make -j1", env="conanbuild")

    def package(self):
        # prefix 已指向 package_folder，直接 make install
        self.run("make install", env="conanbuild")
        # 脚本 shebang 处理：上游脚本 #!/bin/bash，OHOS 上 bash 位于
        # /data/service/hnp/bin/bash（无 /bin/bash 链接，bash_unit 先例同路径）
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for f in os.listdir(bindir):
                p = os.path.join(bindir, f)
                if os.path.isfile(p) and not os.path.islink(p):
                    with open(p, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                    if content.startswith("#!/bin/bash"):
                        content = content.replace("#!/bin/bash",
                                                  "#!/data/service/hnp/bin/bash", 1)
                        with open(p, "w", encoding="utf-8") as fh:
                            fh.write(content)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
