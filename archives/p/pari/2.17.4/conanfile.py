#!/usr/bin/env python3
"""Conan recipe for PARI/GP 2.17.4（鸿蒙 PC 原生构建）。

版本与配置**对齐上游 passagemath-pari 10.8.7**：它打包的是
`libpari-gmp-tls-<hash>.so.2.17.4`，即 **GMP 内核 + 线程局部栈**。
库名由 Configure 拼出（`Configure:104` gmp → `pari-gmp`；`:108` tls → 追加 `-tls`），
所以这两个开关**同时决定 ABI 与 soname**，不是可选优化项。

注意：本仓早先有一份 pari 2.17.3 的 cmd-pkgs 交付，是「内置大数替代 GMP」编的，
出的是 `libpari.so`——库名都不同，下游 cypari2 / passagemath-pari 用不了。
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class PariConan(ConanFile):
    name = "pari"
    version = "2.17.4"
    description = "PARI/GP computer algebra system for number theory"
    license = "GPL-2.0-or-later"
    homepage = "https://pari.math.u-bordeaux.fr"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("PARI supports Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        # autoconf 的 `umask 077` 在这套文件系统上会让 config.status 报 Permission denied。
        # PARI 用自研 Configure、通常走不到那里，但源码树里若混入 autoconf 脚本一并处理。
        # ⚠️ 函数内一律别名导入：`import os` 会把 os 变成 build() 的局部名，
        # 这行之前任何 os.xxx 都 UnboundLocalError，且报错点在别处。
        import glob as _glob, os as _os
        for _cfg in _glob.glob(_os.path.join(self.source_folder, "**", "configure"),
                               recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as _f:
                    _t = _f.read()
            except OSError:
                continue
            if "umask 077" in _t:
                with open(_cfg, "w", encoding="utf-8") as _f:
                    _f.write(_t.replace("umask 077", "umask 022"))

        # 架构识别走 patches/0001：给 config/arch-osname 加 harmonyos 分支。
        # **不用 uname 垫片**——垫片靠 PATH 前缀生效，而 self.run(env="conanbuild")
        # 会用 conan 的环境脚本重设 PATH 把它盖掉（实撞：垫了也仍是 O*-none）。
        # 改源码是确定性的，不依赖环境变量怎么传。
        # PARI 用 **$LD 直接链可执行文件**（config/get_ld：LD 为空时才回落到 $CC）。
        # 环境里若把 LD 设成裸链接器（CI 上是 ld.lld），链接命令就绕过了编译器驱动，
        # 没有 sysroot、没有默认库搜索路径，于是
        #   ld.lld: error: unable to find library -lm
        # 而 libm.a 明明就在 SDK sysroot 里 —— 本机能过只是因为本机环境没设 LD。
        # 显式钉成编译器驱动，不受环境影响；这也正是 PARI 自己的默认意图。
        _cc = self.conf.get("tools.build:compiler_executables",
                            default={}, check_type=dict).get("c", "clang")
        gmp = self.dependencies["gmp"].package_folder
        args = [
            f"--prefix={shlex.quote(self.package_folder)}",
            f"--libdir={shlex.quote(_os.path.join(self.package_folder, 'lib'))}",
            f"--includedir={shlex.quote(_os.path.join(self.package_folder, 'include'))}",
            # GMP 内核：与上游一致，且决定 soname（pari-gmp-…）
            f"--with-gmp={shlex.quote(gmp)}",
            f"--with-gmp-include={shlex.quote(_os.path.join(gmp, 'include'))}",
            f"--with-gmp-lib={shlex.quote(_os.path.join(gmp, 'lib'))}",
            "--enable-tls",          # 线程局部栈：soname 里的 -tls 由它而来
            # 不开 --mt=pthread：PARI 的 pthread 引擎用了 pthread_cancel /
            # pthread_setcanceltype，这套 libc 没有这两个符号，链接期直接
            #   ld.lld: error: undefined symbol: pthread_setcanceltype
            # 它只影响 PARI **自带的并行计算引擎**，不影响 soname
            # （库名只由 gmp + tls 决定，见 Configure:104/108），
            # 下游 cypari2 / passagemath-pari 也不使用该引擎。
            "--graphic=none",        # 不引 X11/FLTK
            "--without-readline",    # gp 的交互补全，库本身不需要；少一层依赖
        ]
        # ⚠️ LD 是**环境变量**、不是 Configure 参数——当参数传只会打印用法并退出
        # （实撞：`./Configure LD=clang …` 直接失败）。依据是 Configure --help 的
        # 「Environment variables affecting the build: CC CFLAGS LD LDFLAGS …」。
        self.run("LD=%s ./Configure %s" % (shlex.quote(str(_cc)), " ".join(args)),
                 cwd=self.source_folder, env="conanbuild")
        # Configure 把 Makefile 生成到 O<os>-<arch>/，make 必须在那儿跑
        objs = sorted(_glob.glob(_os.path.join(self.source_folder, "O*-*")))
        if not objs:
            raise ConanInvalidConfiguration(
                "Configure 没有生成 O<os>-<arch> 构建目录——先看它的输出")
        self._objdir = objs[0]
        self.run("make gp", cwd=self._objdir, env="conanbuild")
        # 跑上游自带测试套件（src/test/in 下的用例）。
        # src/test/dotest 在任一用例出 BUG 时 exit 1，所以失败能真正拦住构建，
        # 不会像某些测试脚本那样「打印错误却返回 0」。
        if can_run(self):
            self.run("make bench", cwd=self._objdir, env="conanbuild")

    def package(self):
        # 用 install-nodata + install-data，**不用 `make install`**：后者含 install-doc，
        # 那一步要 TeX 生成 dvi；conan 包也不需要文档。
        self.run("make install-nodata", cwd=self._objdir, env="conanbuild")
        self.run("make install-data", cwd=self._objdir, env="conanbuild")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # ⚠️ **链接名是 pari，不是 pari-gmp-tls**：PARI 装出来的是
        #   libpari-gmp-tls.so.2.17.4        实体
        #   libpari-gmp-tls.so.9 -> 实体     SONAME 指向这个
        #   libpari.so           -> 实体     **未加版本号的链接名只有这一个**
        # 所以链接用 -lpari，运行期由 SONAME 加载 libpari-gmp-tls.so.9。
        # 写成 pari-gmp-tls 会让 CMakeDeps 报 "Library 'pari-gmp-tls' not found
        # in package"（实撞一轮）。上游 cypari2 同样是 -lpari。
        self.cpp_info.libs = ["pari"]
        self.cpp_info.set_property("cmake_file_name", "pari")
        self.cpp_info.set_property("cmake_target_name", "pari::pari")
        self.cpp_info.set_property("pkg_config_name", "pari")
        self.cpp_info.system_libs = ["m", "pthread"]
