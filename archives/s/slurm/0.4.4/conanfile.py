#!/usr/bin/env python3
"""Conan recipe for slurm 0.4.4 — Meson project (vendored meson).

slurm is a network traffic monitor for the terminal, using ncurses.
Upstream 0.4.4 builds with Meson and depends on the ncurses/curses
dependency only; the product is a single executable plus themes data.

依赖策略：消费制品仓已发布的静态 ncurses/6.6（R35 实证 conan download
二进制可消费），generate() 中取出其 package_folder 的 include/lib 路径，
build() 将上游 `dependency('curses')` 替换为 declare_dependency 直连
libncursesw.a（astroterm/1.0.9 已验证方案），完全不依赖 pkg-config。

meson 获取策略：OHOS 真机与 CI worker 的 PATH 上均无 meson 可执行文件，
且 ohpcd/conancenter 远端不存在可解析的 meson 工具包。沿用
libdvdnav/7.0.0 与 astroterm/1.0.9 已验证的 vendored meson 方案：
source() 下载官方 meson 1.11.2 源码到 source_folder/meson-vendor/，
build() 经 `python3 -c` 在进程内 sys.path.insert 注入后调用
mesonmain.main()，完全不依赖远端工具包。

上游测试现状（R51 清点证据，2026-09-21）：
- meson.build 无任何 test() 条目（grep "test" 零命中）；
- 源码树无 tests/ 目录、无 *test* 文件（find 计数 0）。
即上游 0.4.4 无自动化测试入口；本包以 test_package 消费者用例
（真实执行 slurm 可执行文件 -h）补足鸿蒙可行性验证。
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
    save,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain


class SlurmConan(ConanFile):
    name = "slurm"
    version = "0.4.4"
    description = "Network traffic monitor that shows live statistics in an ncurses terminal UI"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/mattthias/slurm"
    url = "https://github.com/mattthias/slurm"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 静态 widec ncurses（R26：终端工具静态链接；R35/R36 已实证可消费）
        self.requires("ncurses/6.6")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # vendored meson（libdvdnav/astroterm 已验证方案）
        mv = os.path.join(self.source_folder, "meson-vendor")
        get(
            self,
            **self.conan_data["meson_source"],
            strip_root=True,
            destination=mv,
        )

    # 真机 python3.12 运行 vendored meson 所需前缀（libdvdnav/facad notes 已验证）
    _PY_HOME = "/data/service/hnp/python.org/python_3.12"
    _PY_LIB = "/data/service/hnp/python.org/python_3.12/lib"

    def _meson_cmd(self, meson_argv):
        # 绕过 PYTHONPATH：用 `python3 -c` 脚本在进程内 sys.path.insert(0,
        # vendored meson) 再调 mesonmain.main()（astroterm/1.0.9 已验证）。
        py = os.environ.get("HMBS_PYTHON3") or "python3"
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
        # Conan 2.x self.run(env=...) 要 list（["KEY=VALUE", ...]），不是 dict。
        env = {"PATH": os.environ.get("PATH", "")}
        mv = os.path.join(self.source_folder, "meson-vendor")
        pp = os.environ.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (mv + ":" + pp).strip(":") if pp else mv
        if os.path.isdir(self._PY_HOME):
            env["PYTHONHOME"] = self._PY_HOME
        ll = os.environ.get("LD_LIBRARY_PATH", "")
        if os.path.isdir(self._PY_LIB):
            env["LD_LIBRARY_PATH"] = (self._PY_LIB + ":" + ll).strip(":")
        for k in ("HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA", "HMBS_PYTHON3"):
            if k in os.environ:
                env[k] = os.environ[k]
        if extra:
            env.update(extra)
        return [f"{k}={v}" for k, v in env.items()]

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()
        self._inject_meson_archiver()
        # 持久化 ncurses 包路径供 build() 使用（generate 阶段取 host 依赖）
        ncurses = self.dependencies["ncurses"]
        include_dir = os.path.join(
            ncurses.package_folder, ncurses.cpp_info.includedirs[0]
        )
        lib_dir = os.path.join(
            ncurses.package_folder, ncurses.cpp_info.libdirs[0]
        )
        save(
            self,
            os.path.join(self.generators_folder, "ncurses_paths.json"),
            json.dumps({"include_dir": include_dir, "lib_dir": lib_dir}),
        )

    def _inject_meson_archiver(self):
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
        with open(
            os.path.join(self.generators_folder, "ncurses_paths.json"),
            encoding="utf-8",
        ) as handle:
            paths = json.load(handle)
        include_dir = paths["include_dir"].replace("\\", "/")
        libncursesw = os.path.join(paths["lib_dir"], "libncursesw.a")
        if not os.path.isfile(libncursesw):
            raise ConanInvalidConfiguration(
                f"static libncursesw missing in ncurses/6.6 package: {libncursesw}"
            )
        # 上游 meson.build 原文：curses_dep = dependency('curses', version: '>=5')
        # 替换为直连 Conan ncurses 包（astroterm/1.0.9 已验证方案）。
        replace_in_file(
            self,
            os.path.join(self.source_folder, "meson.build"),
            "curses_dep = dependency('curses', version: '>=5')",
            "curses_dep = declare_dependency(\n"
            f"        include_directories: include_directories('{include_dir}'),\n"
            f"        link_args: ['{libncursesw}'],\n"
            "    )",
        )
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        bdir = self.build_folder
        sdir = self.source_folder
        # configure（meson setup <source> <build>）
        py, margs = self._meson_cmd(
            ["setup", sdir, bdir, "--prefix=/", "--native-file", nf]
        )
        self.run(f'"{py}" {" ".join(margs)}', env=self._meson_env())
        # build（ninja）
        ninja = os.environ.get("HMBS_NINJA") or "ninja"
        self.run(f'"{ninja}" -C "{bdir}" -j1', env=self._meson_env())
        self._report_upstream_tests()

    def _report_upstream_tests(self):
        """R51：上游测试如实申报。

        slurm 0.4.4 上游无自动化测试（清点证据见 MANIFEST.yml 与 notes.md：
        meson.build 无 test() 条目，源码树无 tests/ 目录与 *test* 文件）。
        此处仅输出标记供 CI/审计核对，不伪造测试计数。
        """
        ut_result = {
            "status": "no_upstream_tests",
            "framework": "meson",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "evidence": "meson.build contains no test(); no tests/ dir in source tree",
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_result, ensure_ascii=False)
        )

    def package(self):
        # meson install（--destdir staging 到 package_folder；libdvdnav 经验：
        # DESTDIR 环境变量传不可靠，改用 CLI 标志）。
        bdir = self.build_folder
        py, margs = self._meson_cmd(
            ["install", "-C", bdir, "--no-rebuild", "--destdir", self.package_folder]
        )
        self.run(f'"{py}" {" ".join(margs)}', env=self._meson_env())

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
