#!/usr/bin/env python3
"""Conan recipe — dropbear 2025.88 (autotools)

轻量级 SSH2 服务器/客户端套件：服务端 dropbear、客户端 dbclient、密钥工具
dropbearkey 与格式转换工具 dropbearconvert。自包含 libtomcrypt/libtommath，
无外部 Conan 依赖；zlib 为可选特性，按 --disable-zlib 显式关闭（OHOS sysroot
同时存在 zlib.h 与 libz.so，configure 默认 auto 探测会链接未声明的系统
libz，见 notes.md 实测证据）。

HarmonyOS PC 适配要点（证据与完整过程见 notes.md）:
- autoconf 2.73 m4sh AS_TMPDIR 在 configure/config.status 中硬编码
  `(umask 077 && mktemp -d ./confXXXXXX)`；HMDFS 上 0700（组位缺失）目录
  拒绝写入，config.status 报 "can't create ./confXXXXXX/subs1.awk:
  Permission denied"（知识 E011/E136/E206，btparse 同款补丁先例）。
  补丁 0003 将该 umask 改为 022；本包 Makefile.in 无 configure 再生成
  maintainer 规则，补丁不会被静默回滚。
- OHOS libc 不提供 getpass()/getspnam()（sysroot 头文件有 shadow.h、
  struct spwd，但 libc 导出符号表中无这两个函数，configure 实测
  "checking for getpass... no / getspnam... no"）。补丁 0001/0002 依据
  configure 的 AC_CHECK_FUNCS 结果（HAVE_GETPASS/HAVE_GETSPNAM）做特性
  条件编译并提供等价 fallback，保持密码/键盘交互认证与 shadow 密码处理
  可编译可用（无 __OHOS__ 平台条件编译）。
- 显式 --build/--host 三元组跳过 config.guess 的 mktemp/dummy.c 探测
  （HMDFS 拒绝其探针写入，实测 "can't create .../dummy.c: Permission
  denied"）。选 aarch64-unknown-linux-musl：dropbear 自带 config.sub
  (2023-08-22) 接受该写法，拒收 *-linux-ohos。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DropbearConan(ConanFile):
    name = "dropbear"
    version = "2025.88"
    description = "Lightweight SSH2 server and client (dropbear, dbclient, dropbearkey, dropbearconvert)"
    license = "MIT-style (dropbear LICENSE; bundled libtomcrypt/libtommath under their own licenses)"
    homepage = "https://matt.ucc.asn.au/dropbear/dropbear.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _configure_args(self):
        args = [
            # zlib 显式关闭：避免 configure auto 探测链接未声明的系统 libz
            # （sysroot 实测存在 zlib.h + libz.so，默认构建产物 NEEDED 含
            # libz.so；关闭后产物仅依赖 libc.so）。
            "--disable-zlib",
        ]
        if str(self.settings.os) == "OHOS":
            # 跳过 config.guess 的 HMDFS 不兼容探测（见模块 docstring）。
            # 追加在 toolchain 自动参数之后，autoconf 取最后一个取值。
            args.append("--build=aarch64-unknown-linux-musl")
            args.append("--host=aarch64-unknown-linux-musl")
        return args

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure(args=self._configure_args())
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # 应用包：仅发布可执行文件。Conan AutotoolsToolchain 默认将
        # --sbindir 指向 ${prefix}/bin，四个命令实际都落在 bin/
        # （缓存产物清单见 notes.md）。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "dropbear")
