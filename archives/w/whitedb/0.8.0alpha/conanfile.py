#!/usr/bin/env python3
"""Conan recipe — whitedb 0.8.0alpha

WhiteDB: lightweight NoSQL database library written in C, operating fully in
main memory. 任务指定版本 0.7.3-git211004 上游不存在（savannah 项目 404 /
GitHub 无此 tag），按任务总纲采用上游最新版本 v0.8.0alpha。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class WhitedbConan(ConanFile):
    name = "whitedb"
    version = "0.8.0alpha"
    description = "WhiteDB is a lightweight NoSQL database library written in C, operating fully in main memory"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/priitj/whitedb"
    url = "https://github.com/priitj/whitedb"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"whitedb: os={self.settings.os} not supported")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("whitedb: OHOS requires armv8/aarch64")

    def build_requirements(self):
        # 上游 tarball 无预生成 configure（仅 configure.ac + Makefile.am + Bootstrap），
        # build() 必须先自举生成 configure。CI 沙箱对 $HOME 手工安装的 automake/libtool
        # 不可见（ENOENT），以 tool_requires 拉入制品仓已发布版本（同 abiword-plugin-* 先例）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
        else:
            tc.configure_args.append("--disable-shared")
        # OHOS: 显式指定 build/host 三元组, 跳过 config.guess 自动探测。
        # conan 构建环境下 config.guess 在 $TMPDIR 内 mktemp 建 2700 临时目录
        # 写 dummy.c 失败("Permission denied"→"cannot guess build type"),
        # 显式 --build/--host 后 configure 直接用给定三元组(同 a52dec 先例)。
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()
        # VirtualBuildEnv: 把 tool_requires(automake/libtool) 的 bin 目录与
        # ACLOCAL/AUTOMAKE/LIBTOOLIZE 环境变量注入 conanbuild 环境
        VirtualBuildEnv(self).generate()

    def build(self):
        # tarball 无预生成 configure，先用直跑链自举（同 abiword 先例：
        # OHOS HMDFS 下 autoreconf 链存在 autoconf.m4f 加载冲突，改用
        # aclocal→autoconf→autoheader→libtoolize→automake 逐级直跑）
        self._run_autogen()

        # E114 (knowledge/graph/E114.kv): HMDFS 上 config.status 用
        # `(umask 077 && mktemp -d ./confXXXXXX)` 建的临时目录权限为 2700
        # (drwx--S---), 组位/其他位无写权限, 进程写 subs1.awk 报
        # "can't create ./confXXXXXX/subs1.awk: Permission denied"。
        # 修法(同 libgsf/abiword-plugin-* CI 已验证先例): 预建可写目录,
        # 修改 configure 内嵌 config.status 模板 ac_tmp 指向该目录, trap 只透传
        # 退出码不再删目录, TMPDIR 一并指向该目录。
        self._fix_e114()

        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # 上游测试全量执行: Test/common.test(PASS) + Test/log.test(SKIP exit 77,
        # logging 默认禁用, 上游 selftest 主动跳过), make check 汇总 EXIT=0
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 清理 libtool .la 包装文件
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        # 上游库名为 libwgdb(非 whitedb), pkg-config 名 whitedb, Libs: -lwgdb
        self.cpp_info.libs = ["wgdb"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m"]
        self.runenv_info.prepend_path("PATH",
                                      os.path.join(self.package_folder, "bin"))

    # ---------- helpers ----------

    def _run_autogen(self):
        """aclocal → autoconf → autoheader → libtoolize → automake 直跑链。"""
        self.output.info("Running aclocal...")
        self.run('"${ACLOCAL:-aclocal}" --force',
                 cwd=self.source_folder, env="conanbuild", ignore_errors=True)
        self.output.info("Running autoconf...")
        self.run('autoconf -o configure configure.ac',
                 cwd=self.source_folder, env="conanbuild", ignore_errors=True)
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException("autoconf failed to generate configure")
        self.output.info("Running autoheader...")
        self.run('autoheader', cwd=self.source_folder,
                 env="conanbuild", ignore_errors=True)
        self.output.info("Running libtoolize...")
        self.run('"${LIBTOOLIZE:-libtoolize}" --force --copy --no-warn',
                 cwd=self.source_folder, env="conanbuild", ignore_errors=True)
        self.output.info("Running automake...")
        self.run('"${AUTOMAKE:-automake}" --add-missing --copy -a -c',
                 cwd=self.source_folder, env="conanbuild", ignore_errors=True)
        for f in ("configure", "Makefile.in"):
            if not os.path.exists(os.path.join(self.source_folder, f)):
                raise ConanException(f"autogen failed to generate {f}")

    def _fix_e114(self):
        if self.settings.os != "OHOS":
            return
        fixed_tmp = os.path.join(self.build_folder, "ac-tmp")
        os.makedirs(fixed_tmp, exist_ok=True)
        os.environ["TMPDIR"] = fixed_tmp
        _cfg_path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(_cfg_path):
            return
        with open(_cfg_path, "r", encoding="utf-8") as _f:
            _cfg = _f.read()
        if "ac_tmp=$tmp" not in _cfg:
            raise ConanException(
                "E114: ac_tmp=$tmp pattern not found in configure; "
                "autoconf may have changed the template")
        _cfg = _cfg.replace("ac_tmp=$tmp", f"ac_tmp={fixed_tmp}")
        _old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
        _new_trap = 'exit $exit_status'
        if _old_trap in _cfg:
            _cfg = _cfg.replace(_old_trap, _new_trap)
        with open(_cfg_path, "w", encoding="utf-8") as _f:
            _f.write(_cfg)
        os.chmod(_cfg_path, 0o755)
        self.output.info(f"  [ok] Patched configure: ac_tmp -> {fixed_tmp} + TMPDIR (E114)")
