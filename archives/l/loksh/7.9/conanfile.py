#!/usr/bin/env python3
"""Conan recipe for loksh 7.9 - portable OpenBSD ksh (single `ksh` binary).

OHOS notes
----------
* Upstream 7.9 builds with Meson; the release tarball bundles the required
  `subprojects/lolibc` git submodule (dimkr/lolibc, linked statically).
  The GitHub tag tarball does NOT contain it - only the official release
  asset does, hence the pinned release URL (R39).
* Vendored meson pattern (zchunk/1.5.2, astroterm/1.0.9, libdvdnav/7.0.0
  validated): device/CI PATH has no meson executable and no resolvable meson
  tool package exists -> vendor official meson 1.11.2 sources via
  conandata["meson_source"] and invoke it in-process through python3 -c.
* ncurses (editing features) comes from the conan package via pkg-config;
  PkgConfigDeps generates ncursesw.pc (package pkg_config_name) which the
  upstream `dependency('ncursesw')` fallback resolves.  If ncurses were
  missing, upstream silently adds -DSMALL (no command editing) - the build
  guards against that so the shipped ksh keeps full line editing.
* No autotools involved: no config.guess/E114(umask 077) surface.
* E074 applies to ninja too: HMDFS jobserver fifo EPERM -> ninja -j1.
* Upstream has no test target in meson.build (no test suite ships in the
  tarball); per the contest rules the consumer test_package exercises the
  built ksh with real scripting assertions instead.
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.0"


class LokshConan(ConanFile):
    name = "loksh"
    version = "7.9"
    description = "Portable OpenBSD ksh (loksh) - a Linux port of the OpenBSD Korn shell"
    license = "Public Domain"  # pdksh/OpenBSD ksh 公有领域；捆绑 lolibc 同为宽松许可
    homepage = "https://github.com/dimkr/loksh"
    url = "https://github.com/dimkr/loksh"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: settings.os 判断必须同时接受 Linux 与 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "loksh OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        # W0: 行编辑功能依赖 ncurses（上游 dependency('ncurses') → 失败时
        # 依次回退 ncursesw → -DSMALL）。制品仓 ncurses/6.6 的
        # pkg_config_name 为 "ncursesw"，与上游回退分支精确对应。
        # MateBook 第一步：conan download 复核二进制包（R35，禁用 conan list）。
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # vendored meson 构建工具源码（astroterm/1.0.9 已验证方案）
        mv = os.path.join(self.source_folder, "meson-vendor")
        get(self, **self.conan_data["meson_source"], strip_root=True, destination=mv)

    # 真机 python3.12 运行 vendored meson 所需前缀（libdvdnav/astroterm 已验证）
    _PY_HOME = "/data/service/hnp/python.org/python_3.12"
    _PY_LIB = "/data/service/hnp/python.org/python_3.12/lib"
    _HNP_BIN = "/data/service/hnp/bin"

    def _python3(self):
        cand = os.path.join(self._HNP_BIN, "python3")
        return cand if os.path.isfile(cand) else "python3"

    def _ninja(self):
        cand = os.path.join(self._HNP_BIN, "ninja")
        return cand if os.path.isfile(cand) else "ninja"

    def _meson_cmd(self, meson_argv):
        # HMBS_PYTHON3 的 site-packages 无 mesonbuild，且 Conan self.run(env=)
        # 设的 PYTHONPATH 传不到子进程 sys.path → 用 python3 -c 进程内注入。
        py = self._python3()
        mv = os.path.join(self.source_folder, "meson-vendor")
        argv_lit = json.dumps(["meson"] + list(meson_argv))
        mv_lit = json.dumps(mv)
        script = (
            "import sys;"
            f"sys.path.insert(0,{mv_lit});"
            f"sys.argv={argv_lit};"
            "from mesonbuild import mesonmain;"
            "rc=mesonmain.main();"
            "sys.exit(rc or 0)"
        )
        return py, ["-c", f"'{script}'"]

    def _meson_env(self, extra=None):
        # Conan 2.x self.run(env=...) 要 list（["KEY=VALUE", ...]）。
        env = {"PATH": os.environ.get("PATH", "")}
        if os.path.isdir(self._HNP_BIN):
            env["PATH"] = self._HNP_BIN + ":" + env["PATH"]
        mv = os.path.join(self.source_folder, "meson-vendor")
        pp = os.environ.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (mv + ":" + pp).strip(":") if pp else mv
        if os.path.isdir(self._PY_HOME):
            env["PYTHONHOME"] = self._PY_HOME
        ll = os.environ.get("LD_LIBRARY_PATH", "")
        if os.path.isdir(self._PY_LIB):
            env["LD_LIBRARY_PATH"] = (self._PY_LIB + ":" + ll).strip(":")
        # PkgConfigDeps 把依赖的 .pc 聚合到 generators 目录，是上游
        # dependency('ncurses'/'ncursesw') 的解析入口。
        env["PKG_CONFIG_PATH"] = self.generators_folder
        for k in ("HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA", "HMBS_PYTHON3"):
            if k in os.environ:
                env[k] = os.environ[k]
        if extra:
            env.update(extra)
        return [f"{k}={v}" for k, v in env.items()]

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()
        # 生成 ncursesw.pc 到 generators 目录（_meson_env 的 PKG_CONFIG_PATH
        # 指向它，上游 meson.build 的 dependency() 按 pkg-config 名查找）
        PkgConfigDeps(self).generate()
        self._inject_meson_archiver()

    def _inject_meson_archiver(self):
        # meson checklist：CI worker PATH 无裸 llvm-ar/llvm-ranlib，需在
        # native file 写绝对路径（astroterm/1.0.9 同款）
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("cpp") or executables.get("c") or ""
            bindir = os.path.dirname(compiler)
            candidate = os.path.join(bindir, "llvm-ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                candidate_ranlib = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(candidate_ranlib):
                    ranlib = candidate_ranlib
        native_file = os.path.join(
            self.generators_folder, "conan_meson_native.ini"
        )
        if not ar or not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        binaries = "[binaries]\nar = '%s'\n" % ar
        if ranlib:
            binaries += "ranlib = '%s'\n" % ranlib
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", binaries, 1))

    def build(self):
        env = self._meson_env()
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        bdir = self.build_folder
        sdir = self.source_folder
        py, margs = self._meson_cmd(
            ["setup", sdir, bdir, "--prefix=/", "--native-file", nf]
        )
        self.run(f'"{py}" {" ".join(margs)}', env=env)
        # 守门：ncurses 必须被 meson 找到，否则上游静默加 -DSMALL
        #（砍掉命令行编辑），与制品仓发布目标不符。
        ninja_file = os.path.join(bdir, "build.ninja")
        if os.path.isfile(ninja_file):
            with open(ninja_file, encoding="utf-8", errors="replace") as fh:
                if "-DSMALL" in fh.read():
                    raise ConanInvalidConfiguration(
                        "meson fell back to -DSMALL: ncurses/ncursesw was "
                        "not resolved via pkg-config; check ncurses/6.6 "
                        "package and PKG_CONFIG_PATH")
        ninja = self._ninja()
        # E074: HMDFS jobserver fifo EPERM → -j1
        self.run(f'"{ninja}" -C "{bdir}" -j1', env=env)
        # 上游 meson.build 无 test()（tarball 不含测试套件），无上游测试可跑；
        # 依据赛事规则由 test_package 消费者测试真实执行被适配工具（见
        # test_package/MANIFEST.yml 的说明）。

    def package(self):
        # meson install 用 --destdir CLI 标志（Conan self.run(env=...) 注入的
        # DESTDIR 不可靠到达 vendored meson 子进程，libdvdnav 已验证），
        # 配合 setup 阶段的 --prefix=/，产物直接落 package_folder 根。
        bdir = self.build_folder
        py, margs = self._meson_cmd(
            ["install", "-C", bdir, "--no-rebuild", "--destdir",
             self.package_folder]
        )
        self.run(f'"{py}" {" ".join(margs)}', env=self._meson_env())

    def package_info(self):
        # R38: 产物为 ksh 命令行 shell（软件级 commands.json 已声明）
        self.cpp_info.bindirs = ["bin"]
