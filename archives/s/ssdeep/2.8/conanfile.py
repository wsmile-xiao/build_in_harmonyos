#!/usr/bin/env python3
"""Conan recipe — ssdeep 2.8.

ssdeep 是模糊哈希（context-triggered piecewise hashing）工具，
双产物：libfuzzy 库（公开头 fuzzy.h）+ ssdeep CLI 工具。
构建系统：GNU autotools（2012 老工程）。

适配要点（E-class 已知坑）：
  1. tarball 内 config.guess/config.sub 为 2005 版，不认识 HarmonyOS triplet，
     必须以 patches/autotools/ 中 2024 版替换（禁止 --build/--host 绕行）。
  2. tarball 未打包 m4/ 宏目录（aclocal.m4 引用 m4/libtool.m4 等），
     make 阶段 automake maintainer 规则会触发 autoconf 再生成并失败；
     用 libtoolize 生成的 m4/*.m4（vendored in patches/autotools/m4/）
     补齐，并把 autotools 依赖源文件时间戳设为过去、configure 保持最新，
     阻止再生成（参照 babeltrace 1.5.11 配方 E011/E114 处理）。
"""
import os
import shutil
import time as _time

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SsdeepConan(ConanFile):
    name = "ssdeep"
    version = "2.8"
    description = "ssdeep 2.8 — fuzzy hashing library (libfuzzy) and CLI tool"
    license = "GPL-2.0-only"
    homepage = "https://github.com/ssdeep-project/ssdeep"
    url = "https://github.com/ssdeep-project/ssdeep"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # vendored 的 autotools 修复文件（config.guess/config.sub/m4）随配方导出，
        # source() 中复制进源码树（参照 babeltrace 1.5.11 配方）。
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # E-class: 2012 老 autotools —— 替换 config.guess/config.sub 为 2024 版，
        # 并补齐 m4/ 宏目录（libtoolize 产物 vendored 在 patches/autotools/）。
        at_src = os.path.join(self.recipe_folder, "patches", "autotools")
        if not os.path.isdir(at_src):
            at_src = os.path.join(self.export_sources_folder, "patches", "autotools")
        if os.path.isdir(at_src):
            for fn in ("config.guess", "config.sub"):
                src = os.path.join(at_src, fn)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(self.source_folder, fn))
            m4_src = os.path.join(at_src, "m4")
            m4_dst = os.path.join(self.source_folder, "m4")
            if os.path.isdir(m4_src) and not os.path.isdir(m4_dst):
                os.makedirs(m4_dst, exist_ok=True)
                for fn in os.listdir(m4_src):
                    if fn.endswith(".m4"):
                        shutil.copy2(os.path.join(m4_src, fn), os.path.join(m4_dst, fn))

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # 阻止 automake maintainer 规则在 make 阶段重跑 autoconf/automake：
        # tarball 缺 m4/ 且 CI worker 无 aclocal-1.12/automake-1.12，
        # 一旦触发再生成链必然失败。把 autotools 依赖源文件时间戳设为
        # 过去，configure 保持最新，规则不再触发。
        _past = _time.mktime((2000, 1, 1, 0, 0, 0, 0, 0, -1))
        for _f in ("configure.ac", "aclocal.m4", "Makefile.am", "Makefile.in",
                   "config.h.in", "config.guess", "config.sub"):
            _p = os.path.join(self.source_folder, _f)
            if os.path.isfile(_p):
                os.utime(_p, (_past, _past))
        _m4d = os.path.join(self.source_folder, "m4")
        if os.path.isdir(_m4d):
            for _fn in os.listdir(_m4d):
                _p = os.path.join(_m4d, _fn)
                if os.path.isfile(_p):
                    os.utime(_p, (_past, _past))
        _p = os.path.join(self.source_folder, "configure")
        if os.path.isfile(_p):
            os.utime(_p, None)  # 保持最新

        # E114/E110/E112（同 libgsf/abiword 配方）：远端 CI 构建目录（conan cache
        # p/b/... 类路径）上，autoconf config.status 用 `umask 077 && mktemp -d
        # "./confXXXXXX"` 建 0700 私有临时目录并向其中写 subs1.awk 被拒
        # （EACCES → "could not setup config files machinery"），同源问题还影响
        # configure 编译 conftest 时的 clang $TMPDIR 临时文件。修法：配方主进程
        # 预建可写目录、设置 TMPDIR/TMP/TEMP，并把 configure 内嵌 config.status
        # 模板的 ac_tmp 改指该目录（同时把 trap 的删除动作改为仅透传退出码，
        # 避免预建目录被 rm -fr，影响后续轮次）。
        if self.settings.os == "OHOS":
            import tempfile as _tempfile
            fixed_tmp = os.path.join(_tempfile.gettempdir(), "ssdeep-ac-tmp")
            os.makedirs(fixed_tmp, exist_ok=True)
            os.environ["TMPDIR"] = fixed_tmp
            os.environ["TMP"] = fixed_tmp
            os.environ["TEMP"] = fixed_tmp
            _cfg_path = os.path.join(self.source_folder, "configure")
            if os.path.exists(_cfg_path):
                with open(_cfg_path, "r", encoding="utf-8", errors="surrogateescape") as _f:
                    _cfg = _f.read()
                if "ac_tmp=$tmp" in _cfg:
                    _cfg = _cfg.replace("ac_tmp=$tmp",
                                        "ac_tmp={}".format(fixed_tmp))
                    _old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
                    _new_trap = 'exit $exit_status'
                    if _old_trap in _cfg:
                        _cfg = _cfg.replace(_old_trap, _new_trap)
                    with open(_cfg_path, "w", encoding="utf-8",
                              errors="surrogateescape") as _f:
                        _f.write(_cfg)
                    os.chmod(_cfg_path, 0o755)
                    self.output.info(
                        "  [ok] Patched configure: ac_tmp -> {} + TMPDIR (E114)".format(fixed_tmp))
                else:
                    self.output.warning(
                        "  [warn] ac_tmp=$tmp pattern not found in configure; "
                        "skip ac_tmp patch, TMPDIR still set")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 双产物：库（libfuzzy）+ CLI（bin/ssdeep）
        self.cpp_info.libs = ["fuzzy"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "ssdeep")
        self.cpp_info.set_property("cmake_target_name", "ssdeep::ssdeep")