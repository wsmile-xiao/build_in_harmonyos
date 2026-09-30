#!/usr/bin/env python3
"""Conan test_package for lite 2.1.8 (lite-xl).

Builds test_litexl with MesonToolchain, then runs it against the installed
lite-xl binary.  R34: the test GENUINELY executes the packaged lite-xl binary
through its real startup path (SDL init → Lua VM boot → core.init →
$LITE_USERDIR/init.lua) and asserts on its runtime output — not a print-only
shell test (see test_litexl.c).
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LiteTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()
        self._inject_meson_archiver()

    def _inject_meson_archiver(self):
        # 【OHOS 必需】同主配方：conan 的 MesonToolchain 不把 tools.build:compiler_executables
        # 里的 ar/ranlib 写进 native file，meson 便按裸名 llvm-ar/ar 探归档器；而 clang 工具链在
        # /data/service/hnp/bin，PATH 上没有时 meson configure 直接失败。全路径注入 native file。
        import os
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar, _rl = _ce.get("ar"), _ce.get("ranlib")
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
            if _bindir:
                _cand = os.path.join(_bindir, "llvm-ar")
                if os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = os.path.join(_bindir, "llvm-ranlib")
                    if os.path.isfile(_rlc):
                        _rl = _rlc
        _nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not (_ar and os.path.isfile(_nf)):
            return
        with open(_nf, encoding="utf-8") as _f:
            _c = _f.read()
        if "\nar =" in _c or "[binaries]" not in _c:
            return
        _ins = "[binaries]\nar = '%s'\n" % _ar
        if _rl:
            _ins += "ranlib = '%s'\n" % _rl
        with open(_nf, "w", encoding="utf-8") as _f:
            _f.write(_c.replace("[binaries]\n", _ins, 1))

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        dep = self.dependencies["lite"]
        bindir = dep.cpp_info.bindirs[0]
        litexl = os.path.join(dep.package_folder, bindir, "lite-xl")
        # OHOS 上 /system/bin/sh (mksh) 不能直接 exec ELF，用 bash 包一层执行
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # 真实调用被测二进制；env=conanrun 提供全部依赖库路径（LD_LIBRARY_PATH），
        # 保证 lite-xl 运行期能找到 freetype 等 conan 依赖的 .so。
        self.run(
            f'LITE_XL_BIN="{litexl}" {bash} -c "./test_litexl"',
            env="conanrun",
        )
