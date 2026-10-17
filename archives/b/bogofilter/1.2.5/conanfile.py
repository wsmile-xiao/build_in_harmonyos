#!/usr/bin/env python3
"""Conan recipe for bogofilter 1.2.5 — fast Bayesian spam filter (C).

bogofilter 是 C 语言贝叶斯垃圾邮件过滤器（GPL-2.0），Autotools 构建
（自带 configure）。数据存储引擎默认 Berkeley DB（libdb），制品仓未发布
libdb → 用 --with-database=sqlite3 切换 sqlite（制品仓已发布）替代。

OHOS 适配:
- config.guess 不识别 `aarch64-linux-ohos` → configure 用
  `--build=aarch64-linux --host=aarch64-linux`（鸿蒙 clang 驱动仍目标
  aarch64-linux-ohos）；
- 测试: 上游 `make check` 自带测试集；test_package 用 bogoutil 训练
  样本词库 + bogofilter 分类验证贝叶斯流程可用。
"""
import os
import re

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import get, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps


class BogofilterConan(ConanFile):
    name = "bogofilter"
    version = "1.2.5"
    description = "Fast anti-spam filtering by Bayesian statistical analysis"
    license = "GPL-2.0"
    homepage = "http://bogofilter.sourceforge.net/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        # 默认引擎 Berkeley DB（libdb）制品仓未发布 → 用 sqlite3 替代
        self.requires("sqlite3/3.49.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--build=aarch64-linux",
                "--host=aarch64-linux",
                "--with-database=sqlite3",
            ]
        )
        tc.generate()
        # TMPDIR 注入：CI 沙箱 TMPDIR(/data/storage/el2/base/cache) 不可写，
        # configure 早期 conftest 阶段（AC_PROG_CC 检测）创建临时文件失败 →
        # "C compiler cannot create executables"（CI #29277）。在 build 目录
        # 内创建可写 tmp 并注入 TMPDIR，使 configure 全程使用可写目录
        # （同 docbook/libgsf "ac_tmp" 修复思路）。必须与 buildenv 一起注入。
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        self.buildenv_info.define("TMPDIR", _tmp_dir)
        VirtualBuildEnv(self).generate()
        # sqlite3 头/库路径注入（AC_LIB_LINKFLAGS 走 pkg-config / 默认路径）
        sqlite_pkg = self.dependencies["sqlite3"].package_folder
        env = Environment()
        env.append("CPPFLAGS", f"-I{os.path.join(sqlite_pkg, 'include')}")
        env.append("LDFLAGS", f"-L{os.path.join(sqlite_pkg, 'lib')}")
        env.vars(self).save_script("conanbuild_bogofilter_env")

    def _patch_configure_umask(self, build):
        """configure 运行前移除 umask 077（CI #29302 根因）。

        上游 configure 用 `umask 077 && mktemp -d ./confXXXXXX` 创建 ac_tmp
        临时目录，077 权限使脚本子进程写 subs1.awk 被鸿蒙 HMDFS 拦截
        （config.status 阶段 Permission denied）。必须在 configure **运行前**
        patch configure 脚本本身——现有 _fix_config_status 事后修 config.status
        走不到（configure 内部已失败抛异常）。同 abook 方案但提前到 configure 前。
        """
        path = os.path.join(build, "configure")
        if not os.path.exists(path):
            return
        content = load(self, path)
        fixed = content.replace("umask 077 && mktemp", "mktemp")
        fixed = fixed.replace("umask 077 && mkdir", "mkdir")
        if fixed != content:
            save(self, path, fixed)
            self.output.info("patched configure: removed umask 077 (ac_tmp)")

    def _fix_config_status(self, build):
        """config.status ac_tmp 指向可写目录（鸿蒙安全框架拦脚本子进程
        写 TMPDIR，同 abook/globus-common 模式）。"""
        path = os.path.join(build, "config.status")
        if not os.path.exists(path):
            return
        content = load(self, path)
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        content = content.replace(
            "ac_tmp=$tmp",
            'ac_tmp=$tmp\nchmod 755 "$tmp" 2>/dev/null',
        )
        save(self, path, content)

    def build(self):
        # TMPDIR 用 os.environ 注入（CI 沙箱 TMPDIR=/data/storage/el2/base/cache
        # 不可写，clang 链接 conftest 创建临时文件失败 → "C compiler cannot
        # create executables"）。buildenv_info 注入在 CI 环境（.cache/conan2
        # 新版本）未生效——os.environ 让 configure/clang 子进程直接继承。
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        # 先修 configure 脚本（umask 077 → 可写 ac_tmp），再运行 configure
        self._patch_configure_umask(self.build_folder)
        autotools = Autotools(self)
        autotools.configure()
        self._fix_config_status(self.build_folder)
        cs_path = os.path.join(self.build_folder, "config.status")
        mk_path = os.path.join(self.build_folder, "Makefile")
        if os.path.exists(cs_path) and not os.path.exists(mk_path):
            self.run("cd " + self.build_folder + " && bash config.status")
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
