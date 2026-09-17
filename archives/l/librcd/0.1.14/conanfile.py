#!/usr/bin/env python3
"""Conan recipe — librcd 0.1.14（R. Charset Detection Library）。

librcd 是 RusXMMS 项目的俄文/西里尔文本编码自动检测库（LGPL-2.1+），只有**一个**
公开 API：`rcdGetRussianCharset(buf, len)`，返回 CP1251 / KOI8-R / UTF-8 / CP866 /
ISO-8859-1 五选一的枚举。上游自述其针对**很短的标题**（3-4 字母的 ID3 tag、文件名）
优化，在短文本上的准确率优于 Enca。

构建系统
--------
纯 autotools（autoconf 2.68 + libtool 2.x）。上游另有 `CMakeLists.txt`，但它在
**第一行**就 `message(FATAL_ERROR "Windows only, use autotools to build under
POSIX-capable systems")`，POSIX 平台只能走 autotools。

`configure` / `config.sub` / `config.guess` / `ltmain.sh` / `m4/*.m4` / `aclocal.m4`
全部**预生成并随包分发**，因此本配方**不做 autoreconf**：既不依赖设备 harmonybrew
里的 autoconf/automake（worker PATH 没有 automake，见设备事实），也不引入新的生成物。
代价是这两份 2005/2008 年的 config 脚本不认识 aarch64 与 HarmonyOS，需要补丁（下）。

四个补丁都是 autotools 生成物在 **VPATH + OHOS 沙箱**下的可移植性修复
（不含平台宏、不改上游 C 源码逻辑；补丁逐条说明见 conandata.yml 与 notes.md）：
  * `0001` config.sub 增加 `aarch64` 机器与 `linux-ohos` OS；
  * `0002` config.guess 对 aarch64 直接回 `aarch64-unknown-linux-gnu`（该脚本自身的
    LIBC 探测要在 `umask 077` 建的临时目录里编译探针程序，OHOS 沙箱不允许）；
  * `0003` autoconf 2.68 的 `config.status` 用 `umask 077` 建临时目录，HMDFS 落盘为
    `drwx--S--- 2700` 且属主被映射成共享属主，**同一进程随后也写不进去**，改成 022；
  * `0004` 上游 configure 用 `cat VERSION` 取版本号，VPATH 构建下当前目录里没有
    `VERSION`，使 `-version-info` 退化成 `0:0:0`（产物名 `librcd.so.0.0.0`）；改为
    `cat "$srcdir/VERSION"` 后恢复 `1:14:1`（产物名 `librcd.so.0.1.14`，soname 两种
    情形下都是 `librcd.so.0`）。

除补丁外还有一处**构建期**适配（不改上游文件）：OHOS 上用 `/system/bin/sh` 显式跑
configure（`_configure()`），把 configure → config.status → Makefile 的 SHELL →
libtool 钉在同一个 Toybox shell 上。否则 profile buildenv 的 `CONFIG_SHELL=bash` 会让
autoconf 在 Toybox sh 下选中的 `ECHO='print -r --'` 落到 bash 里执行，libtool 生成时
引号转义整段丢失、产出的 `libtool` 成为非法 sh（`syntax error near unexpected token
'}'`）。这是本包 build() 从"零错误编译"到"能编译"的关键一步，详见 notes.md 问题 5。

关于 `src/russian_table.h` 的字符编码（重要，不是缺陷）
-------------------------------------------------------
该文件是上游生成器（`statgen/doit` → `generate`）产出的**数据表**，字符字面量按
**KOI8-R/CP866 原始字节**书写，整个文件不是合法 UTF-8（276238 字节里 14202 个高位
字节）。clang 会对每个这样的字面量发一条 `-Winvalid-source-encoding` 警告（本包干净轮
日志里 clang 汇总行为 `14205 warnings generated`，约 1.42 万条），但**保留原始字节值**——这正是检测算法需要的值。这一点不能想当然：本包用
`test_package`（34 项断言）在五种编码上核对检测结果来实证"表值没被编译器改写"，
否则会出现"编译零错误、检测全错"的假绿。配方**不**添加 `-Wno-invalid-source-encoding`
去掩掉这些警告（仓库同类先例 vitetris 0.59.1 亦如实保留）。

上游测试
--------
上游**没有**自动化测试套件：`make check` 是最小空实现（`SUBDIRS = src`，各 Makefile.am
无 `TESTS`/`check_PROGRAMS`），编译并运行 0 个测试；`examples/`（演示程序）与
`statgen/`（离线语料统计/生成工具）都不在 `SUBDIRS` 里、目标体内 0 条断言，且
`statgen/doit` 需要 `dos2unix` + `iconv` + `ru_RU.KOI8-R` locale 与语料。清点过程与
归因写在版本级 notes.md 与 test_package/MANIFEST.yml，实测 N = 0。

options
-------
`options.shared` 默认 **True**：系统 `/lib`、`/lib64` 下不存在 `librcd`，不触发 R26
的系统同名库静态约束，按 ADAPTATION_GUIDE §4.1 保留动态产物由 Conan 管理依赖链。
上游 libtool 默认同时产出 `.so` 与 `.a`，本配方显式二选一，避免同一包内两种变体并存
造成下游链接歧义。
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibrcdConan(ConanFile):
    name = "librcd"
    version = "0.1.14"
    description = ("Charset detection library for Russian text "
                   "(CP1251 / KOI8-R / UTF-8 / CP866 / ISO-8859-1)")
    license = "LGPL-2.1-or-later"
    homepage = "http://rusxmms.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("charset", "encoding-detection", "russian", "cyrillic", "koi8-r", "cp1251")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "librcd is adapted for Linux/OHOS, got %s" % self.settings.os)
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "librcd/0.1.14 is validated for OHOS armv8, got %s" % self.settings.arch)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 上游 libtool 默认同时构建并安装 .so 与 .a，两种变体并存会让下游链接结果
        # 依赖链接器细节。Conan 只对 package_type=shared-library/static-library 自动
        # 追加这两个开关，本包 package_type=library，所以在配方里显式落地选项。
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        self._configure(autotools)
        autotools.make(args=["-j1"])
        # 上游没有自动化测试套件（见模块文档串与 notes.md），但 `make check` 是项目
        # 自述的入口，按仓库要求仍然调用：它编译并运行 0 个测试（TOTAL = 0），
        # 如实记入 reports/test-report.md，不以"构建成功"冒充"测试通过"。
        autotools.make(target="check", args=["-j1"])

    def _configure(self, autotools):
        """跑 configure；OHOS 上把生成链钉在同一个 Toybox shell 上。

        本包实测（notes.md 问题 5，与知识草稿 DRAFT-E551 同源）：profile 的 [buildenv]
        把 CONFIG_SHELL/SHELL 指向 `/data/service/hnp/bin/bash`，而 conan 调用 configure
        时它由 shebang 在 Toybox `/bin/sh` 下执行。autoconf 2.68 的 ECHO 探测在 Toybox
        sh 下选中 `print -r --`（Toybox 自带 print 内建），该字面值被写进 config.status；
        随后 config.status 若在 bash 下执行，`$ECHO` 找不到 print，libtool 的
        "Double-quote double-evaled strings" 段整段失效，生成的 `libtool` 文件丢掉
        `\\"` 转义、本身成为非法 sh，在版本脚本行报
        `syntax error near unexpected token '}'`。
        命令行前缀赋值优先于聚合 env，可胜过 profile 的 buildenv；这里同时钉住 SHELL，
        使 configure → config.status → Makefile 的 SHELL → libtool 全程是同一个 shell
        （仓库内先例：archives/a/abx、archives/b/barvinok、archives/n/nut）。
        """
        if self.settings.os != "OHOS":
            autotools.configure()
            return
        configure_script = os.path.join(self.source_folder, "configure")
        command = ("CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh "
                   + shlex.join(["/system/bin/sh", configure_script]))
        if autotools._configure_args:
            command = "%s %s" % (command, autotools._configure_args)
        self.run(command, cwd=self.build_folder, env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # libtool 的 .la 元数据不入库（与仓库 autotools 模板一致）。
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # 安装出来的库文件是 <pkg>/lib/librcd.so（automake 直接采用 librcd.la 的
        # 基名），因此链接开关是 -lrcd —— 与上游 librcd.pc 里的 `Libs: ... -lrcd`
        # 一致；写成 "librcd" 会生成 -llibrcd 去找并不存在的 liblibrcd.so。
        self.cpp_info.libs = ["rcd"]
        self.cpp_info.set_property("pkg_config_name", "librcd")
