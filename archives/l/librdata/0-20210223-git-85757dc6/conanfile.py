#!/usr/bin/env python3
"""Conan recipe — librdata 0-20210223-git-85757dc6.

librdata 是读写 R 语言数据文件（`.RData` / `.rds`，R 序列化的 data.frame）的 C 库。
上游 https://github.com/WizardMac/librdata 无 release tag，本版本取 2021-02-23 的
git 快照 commit 4a80bf3894c9250195a564017f2136fd85757dc6（版本串末 8 位即其短哈希）。

上游树是 autotools 工程，但 GitHub archive 快照**不含 configure**（只有
configure.ac / Makefile.am / autogen.sh / config.rpath），必须在 build() 里
autoreconf 自举——这是本配方与「发行 tarball 自带 configure」那类包的唯一结构性差异。

OHOS 适配点（每一条都有设备实测证据，报告见 reports/）：
  1) patches/0001-configure.ac.patch —— 上游 configure.ac 第 17 行用 AM_ICONV，
     该宏来自 GNU gettext 的 iconv.m4，本工具链闭包里没有它，autoreconf 直接
     失败：`configure.ac:17: error: possibly undefined macro: AM_ICONV`。
     OHOS musl libc 自带 iconv.h 与 iconv()/iconv_open()/iconv_close()，
     故改成直接探测 libc（保留「找不到就报错」的语义，不静默降级）。
  2) build() 里删掉生成 configure 里的 `umask 077`（E114）：HMDFS 会把
     `(umask 077 && mktemp -d ./confXXXXXX)` 落成 `drwx--S---`（属主被映射到
     共享属主），随后 config.status 写 `./confXXXXXX/subs1.awk` 报
     `Permission denied`，configure 以 `could not setup config files machinery` 退出。
     去掉 umask 077 后目录落成 `drwxrws--x`（继承父目录的 setgid/组写位），可写。
  3) 显式传 `--build/--host=aarch64-unknown-linux-ohos`：上游 AC_CANONICAL_HOST
     会跑 config.guess，而 config.guess 在同一 HMDFS 目录里创建 dummy.c 同样报
     `Permission denied` → `unable to guess system type`。三元组由 automake 1.18
     的 config.sub 规范化（实测 `aarch64-linux-ohos` → `aarch64-unknown-linux-ohos`）。
     build==host，故 configure 仍是原生构建，AC_CHECK_LIB 做的是真实链接探测。
  4) 三个可选压缩后端（bz2 / lzma / z）走 Conan 依赖并显式注入
     CPPFLAGS/LDFLAGS/LIBS（AutotoolsDeps）：OHOS SDK sysroot 里 `libz.so` 是
     一个 stub（13888 B、全部符号同址、SONAME=libz.so，且 /system/lib64 下没有
     libz.so，运行期只有 /usr/lib/libz.so.1）；若让上游的
     `AC_CHECK_LIB([z],[deflate])` 命中它，会把 `libz.so` 写进 DT_NEEDED，
     `librdata.so` 运行期就装载不起来。三个后端都是静态制品，链接结果是内链
     （实测 librdata.so 的 DT_NEEDED 只有 libc.so）。
  5) tool_requires 只放 automake/libtool，**不放 autoconf**：conan 的
     autoconf/2.72 会带出 conan perl/5.42.2 并把 PERL5LIB 指向它的 XS 模块，
     而本机 autoreconf/autoconf 解析到的是 /data/service/hnp/bin（shebang 钉死在
     HNP perl 5.42.0），两套 perl 混用后 autoreconf 直接
     `Can't load .../Cwd.so ... Perl_my_cxt_init: symbol not found`。
     HNP 工具链自带 autoconf 2.72 + m4 1.4.20 + perl 5.42.0，去掉 conan autoconf
     后 autoreconf 正常（实测 rc 0 → 1 的对照见 reports/）。

构建与测试：
  * build() 里 `make` 之后跑 `make check`——上游 `TESTS = test_rdata`
    （automake 框架注册 1 项，`test-suite.log` 的 `# TOTAL: 1`）；
  * test_package 走 CMakeDeps 找到本包，用公开 API 做一轮
    write→read 往返（.RData 与 .rds 两条路径），断言列数/取值/NULL 文本/表名。
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _drop_umask_077(path):
    """E114：HMDFS 强制 setgid，`(umask 077 && mktemp -d)` 落成 drwx--S--- 且属主
    被映射成共享属主，随后 config.status 往该目录写文件恒 Permission denied。
    configure 是 autoreconf 的产物、不在源码树里，因此只能在生成之后就地修。"""
    with open(path, "r", encoding="utf-8") as handle:
        data = handle.read()
    patched = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`',
    ).replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    if patched == data:
        raise ConanException(
            "E114 workaround did not apply: configure no longer creates its temp dir "
            "with `umask 077 && mktemp -d`")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(patched)


class LibrdataConan(ConanFile):
    name = "librdata"
    version = "0-20210223-git-85757dc6"
    description = "C library for reading and writing R data frames (.RData / .rds)"
    license = "MIT"
    homepage = "https://github.com/WizardMac/librdata"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游 configure.ac 用 AC_CHECK_LIB 探测三个可选压缩后端。
        # OHOS SDK sysroot 只有 libz.so stub（见模块 docstring 第 4 条），
        # 因此三个后端都显式走 Conan；三者制品均为静态库，内链进 librdata，
        # 不引入运行期 .so 依赖（R26 同口径）。
        self.requires("zlib/1.3.1.1")
        self.requires("bzip2/1.0.8.2")
        self.requires("liblzma/5.8.1")

    def build_requirements(self):
        # GitHub archive 快照不带 configure，build() 必须 autoreconf 自举。
        # 只声明 automake/libtool：conan autoconf 会带出 conan perl 并污染
        # PERL5LIB，与 HNP 自带 autoconf/perl 混用后 autoreconf 直接崩（见 docstring 第 5 条）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32：settings.os 只支持 Linux/OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "librdata is only supported on OHOS/Linux, not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        if str(self.settings.os) == "OHOS":
            # config.guess 在本设备 HMDFS 上无法创建 dummy.c（E114），且上游
            # AC_CANONICAL_HOST 需要把 OHOS 三元组交给 config.sub 规范化。
            tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()
        # AutotoolsToolchain 本身不再为依赖注入 -I/-L/-l：压缩后端靠它拿到
        # CPPFLAGS/LDFLAGS/LIBS，configure 的 AC_CHECK_LIB 才会命中 Conan 制品
        # 而不是 sysroot 的 libz.so stub。
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 上游快照无 configure：先自举（automake 1.18 提供 aclocal/automake/config.sub，
        # libtool 2.5.4 提供 libtoolize/ltmain.sh）
        autotools.autoreconf()
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        self._configure(autotools)
        # conan 默认 os.cpu_count()=20 而本机 affinity 更小；显式自限，避免超订
        jobs = self.conf.get("tools.build:jobs", default=2, check_type=int) or 2
        autotools.make(args=["-j{}".format(jobs)])
        # 上游测试：TESTS = test_rdata（automake 框架注册 1 项）
        autotools.make(target="check", args=["-j{}".format(jobs)])

    def _configure(self, autotools):
        """把 configure → config.status → Makefile/libtool 的 SHELL 全程钉在同一个 sh。

        profile [buildenv] 的 CONFIG_SHELL/SHELL 指向 bash，而 configure 由 shebang 在
        Toybox /bin/sh 下执行：autoconf 会选中 Toybox 的 `print` 内建并把
        ECHO='print -r --' 写进 config.status，随后在 bash 下跑的 config.status/libtool
        找不到 `print`，生成的 libtool 丢引号转义。命令行前缀赋值优先于聚合 env。
        """
        if str(self.settings.os) != "OHOS":
            autotools.configure()
            return
        configure = os.path.join(self.source_folder, "configure")
        command = ("CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh "
                   + shlex.join(["/system/bin/sh", configure]))
        if autotools._configure_args:
            command += " " + autotools._configure_args
        self.run(command, env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool 的 .la 会烤死构建期绝对路径（含 conan cache 路径），不进交付面
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["rdata"]
        self.cpp_info.set_property("cmake_file_name", "librdata")
        self.cpp_info.set_property("cmake_target_name", "librdata::librdata")
