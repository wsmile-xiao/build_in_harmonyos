#!/usr/bin/env python3
"""Conan recipe for cracklib 2.9.8 (cracklib/cracklib).

CrackLib 是密码强度检查库：FascistCheck()/FascistCheckUser() 对候选密码做
字典命中/反转命中/过短/过于规律等检查，返回拒绝原因或 NULL（通过）。
纯 C，零第三方运行时依赖（W0 预检通过；--without-zlib 关闭可选 gz 支持，
避免把 gz* 符号泄漏给消费者，CI #43836 链接实测）。

OHOS 适配要点（沿 2.10.3 已验证经验，W0b 历史比对）：
- 预生成 configure 的官方 release tarball；显式 --build/--host=
  aarch64-unknown-linux-gnu（build==host 原生，跳过 config.guess 写盘探针，
  沿用 libmatheval 教训）+ --without-python --disable-nls（裁剪 python
  绑定与 NLS，沙箱无 gettext）。
- 顶层 SUBDIRS = m4 lib util po doc python dicts：只编 lib + util
  （make SUBDIRS="lib util"，同 2.10.3 裁剪模式）。
- 设备默认 TMPDIR(HMDFS) 临时文件权限受限，config.status 的
  confg*/subs*.awk 机制会 Permission denied（CI #43739 实测复现）；
  TMPDIR 指到可写可执行的 build 目录，并把 configure 生成的
  config.status here-doc 里的 umask 077 全部放宽为 022（CI #43775 根因）。
- 上游测试真相：util/Makefile.am 声明 3 个 check_PROGRAMS（testlib/testnum/
  teststr，stdin 交互驱动），无随包分发的自动化 check 脚本 →
  发布包内上游自动化测试不可用（详见 test_package/MANIFEST.yml）。
  适配侧 L1：用上游工具 cracklib-packer（输入经 sort -u 规范化，等效
  cracklib-format 对该净词表的输出）把 dicts/cracklib-small（54763 词）
  打成 testdict，再用公开 API FascistCheckUser 做 4 条语义断言
  （典内词×2 拒绝/过短拒绝/强密码通过）。
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
import os


class CracklibConan(ConanFile):
    name = "cracklib"
    version = "2.9.8"
    description = "CrackLib - a password strength checking library (FascistCheck)"
    license = "LGPL-2.1-only"
    homepage = "https://github.com/cracklib/cracklib"
    url = ""  # CI fills this
    topics = ("password", "strength", "dictionary", "security")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        copy(self, "test_cracklib_build.c", src=self.recipe_folder, dst=self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        src = self.source_folder
        triple = "aarch64-unknown-linux-gnu"
        # 设备默认 TMPDIR(HMDFS) 临时文件权限受限，config.status 的
        # confg*/subs*.awk 机制会 Permission denied（CI #43739 实测复现）；
        # 指到可写可执行的 build 目录（libmatheval 同款教训）。
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        # 真正的根因（CI #43775 在 TMPDIR 修复后仍复现）：config.status 用
        # (umask 077 && mktemp -d ./confXXXXXX) 在 cwd 建临时目录，随后往里写
        # subs*.awk 被 HMFS 拒绝（700 目录写受限；conf 目录不走 TMPDIR）。
        # configure 生成的 config.status 从其 here-doc 继承同样文本，把
        # configure 里的 umask 077 全部放宽为 022 即同步修复。
        configure_path = os.path.join(src, "configure")
        with open(configure_path, encoding="utf-8") as fh:
            configure_text = fh.read()
        if "umask 077" in configure_text:
            with open(configure_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(configure_text.replace("umask 077", "umask 022"))
        shared = "--enable-shared" if self.options.shared else "--disable-shared"
        static = "--disable-static" if self.options.shared else "--enable-static"
        self.run(
            f"./configure --build={triple} --host={triple} {shared} {static} "
            f"--without-python --disable-nls --without-zlib --prefix=/__pkg_prefix__",
            cwd=src,
        )
        # 只编 lib + util（po/doc/python/dicts 裁剪，SUBDIRS 运行期覆盖）
        self.run('make SUBDIRS="lib util" -j4', cwd=src)

        # 层1 上游工具链建典 + FascistCheck 语义断言（上游 check_PROGRAMS 为
        # stdin 交互驱动，发布包无自动化 check 脚本，等效覆盖其判据）
        # cracklib-format 首段是无条件 `gzip -cdf`：GNU gzip 的 -f 对
        # 非 gzip 输入原样穿透，而设备 gzip（toybox）不支持该语义 →
        # 报 "gzip: not gzip" 产空典（CI #43836 实测）。
        # dicts/cracklib-small 本身已是小写净词表，format 的规范化管道
        # （去注释/转小写/去空行）对它恒等，等效收敛为 sort -u。
        util = os.path.join(src, "util")
        libdir = os.path.join(src, "lib", ".libs")
        bf = self.build_folder
        self.run(
            f"LC_ALL=C sort -u {os.path.join(src, 'dicts', 'cracklib-small')} "
            f"| {os.path.join(util, 'cracklib-packer')} {os.path.join(bf, 'testdict')}"
        )
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        self.run(
            f"{cc} -O2 -I{os.path.join(src, 'lib')} "
            f"{os.path.join(self.export_sources_folder, 'test_cracklib_build.c')} "
            f"-L{libdir} -lcrack -Wl,-rpath,{libdir} -o {os.path.join(bf, 'test_cracklib_build')}"
        )
        self.run(f"./test_cracklib_build {os.path.join(bf, 'testdict')}", cwd=bf)

    def package(self):
        copy(self, "crack.h", src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING.LIB", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        for pat in ("*.a", "*.so", "*.so.*", "*.la"):
            copy(self, pat, src=os.path.join(self.source_folder, "lib", ".libs"),
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # .la 文件 libdir 硬编码会在消费时报错，剔除
        la = os.path.join(self.package_folder, "lib", "libcrack.la")
        if os.path.exists(la):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["crack"]
