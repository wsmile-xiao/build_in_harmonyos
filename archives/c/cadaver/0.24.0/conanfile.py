#!/usr/bin/env python3
"""Conan recipe for cadaver 0.24.0 — WebDAV command-line client (autotools).

cadaver is a CLI WebDAV client for Unix, built with autotools. Depends on
neon (WebDAV library). The configure script finds neon via --with-neon=DIR
(NEON_WITH_LIBS macro). No upstream test suite (tar tzf verified: only
autoconf m4 macros, no real tests).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy


class CadaverConan(ConanFile):
    name = "cadaver"
    version = "0.24.0"
    package_type = "application"
    description = "Command-line WebDAV client for Unix"
    license = "GPL-2.0-or-later"
    homepage = "https://notroj.github.io/cadaver/"
    url = ""
    settings = "os", "arch", "compiler", "build_type"
    requires = "neon/0.34.0", "expat/2.8.2"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"]["cadaver"], strip_root=True)

    def build(self):
        # E007/E011（同 neon 0.34 配方）：config.guess 识别 OHOS + 非
        # HMDFS work 权限放开
        work = self.source_folder
        os.system(f"chmod -R 777 {work}")
        neon = self.dependencies["neon"].package_folder
        expat = self.dependencies["expat"].package_folder
        # neon.m4 用 bin/neon-config 脚本检查 neon（conan neon package 未装
        # 该脚本——'could not use external neon library' 实测）——patch
        # configure：libneon.a 存在即 found（NEON_USE_EXTERNAL 调用
        # neon-config 返回空——CFLAGS/LIBS 由配方 CPPFLAGS/LDFLAGS/LIBS
        # 提供）
        cfg = os.path.join(work, "configure")
        cs = open(cfg).read()
        _old = "if test -x ${NEON_CONFIG}; then"
        _new = "if test -x ${NEON_CONFIG} -o -f ${neon_ext_path}/lib/libneon.a; then"
        if _old in cs:
            cs = cs.replace(_old, _new)
            open(cfg, "w").write(cs)
            self.output.info("configure neon check patched (libneon.a)")
        else:
            self.output.warning("configure neon check pattern not found")
        # 沙箱不能运行 configure 测试程序——cross.cache 预置
        # （ac_cv_ 前缀变量才被 autoconf cache 加载——ne_cv_ 前缀需
        # 环境变量传递：configure 的 off64_t printf 格式检测（运行测试
        # 程序）在沙箱失败——'incompatible neon library version' 实为
        # ne_cv_fmt_off64_t=none（非 neon 版本问题）——aarch64 上
        # off64_t=long long 用 %lld——环境变量预置跳过运行检测）
        with open(os.path.join(work, "cross.cache"), "w") as f:
            # ac_cv_prog_cc_works + ac_cv_prog_cc_cross 同时预置（#6257
            # 教训：autoconf AC_PROG_CC 先查 works 再查 cross——只预置
            # cross 不够——沙箱无法运行 conftest 报 cannot run C compiled
            # programs 实测）
            f.write("ac_cv_prog_cc_works=yes\n")
            f.write("ac_cv_prog_cc_cross=yes\n")
        # NEON_USE_EXTERNAL 调用 $NEON_CONFIG --version/--cflags/--libs
        # （conan neon package 未装 neon-config 脚本——ne_libver 空 →
        # 版本匹配失败实测）——生成 neon-config 脚本 + patch configure：
        # 1) NEON_CONFIG 路径指向生成的脚本；2) 版本 wanted 列表加 33/34
        # （cadaver 0.24 支持 0.27-0.32，neon 0.34 API 向后兼容实测编译）
        _ncfg = os.path.join(work, "neon-config")
        with open(_ncfg, "w") as _f:
            _f.write(
                '#!/bin/sh\n'
                f'case "$1" in\n'
                f'  --prefix) echo "{neon}" ;;\n'
                f'  --cflags) echo "-I{neon}/include -I{neon}/include/neon" ;;\n'
                f'  --libs) echo "-L{neon}/lib -lneon" ;;\n'
                f'  --version) echo "0.34.0" ;;\n'
                f'esac\n')
        os.chmod(_ncfg, 0o755)
        _cfg = os.path.join(work, "configure")
        _cs = open(_cfg).read()
        _cs = _cs.replace(
            'NEON_CONFIG="$neon_ext_path/bin/neon-config"',
            f'NEON_CONFIG="{_ncfg}"')
        _cs = _cs.replace(
            "for v in 27 28 29 30 31 32; do",
            "for v in 27 28 29 30 31 32 33 34; do")
        # E011（同 neon 0.34 配方）：config.status 生成的 subs1.awk 无 x 位
        # （重定向 666——umask 无法给 x——exec Permission denied 实测）——
        # 生成后 chmod +x + umask 000（临时目录 700 属主问题同族）
        _cs = _cs.replace(
            "echo 'BEGIN {' >\"$ac_tmp/subs1.awk\" &&",
            "echo 'BEGIN {' >\"$ac_tmp/subs1.awk\" &&\n"
            "chmod +x \"$ac_tmp/subs1.awk\" &&")
        _cs = _cs.replace("umask 077", "umask 000")
        open(_cfg, "w").write(_cs)
        self.output.info("configure neon-config + version list patched")
        # config.guess 无法识别 OHOS（uname -s=HarmonyOS 不在 Linux|GNU
        # 分支——'cannot guess build type' 实测——E007）——内联 patch：
        # HarmonyOS → ${UNAME_MACHINE}-unknown-linux-ohos（cadaver 的
        # config.guess 无 GUESS= 变量——旧版格式——各分支 echo+exit）
        _cg = os.path.join(work, "config.guess")
        _cs = open(_cg).read()
        _old = 'case "$UNAME_SYSTEM" in'
        _new = ('case "$UNAME_SYSTEM" in\n'
                'HarmonyOS)\n'
                '    echo ${UNAME_MACHINE}-unknown-linux-ohos\n'
                '    exit ;;\n')
        if _old in _cs:
            _cs = _cs.replace(_old, _new, 1)
            open(_cg, "w").write(_cs)
            self.output.info("config.guess HarmonyOS patched")
        else:
            self.output.warning("config.guess pattern not found")
        self.run(
            f"umask 0 && ne_cv_fmt_off64_t=lld ./configure "
            f"--cache-file={work}/cross.cache "
            f"--host=aarch64-unknown-linux-ohos "
            f"--build=aarch64-unknown-linux-gnu "
            f"--with-neon={neon} "
            f"--prefix={self.package_folder} "
            f"CPPFLAGS=\"-I{neon}/include -I{neon}/include/neon "
            f"-I{expat}/include\" "
            f"LDFLAGS=\"-L{neon}/lib -L{expat}/lib\" "
            f"LIBS=\"-lneon -lexpat\" "
            # CI worker 沙箱禁止生成/运行 conftest 可执行文件 →
            # 'checking whether the C compiler works... no'（#30663 实测，
            # 同 speex 先例）——configure 命令行 cache 变量强制跳过该
            # 运行检查（cadaver 0.24 configure 无 ac_cv_prog_cc_works
            # 变量定义——cross.cache 预置无效实测——VAR=value 命令行
            # cache 变量可靠——speex 1.2.1 main 先例）
            f"ac_cv_prog_cc_works=yes ac_cv_prog_cc_cross=yes",
            cwd=work)
        self.run("make -j1", cwd=work)

    def package(self):
        work = self.source_folder
        # cadaver 可执行文件在构建根目录（make 顶层生成——实测 b/cadaver，
        # 非 src/.libs——libtool 未启用）
        bin_src = os.path.join(work, "cadaver")
        if not os.path.exists(bin_src):
            for cand in (os.path.join(work, "src", ".libs", "cadaver"),
                         os.path.join(work, "src", "cadaver")):
                if os.path.exists(cand):
                    bin_src = cand
                    break
        if not os.path.exists(bin_src):
            raise Exception(f"cadaver binary not found under {work}")
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        copy(self, os.path.basename(bin_src), src=os.path.dirname(bin_src),
             dst=bin_dst)

    def package_info(self):
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
        self.output.info(f"cadaver bin: {os.path.join(self.package_folder, 'bin')}")
