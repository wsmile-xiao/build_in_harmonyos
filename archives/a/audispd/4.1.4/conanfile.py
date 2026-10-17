#!/usr/bin/env python3
"""Conan recipe for audispd 4.1.4 — Linux audit event dispatcher (C).

audispd 是 Linux audit 用户态（linux-audit/audit-userspace）的事件分发
守护进程组件（audisp/ 目录，audispd.c + libdisp 库 + audisp-* 插件），
Autotools 构建。依赖均为同仓库组件（libaudit/audisp 内部），无外部 conan
依赖；signalfd 鸿蒙 libc 提供；AF_UNIX 本地 socketpair（无特权端口依赖）。

OHOS 适配:
- configure 用 --build=aarch64-linux --host=aarch64-linux；
- 构建 audisp/（libdisp 守护进程库）与 audisp/plugins（audisp-af_unix
  等插件），headless 路径（守护进程逻辑 + 本地管道，无需特权端口）；
- 测试: test_package 验证 audisp-af_unix 等插件可执行存在并运行。
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain


class AudispdConan(ConanFile):
    name = "audispd"
    version = "4.1.4"
    description = "Linux audit event dispatcher daemon (audit-userspace audisp)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/linux-audit/audit-userspace"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # libtool 提供 libtoolize、automake 提供 aclocal（autoreconf 生成
        # configure 必需）——CI 环境两者均无（本地 ~/.local/bin 有但 CI
        # PATH 不含），制品仓 libtool/2.5.4 与 automake/1.18 有 armv8/OHOS
        # 二进制
        self.requires("libtool/2.5.4")
        self.requires("automake/1.18")

    def export_sources(self):
        # compat/audit_socket_compat.h（鸿蒙 socket 头冲突兼容）随配方传递
        copy(self, "compat/*", self.recipe_folder, self.export_sources_folder)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--build=aarch64-linux",
                "--host=aarch64-linux",
                # python3 bindings 需 swig（鸿蒙无）——禁用
                "--without-python3",
                # zos-remote 插件需 openldap（鸿蒙无）——禁用
                "--disable-zos-remote",
            ]
        )
        # 全局 -include compat 头（鸿蒙 sys/socket.h 与 linux/socket.h 的
        # sockaddr_storage 重定义冲突——所有编译单元统一跳过 linux/socket.h）
        # 根因：鸿蒙 sys/socket.h 的 sockaddr_storage 在 #ifndef __MUSL__ 内，
        # 编译未定义 __MUSL__ 导致 sys/socket.h 与 linux/socket.h 双定义——
        # 定义 __MUSL__（鸿蒙 libc 即 musl）让 sys/socket.h 跳过，仅保留
        # linux/socket.h 的定义。
        tc.cflags.append("-D__MUSL__")
        tc.generate()

    def build(self):
        # CFLAGS 用 os.environ 注入（configure 捕获进 Makefile）：
        # 鸿蒙 sys/socket.h 的 sockaddr_storage 在 #ifndef __MUSL__ 内，
        # 未定义 __MUSL__ 时与 linux/socket.h 双定义冲突——定义 __MUSL__
        # （鸿蒙 libc 即 musl）让 sys/socket.h 跳过，仅保留 linux/socket.h
        # 的定义。tc.cflags 在 configure 捕获 CFLAGS 时不生效，故用 os.environ。
        os.environ["CFLAGS"] = "-D__MUSL__"
        # TMPDIR 用 os.environ 注入（同 libgsf/bogofilter 教训）：CI 沙箱
        # TMPDIR=/data/storage/el2/base/cache 不可写——configure 的
        # config.status 用 ac_tmp 临时目录（confdXXXX/subs1.awk）写文件时
        # Permission denied。注入 build 目录内可写 .conan_tmp，configure
        # 子进程直接继承。
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        # libtool 包提供 libtoolize、automake 包提供 aclocal（autoreconf
        # 依赖）——把两者 bin 前置到 PATH（CI 环境 PATH 无这些工具）
        libtool_pkg = self.dependencies["libtool"].package_folder
        libtool_bin = os.path.join(libtool_pkg, "bin")
        if os.path.isdir(libtool_bin):
            os.environ["PATH"] = (
                libtool_bin + os.pathsep + os.environ.get("PATH", ""))
        automake_pkg = self.dependencies["automake"].package_folder
        automake_bin = os.path.join(automake_pkg, "bin")
        if os.path.isdir(automake_bin):
            os.environ["PATH"] = (
                automake_bin + os.pathsep + os.environ.get("PATH", ""))
        autotools = Autotools(self)
        # audit-userspace tarball 无顶层 configure（仅 configure.ac）——
        # 用 autoreconf 生成（鸿蒙 hnp/bin 提供 autoreconf/autoconf）
        autotools.autoreconf()
        # patch configure 脚本的 ac_tmp 创建逻辑：autoconf 默认
        # `mktemp -d "./confXXXXXX"`（当前目录创建新临时目录）——鸿蒙
        # 安全框架拦脚本子进程在新目录写文件（config.status 写
        # subs1.awk 时 Permission denied）。改为直接指向 build 目录内
        # 已存在的可写 .conan_tmp（不创建新子目录——libgsf 先例）。
        _cfg = os.path.join(self.source_folder, "configure")
        _actmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_actmp_dir, exist_ok=True)
        if os.path.isfile(_cfg):
            _c = open(_cfg).read()
            _n = _c.replace(
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                f'tmp="{_actmp_dir}"')
            if _n != _c:
                open(_cfg, "w").write(_n)
                self.output.info(
                    "patched configure: ac_tmp -> existing .conan_tmp")
        autotools.configure()
        # libaudit.h：鸿蒙 sys/socket.h:377 与 linux/socket.h:23 都定义
        # sockaddr_storage（重定义冲突）——预定义 _UAPI_LINUX_SOCKET_H 跳过
        # linux/socket.h 的 sockaddr_storage，并手动提供 netlink.h 需要的
        # __kernel_sa_family_t（原由 linux/socket.h 定义）
        libaudit_h = os.path.join(self.source_folder, "lib", "libaudit.h")
        content = load(self, libaudit_h)
        guard = (
            "#ifndef _UAPI_LINUX_SOCKET_H\n"
            "#define _UAPI_LINUX_SOCKET_H\n"
            "typedef unsigned short __kernel_sa_family_t;\n"
            "#endif\n"
        )
        fixed = content.replace(
            "#include <asm/types.h>", guard + "#include <asm/types.h>"
        )
        if fixed != content:
            save(self, libaudit_h, fixed)
            self.output.info("patched libaudit.h: skip linux/socket.h sockaddr_storage")
        # common/common.c：鸿蒙 utmpx.h 无 getutxent 声明（wall 广播功能
        # 不可用）——wall_message 跳过广播循环（headless 可选路径）
        common_c = os.path.join(self.source_folder, "common", "common.c")
        cc = load(self, common_c)
        cfixed = cc.replace(
            "\tsetutxent();\n\n\t// Send the message to all active users\n\twhile ((entry = getutxent())) {",
            "\tsetutxent();\n\n\t// OHOS: getutxent not available — skip wall\n\twhile (0) {",
        )
        if cfixed != cc:
            save(self, common_c, cfixed)
            self.output.info("patched common.c: skip wall broadcast (no getutxent)")
        # common/common.c：setutxent()/endutxent() 也移除（鸿蒙 utmpx.h 无
        # 这些函数，wall 广播完全禁用）
        cc2 = load(self, common_c)
        cfixed2 = cc2.replace("\tsetutxent();\n", "").replace(
            "\tendutxent();\n", "")
        if cfixed2 != cc2:
            save(self, common_c, cfixed2)
            self.output.info("patched common.c: drop setutxent/endutxent")
        # auparse/auparse.c：secure_getenv（鸿蒙无）→ getenv
        auparse_c = os.path.join(self.source_folder, "auparse", "auparse.c")
        ac = load(self, auparse_c)
        afixed = ac.replace("secure_getenv(", "getenv(")
        if afixed != ac:
            save(self, auparse_c, afixed)
            self.output.info("patched auparse.c: secure_getenv -> getenv")
        # 构建 lib/（libaudit.la，audisp 的 libdisp 依赖）→ audisp/（libdisp
        # 守护进程库 + libqueue）→ plugins（audisp-*）
        # make 命令行 CFLAGS 覆盖 Makefile 写死值（优先级最高）：
        # 全局 -include compat 头——预定义 _UAPI_LINUX_SOCKET_H 让
        # linux/socket.h 跳过（与 sys/socket.h 的 sockaddr_storage 双定义
        # 冲突，且 sys/socket.h 的定义是 netinet/in.h 需要的完整类型），
        # 并手动提供 netlink.h 需要的 __kernel_sa_family_t。
        # 注：不能用 -D__MUSL__（会让 sys/socket.h 跳过定义，
        # netinet/in.h 的 sockaddr_storage 变不完整类型报错）。
        # export_sources 自动放置 compat/ 到 source_folder——从那里取
        compat_h = os.path.join(self.source_folder, "compat",
                                "audit_socket_compat.h")
        mk_cflags = (
            f"-Wno-error=format-security -Wno-error=format -include {compat_h}"
        )
        # libtool 用 $TMPDIR 创建临时文件——鸿蒙 /tmp 只读（libtool 报
        # "can't create temporary file /tmp/xxx.tmp: Read-only file
        # system"）。make 命令行显式传 TMPDIR（make 变量优先级高，让
        # libtool 用可写 .conan_tmp）。
        tmp = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(tmp, exist_ok=True)
        # 依赖顺序（顶层 SUBDIRS = common lib auparse audisp auplugin）：
        # common/（libaucommon.la）→ lib/（libaudit.la）→ auparse/
        # （libauparse.la）→ audisp/（libqueue.la + libdisp.la）→ auplugin/
        # （libauplugin.la，依赖 audisp/libqueue.la + auparse/libauparse.la）
        # → audisp/plugins（audisp-*）
        self.run(f"make SHELL=/bin/sh TMPDIR='{tmp}' CFLAGS='{mk_cflags}' -C common",
                 cwd=self.source_folder)
        self.run(f"make SHELL=/bin/sh TMPDIR='{tmp}' CFLAGS='{mk_cflags}' -C lib",
                 cwd=self.source_folder)
        self.run(f"make SHELL=/bin/sh TMPDIR='{tmp}' CFLAGS='{mk_cflags}' -C auparse",
                 cwd=self.source_folder)
        self.run(f"make SHELL=/bin/sh TMPDIR='{tmp}' CFLAGS='{mk_cflags}' -C audisp",
                 cwd=self.source_folder)
        self.run(f"make SHELL=/bin/sh TMPDIR='{tmp}' CFLAGS='{mk_cflags}' -C auplugin",
                 cwd=self.source_folder)
        self.run(f"make SHELL=/bin/sh TMPDIR='{tmp}' CFLAGS='{mk_cflags}' -C audisp/plugins",
                 cwd=self.source_folder)

    def package(self):
        # 安装 audisp 插件可执行（audisp-af_unix 等）到 bin/
        plugins_dir = os.path.join(
            self.source_folder, "audisp", "plugins")
        dest = os.path.join(self.package_folder, "bin")
        os.makedirs(dest, exist_ok=True)
        for root, _, files in os.walk(plugins_dir):
            for f in files:
                if f.startswith("audisp-") and os.access(
                        os.path.join(root, f), os.X_OK):
                    src = os.path.join(root, f)
                    import shutil
                    shutil.copy2(src, os.path.join(dest, f))

    def package_info(self):
        self.cpp_info.libs = []
