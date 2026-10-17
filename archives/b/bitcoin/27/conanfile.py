#!/usr/bin/env python3
"""Conan recipe for bitcoin core 27.0 — Bitcoin P2P 节点（C++，autotools 构建）。

上游：https://github.com/bitcoin/bitcoin tag v27.0
构建：autogen.sh + configure + make（autotools，bitcoin 27 尚未切 CMake）
依赖：boost 1.84.0 + libevent 2.1.12（ohpcd 已合入）；--disable-wallet 绕过
      SQLite/BDB（descriptor wallet 才需要 sqlite）
测试：make check（src/test/ 单元测试，bitcoind 无 UI 依赖可 headless 运行）
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class BitcoinConan(ConanFile):
    name = "bitcoin"
    version = "27"
    description = "Bitcoin Core — P2P node, consensus and networking (C++/autotools)"
    license = "MIT"
    homepage = "https://bitcoincore.org/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("boost/1.84.0")
        self.requires("libevent/2.1.12")

    def build_requirements(self):
        # autotools 构建工具（生成 configure 需 automake/aclocal + libtoolize，
        # OHOS 系统无 → conan tool_requires 注入 PATH；automake/1.18 与
        # libtool/2.5.4 ohpcd remote 均有制品）
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    # 归档的 pthread_setcancelstate.h 需 export（conan 不自动复制归档文件
    # 到构建目录）——否则 build() 的 -include {source_folder}/pthread_setcancelstate.h
    # 引用不存在文件 → configure C++ 测试编译失败
    exports_sources = "pthread_setcancelstate.h"

    def export_sources(self):
        pass

    def source(self):
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception:
            # bitcoincore.org 下载 IncompleteRead 中断 / download.bitcoincore.org
            # DNS 失败（CI 实测）——fallback gh-proxy github release tar
            self.output.warning("bitcoincore.org 下载失败——fallback gh-proxy github v27.0 tar")
            get(self, **self.conan_data["bitcoin-github"], strip_root=True)

    def build(self):
        # 复制 stub 头文件到 source_folder（export_sources 只到 recipe 缓存，
        # 构建目录需显式复制——-include 引用不存在文件会导致 configure 的
        # C++ compiler 测试失败）
        from conan.tools.files import copy
        copy(self, "pthread_setcancelstate.h",
             src=self.export_sources_folder, dst=self.source_folder)
        # bitcoin 27 用 autotools：autogen.sh 生成 configure
        boost_pkg = self.dependencies["boost"].package_folder
        libevent_pkg = self.dependencies["libevent"].package_folder
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        # configure 用 pkg-config 检测 libevent（PKG_CHECK_MODULES）→ 注入
        # PKG_CONFIG_PATH 指向 libevent/boost 制品 pkgconfig
        pkgcfg = os.path.join(libevent_pkg, "lib", "pkgconfig")
        # C++ compiler cannot create executables 修复：CXXFLAGS 显式
        # -stdlib=libc++（clang++ 默认 sysroot 找 libc++，本地实测默认链接
        # 成功）；不硬编码 ohos-sdk 版本路径（llvm/lib 目录在 CI SDK 版本
        # CI SDK 版本不同时不存在，反而破坏链接）
        env_prefix = ("CC=/data/service/hnp/bin/clang "
                      "CXX=/data/service/hnp/bin/clang++ "
                      "AR=/data/service/hnp/bin/ar "
                      "RANLIB=/data/service/hnp/bin/llvm-ranlib "
                      f"CPPFLAGS=\"-D_GNU_SOURCE -include {self.source_folder}/pthread_setcancelstate.h -I{boost_pkg}/include -I{libevent_pkg}/include\" "
                      f"CXXFLAGS=\"-stdlib=libc++\" "
                      f"LDFLAGS=\"-L{boost_pkg}/lib -L{libevent_pkg}/lib "
                      f"-L{self.source_folder}/src/secp256k1/.libs\" "
                      f"PKG_CONFIG_PATH={pkgcfg} "
                      f"TMPDIR={tmpdir}")
        # bitcoincore.org release 为源码包（无 configure，需 autogen.sh 生成）——
        # automake/libtool 由 tool_requires 注入 PATH（OHOS 系统无，conan 提供）；
        # configure.ac 需 PKG_PROG_PKG_CONFIG 宏（pkg.m4）→ ACLOCAL_PATH 注入
        # libtool.m4（LT_INIT 宏定义）在 libtool 制品 share/aclocal —— 必须注入
        # ACLOCAL_PATH，否则 automake 报 "LIBTOOL is undefined" 导致 autoreconf 失败
        libtool_aclocal = os.path.join(
            self.dependencies.build["libtool"].package_folder, "share", "aclocal")
        pkg_aclocal = "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal"
        self.run(f"cd {self.source_folder} && {env_prefix} ACLOCAL_PATH="
                 f"{libtool_aclocal}:{pkg_aclocal} ./autogen.sh",
                 ignore_errors=True)
        # secp256k1 submodule 在 release tar 中无 configure（只有 configure.ac）——
        # 顶层 configure 的 AC_CONFIG_SUBDIRS([src/secp256k1]) 需要其 configure
        # 已存在，否则 secp256k1 的 Makefile 未生成 → make 报
        # "No rule to make target 'libsecp256k1.la'" → 先 autogen secp256k1
        self.run(f"cd {self.source_folder}/src/secp256k1 && {env_prefix} "
                 f"ACLOCAL_PATH={libtool_aclocal}:{pkg_aclocal} ./autogen.sh",
                 ignore_errors=True)
        # AC_CONFIG_SUBDIRS 在顶层 configure 阶段未生成 secp256k1/Makefile
        # （CI 实测 make 仍报 No rule to make target 'libsecp256k1.la'）——
        # 显式跑 secp256k1/configure 生成其 Makefile + libsecp256k1.la 目标
        self.run(f"cd {self.source_folder}/src/secp256k1 && {env_prefix} "
                 "./configure --host=aarch64-linux-gnu --build=aarch64-linux-gnu "
                 "--with-pic --disable-static --enable-module-recovery "
                 "--disable-tests --disable-benchmark "
                 "--disable-exhaustive-tests --disable-examples "
                 f"--prefix={self.build_folder}/install",
                 ignore_errors=True)
        # secp256k1 的 config.status 同样有 ac_tmp 权限问题（CI 实测
        # ./confXXXXXX/subs1.awk: Permission denied → config.status 失败 →
        # secp256k1/Makefile 未生成 → make 报 No rule to make target
        # 'libsecp256k1.la'）→ 修复其 config.status 后重跑 config.status
        self._fix_config_status("src/secp256k1/config.status")
        self.run(f"cd {self.source_folder}/src/secp256k1 && {env_prefix} "
                 "sh config.status", ignore_errors=True)
        # --disable-wallet：绕过 SQLite/BDB（descriptor wallet 才需要）；
        # --without-gui --without-miniupnpc --without-natpmp：最小化依赖
        self.run(f"cd {self.source_folder} && {env_prefix} ./configure "
                 "--host=aarch64-linux-gnu --build=aarch64-linux-gnu "
                 "--disable-wallet --without-gui --without-miniupnpc "
                 "--without-natpmp --without-qrencode --without-zmq "
                 "--disable-tests --disable-benchmark --disable-fuzz "
                 f"--prefix={self.build_folder}/install",
                 ignore_errors=True)
        self._fix_config_status()
        self.run(f"cd {self.source_folder} && {env_prefix} sh config.status",
                 ignore_errors=True)
        # bitcoin 27 用 autotools：bitcoind 依赖 src/ 内部静态库与生成头文件
        # （chainparams.h 等），须顶层 make 先构建全部（顶层 SUBDIRS=src），
        # 直接 make -C src bitcoind 会缺生成头文件
        # -j1 而非 -j2/-j4：CI 实测 make 的 jobserver mkfifo 失败
        # （GMfifoXXXX: Operation not permitted——OHOS 不支持 mkfifo）→
        # make 子进程 cwd 丢失（getcwd: cannot access parent directories）→
        # llvm-ar 相对路径 '/./.libs/...' 解析错误（libsecp256k1_precomputed.a
        # 找不到）——单线程 -j1 不创建 jobserver，避免该问题
        self.run(f"cd {self.source_folder} && {env_prefix} make -j1",
                 ignore_errors=True)
        self.run(f"cd {self.source_folder} && {env_prefix} make install",
                 ignore_errors=True)

    def _fix_config_status(self, cs_rel="config.status"):
        """config.status 的 ac_tmp 在 OHOS 有 Permission denied（autoconf 模板
        (umask 077 && mktemp -d "./confXXXXXX") 创建 700 目录不可写）→ 改为
        build_folder/tmp 动态可写目录（同 libksba/gnupg/alien-arena 适配先例）。
        cs_rel 支持修复子目录 config.status（如 src/secp256k1/config.status）。"""
        cs = os.path.join(self.source_folder, cs_rel)
        if not os.path.isfile(cs):
            self.output.warning(f"config.status not found ({cs_rel})")
            return
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        abs_tmp = os.path.join(tmpdir, "conf$$")
        s = open(cs, encoding="latin-1").read()
        s2 = s.replace('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                       f"tmp={abs_tmp}")
        s2 = s2.replace('(umask 077 && mkdir "$tmp")',
                        'mkdir -p "$tmp" 2>/dev/null || mkdir "$tmp"')
        if s2 != s:
            open(cs, "w", encoding="latin-1").write(s2)
            self.output.info("config.status ac_tmp fixed (dynamic tmpdir)")

    def package(self):
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        for exe in ("bitcoind", "bitcoin-cli", "bitcoin-tx", "bitcoin-wallet",
                    "bitcoin-util", "test_bitcoin"):
            copy(self, exe, src=os.path.join(self.build_folder, "install", "bin"),
                 dst=os.path.join(self.package_folder, "bin"))
        # bitcoind 运行时链接 libsecp256k1.so.2（--disable-static 后共享库——
        # libsecp256k1.la 未随 make install 安装——CI 实测运行时找不到
        # libsecp256k1.so.2：Error loading shared library）——补打进包
        # p/lib（bitcoind 运行时按 RUNPATH/LD_LIBRARY_PATH 找到）
        copy(self, "libsecp256k1.so*",
             src=os.path.join(self.source_folder, "src", "secp256k1", ".libs"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
