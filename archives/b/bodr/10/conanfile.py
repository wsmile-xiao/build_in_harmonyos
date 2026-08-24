#!/usr/bin/env python3
"""Conan recipe for bodr 10 — Blue Obelisk Data Repository。

BODR 是化学数据仓库（元素/同位素/晶体 XML/XSLT 数据——autotools 打包
到 share/）。OHOS 适配：configure + make install（纯数据——无编译依赖）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BodrConan(ConanFile):
    name = "bodr"
    version = "10"
    description = "Blue Obelisk Data Repository (chemical data)"
    license = "CC-BY-SA-3.0"
    homepage = "https://www.blueobelisk.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def build_requirements(self):
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 复制源码到可写目录（source_folder 的 owner 20001006——config.status
        # 的临时目录（confCEHiCB/）在源码树创建失败（Permission denied）；
        # workdir 放 ~/tmp（当前用户可写——CI 的 .cache/tmp 遗留目录 owner
        # 20001006 不可写——config.status 的 ./confplLchh/subs1.awk Permission
        # denied 根因；且须在 source_folder 外——避免 cp -r 自复制）——
        # 构建后 install 到 package）
        workdir = os.path.join(os.path.expanduser("~"), "tmp", "bodr-src-tmp")
        if os.path.isdir(workdir):
            shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(workdir, exist_ok=True)
        self.run(f'cp -r {self.source_folder}/. {workdir}/')
        # autoreconf 重新生成 configure（预生成的 configure 与 autoconf 2.72
        # 不兼容——config.status: could not setup config files machinery）
        self.run("autoreconf -fi", cwd=workdir)
        # config.status 的临时目录机制（mktemp -d "./confXXXXXX" 在 cwd——
        # OHOS HMDFS 权限模型——即使 cwd 可写也 Permission denied（实测
        # ./confBJGNaD/subs1.awk Permission denied）——patch configure/
        # config.status 的 mktemp 改 ~/tmp 可写目录（avarice 同款已验证））
        tmpd = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmpd, exist_ok=True)
        for cf in ("configure",):
            cfp = os.path.join(workdir, cf)
            if os.path.isfile(cfp):
                with open(cfp) as f:
                    cft = f.read()
                cft = cft.replace('mktemp -d "./confXXXXXX"',
                                  f'mkdir -p "{tmpd}/conf$$-$RANDOM"')
                cft = cft.replace('tmp=./conf$$-$RANDOM',
                                  f'tmp={tmpd}/conf$$-$RANDOM')
                with open(cfp, "w") as f:
                    f.write(cft)
        # configure 的 UID 检查（dist-ustar——`id -u` 在 OHOS 返回 'unknown'——
        # `test: integer expected` 失败）——假 id 脚本返回 0 绕过
        fake_bin = os.path.join(self.build_folder, "fakebin")
        os.makedirs(fake_bin, exist_ok=True)
        with open(os.path.join(fake_bin, "id"), "w") as f:
            f.write("#!/bin/sh\necho 0\n")
        os.chmod(os.path.join(fake_bin, "id"), 0o755)
        # conan run() 的 env 参数是 list（非 dict）——PATH 前置假 id；
        # TMPDIR 设为 workdir（config.status 的临时目录 confIehHGc/ 在 TMPDIR——
        # OHOS 默认 TMPDIR 创建失败（Permission denied））
        env = [
            "PATH=" + fake_bin + ":" + os.environ.get("PATH", ""),
            "TMPDIR=" + workdir,
        ]
        self.run(f"./configure --prefix={self.package_folder}", cwd=workdir, env=env)
        # configure 生成 config.status 后 patch 其 mktemp（同上——config.status
        # 运行时再建临时目录——配环境解决 Permission denied）
        cs = os.path.join(workdir, "config.status")
        if os.path.isfile(cs):
            with open(cs) as f:
                ct = f.read()
            ct = ct.replace('mktemp -d "./confXXXXXX"',
                            f'mkdir -p "{tmpd}/conf$$-$RANDOM"')
            ct = ct.replace('tmp=./conf$$-$RANDOM',
                            f'tmp={tmpd}/conf$$-$RANDOM')
            with open(cs, "w") as f:
                f.write(ct)
        self.run("make -j4", cwd=workdir, env=env)

    def package(self):
        workdir = os.path.join(os.path.expanduser("~"), "tmp", "bodr-src-tmp")
        self.run("make install", cwd=workdir)
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
