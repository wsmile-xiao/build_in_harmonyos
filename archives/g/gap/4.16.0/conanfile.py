#!/usr/bin/env python3
"""Conan recipe — GAP 4.16.0（计算群论系统；手写 recipe）

为什么手写而不用生成器：GAP 的安装远不止 `make install`。
① 上游自己在 `Makefile.rules` 的 install 目标里印着「'make install' support is still
   experimental, and may be buggy. It also does not take care of installing GAP packages」；
② GAP 的**包（pkg/）是功能的一半**，`make install` 一个都不装。sage 的 spkg-install
   手工补装了 18 个包（gapdoc/primgrp/smallgrp/transgrp 是 GAP 起动就要的，
   其余是默认自动加载的 PackagesToLoad 那一批 + tomlib 的依赖 atlasrep）。
   少装 = GAP 能起来但一用就报 package not available，属**静默功能缺失**。

消费方是 passagemath-gap 的 wheel：它把整个 `lib/gap` 树（按一长串 --exclude 剔掉
大数据与文档）塞进 wheel 的 `sage_wheels/gap/`，再单独拷 `bin/gap`。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class GapConan(ConanFile):
    name = "gap"
    version = "4.16.0"
    description = "GAP — 计算离散代数系统，尤以计算群论见长"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gap-system.org/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # sage spkg-install.in 里逐字列出的那批（顺序无关，缺一都可能让默认配置起不来）
    _SAGE_PKGS = (
        "gapdoc", "primgrp", "smallgrp", "transgrp",          # GAP 启动必需
        "alnuth", "atlasrep", "autpgrp", "crisp", "ctbllib",   # 默认自动加载的
        "factint", "fga", "irredsol", "laguna", "polenta",
        "polycyclic", "resclasses", "sophus", "tomlib",
        "packagemanager",
    )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("gmp/6.3.0")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        # 依赖显式指路：GAP 的 configure 用 --with-gmp/--with-readline 收前缀
        tc.configure_args.append("--with-gmp=%s" % self.dependencies["gmp"].package_folder)
        # **明确不接 readline**：configure 的 readline 链接测试在设备上过不去
        # （`--with-readline was given, but further tests for readline failed`，
        # 它还要 ncurses/tinfo 一起链）。readline 只影响**交互式命令行的行编辑**，
        # 而 passagemath 走的是 libgap 与管道，不用 GAP 自己的 REPL 编辑功能。
        # 这是一处**有意的能力取舍**，不是没接上：接口层面无损。
        tc.configure_args.append("--without-readline")
        tc.configure_args.append("--with-zlib=%s" % self.dependencies["zlib"].package_folder)
        # 把依赖的 libdir 前置进 LDFLAGS（同 autotools 模板：环境里的 -L 会抢在前面）
        import os as _os
        _env = tc.environment()
        _lp = " ".join("-L{}".format(_d) for _r, _dep in self.dependencies.items()
                       for _d in (_dep.cpp_info.libdirs or []) if _os.path.isabs(_d))
        if _lp:
            _env.prepend("LDFLAGS", _lp)
        tc.generate(_env)

    def build(self):
        import glob as _glob
        # configure 里的 umask 077 在这套文件系统上会让 config.status 建的临时目录不可写
        for cfg in _glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j4"])

    def package(self):
        autotools = Autotools(self)
        # install 并行有竞态（上游自己都说这个目标是实验性的），恒 -j1
        autotools.install(args=["-j1"])
        self._install_gap_packages()
        self._sign_binaries()

    def _install_gap_packages(self):
        """把 sage 需要的 GAP 包拷进 <pkg>/lib/gap/pkg。

        `make install` 一个包都不装，而 GAP 起动就要 gapdoc/primgrp/smallgrp/transgrp。
        逐个核对，缺一即失败 —— 少装不会报错，只会在下游用到时才炸。
        """
        import shutil as _shutil
        src_pkg = os.path.join(self.source_folder, "pkg")
        # GAP 的 make install 把**架构无关**的 GAP root 装到 share/gap（lib/init.g 在那），
        # lib/gap 只放 sysinfo.gap 这类架构相关件。包是架构无关的，必须进 share/gap/pkg —— 
        # 放 lib/gap/pkg 的话 GAP 起来就报 `cannot find 'lib/init.g'`（实撞）。
        dst_pkg = os.path.join(self.package_folder, "share", "gap", "pkg")
        os.makedirs(dst_pkg, exist_ok=True)
        missing = []
        for name in self._SAGE_PKGS:
            # 源码树里的包目录带版本后缀（如 GAPDoc-1.6.7），按前缀匹配
            cands = [d for d in sorted(os.listdir(src_pkg))
                     if d.lower() == name or d.lower().startswith(name + "-")]
            if not cands:
                missing.append(name)
                continue
            for d in cands:
                s, t = os.path.join(src_pkg, d), os.path.join(dst_pkg, d)
                if not os.path.isdir(t):
                    _shutil.copytree(s, t, symlinks=True)
        if missing:
            raise RuntimeError("GAP 包缺失（tarball 里没找到）: %s" % ", ".join(missing))
        self.output.info("已装 GAP 包: %s" % ", ".join(sorted(os.listdir(dst_pkg))))

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _tool(self, name, fallback):
        import shutil as _shutil
        return _shutil.which(name) or fallback

    def _sign_binaries(self):
        if self.settings.os != "OHOS":
            return
        import glob as _glob
        targets = _glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += _glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for n in os.listdir(bindir):
                p = os.path.join(bindir, n)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = self._tool("llvm-objcopy", "/data/service/hnp/bin/llvm-objcopy")
        signer = self._tool("binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool")
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["gap"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "libgap")
        # 消费方（passagemath-gap）要知道 GAP root 在哪
        self.runenv_info.define_path("GAP_ROOT", os.path.join(self.package_folder, "share", "gap"))
