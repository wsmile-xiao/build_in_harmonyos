#!/usr/bin/env python3
"""Conan recipe — coinor-symphony 5.7.2（COIN-OR 分支定价 MILP 求解框架，autoconf 2.59）。

集成形态（W0 实核 + 原生探索 2026-09-23，证据全在 $TASK_DIR）：
- 版本面：上游 tag `releases/5.7.2`（git ls-remote 实证
  380996ca2800730edcac283eaecea5d046a4698b，w0/w0-checks.md W0-1a）；发行物取官方
  tag 归档 https://github.com/coin-or/SYMPHONY/archive/refs/tags/releases/5.7.2.tar.gz
  sha256=0807187a907027590fb860454b20cfde29dd61a2ce21b8af6be2ece4327955da——三处同源
  全等（w0 下载件 / init-build .tarball-sha256 / init-build 落盘副本，W0-1b）；
  同源检测未被已适配版本占用（W0-1c RC=1）。
- 硬依赖五枚全部 ohpcd 在档（conan list 逐一实查 + 双 profile `-pr:h/-pr:b` 双传
  绝对路径 `conan install --build=missing` rc=0，W0-2）：coinutils/2.11.13、
  coin-or/0.108.12（即 Osi）、clp/1.17.10、cgl/0.60.10.1、zlib/1.3.1——闭包钉版与
  coinor-cbc 2.10.13 完全一致（cgl→clp→coin-or→coinutils 同源）。
- 顶层 configure 仅做子包编排（AC_COIN_MAIN_PACKAGEDIR + subdirs 循环，
  configure.ac:98）→ 直接驱动 <src>/SYMPHONY/configure（coinor-cbc 同款口径：
  少一层 autoconf 脆弱面；顶层 configure 与 SYMPHONY/configure 均为 autoconf 2.59）。
- 依赖注入 **flags 模式**（coinor 家族口径）：已发布包 prefix=/ 固化在 .pc、pkg-config
  路径不可用 → --with-<pkg>-incdir / --with-<pkg>-lib 显式注入；incdir 只收单目录而
  四包头分居各自 include/coin → generate() 合并成单一 coin-include staging；闭包链接
  串用**直接 .a 绝对路径**（.la 文件 libdir='//' 会让 libtool 解析报
  "not a valid libtool archive"，coinor-cbc 探索轮实测）。
- 测试数据：--with-sample-datadir=Data-Sample 1.2.13（官方 coin-or-tools 仓库 tag
  归档，sha256 cb4c3713…06c9 与 coinor-cbc/coin-osi 同钉版）激活 COIN_HAS_SAMPLE →
  `make test` 的 unitTest 取 -mpsDir 跑上游断言面（explore-test.log 实测
  Severity PASSED 412 / ERROR 0 / "All tests completed successfully" / TEST_RC=0）；
  test 目标自带 `-miplib3Dir=`（空值显式关 MIPLIB3 面）、Netlib 未配置（上游自报
  Skipped Testing of OsiSymSolverInterface on Netlib problems）——两面未运行在
  notes/PR 正文如实申报。
- HMDFS 双修（E114 / DRAFT-E678 同族，**build() 内 seds、不登记源补丁**——
  sollya E678 正解口径「生成物不进 git，留痕 conanfile 同名函数，免 refresh-patch」）：
  ① 老 config.sub 无 musl 词表：`--build=aarch64-unknown-linux-musl`（coinor-cbc 可用
  的值）在此报 `Invalid configuration 'aarch64-unknown-linux-musl': machine
  'aarch64-unknown-linux' not recognized` → 用原生探索已验证的
  `--build=aarch64-unknown-linux-gnu`（CONFIGURE_RC=0）；
  ② autoconf 2.59 config.status 的 `(umask 077 && mktemp -d -q "./confstatXXXXXX")`
  在 HMDFS 落盘 2700 后不可写（探索期 explore-configure2.log 逐字
  `./confstatXXXXXX/out: Permission denied`，手工三轮 config-status-fix{,2,3} 收敛、
  fix3 无错误收尾）→ **configure 之前**对生成器 configure 做四处替换
  （umask 077→022、mktemp→固定 ./conftmp、fallback confstat$$-$RANDOM→./conftmp、
  mkdir→mkdir -p），AC_OUTPUT 内跑的 config.status 与生成出的 config.status 即继承
  修复；configure 之后对 config.status 再幂等补一遍（strict=False，未命中即跳过）。
- R33 / coinor 家族当日铁律：configure 调用处**显式钉死**
  CFLAGS/CXXFLAGS='-O3 -pipe -DNDEBUG'（= 原生探索已验证配置的优化基座，config.log
  1047 行实测同值），防 CI worker 泄漏 `-fPIC -O2`（无 -DNDEBUG）——coinor-cbc
  !11827 教训：泄漏值使 `#ifdef NDEBUG` 编译期分叉 → 设备跳过、CI 执行 ositests
  Segfault。钉死后 CI/W3/设备三方同源。
- 测试驱动：`make -j1 test`（MAKEFLAGS='' 单线程规避 HMDFS libtool .lo 并发截断，
  coinor-cbc 同款）；运行前 binary-sign-tool 自签 src/symphony、test/unitTest、
  test/punitTest（否则加载器 EPERM；探索 run-test.sh 同序实测）。
- 交付：bin/symphony（CLI：-F 读 MPS、-L 读 LP——探索实测 -F 收 LP 文件报
  "Errors in reading mps file" 退出 -122，test_package 走 -L）、lib/libSym.a +
  libOsiSym.a、include/coin/*.hpp、symphony/osi-sym .pc、share/coin/doc。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)


# ── 钉死的构建标志（R33 / coinor 家族当日铁律）──────────────────────────
# 设备已验证配置基座（原生探索 config.log CFLAGS='-O3 -pipe -DNDEBUG …'）。
# 防 CI worker 环境泄漏 -fPIC -O2（无 -DNDEBUG）造成编译期 #ifdef NDEBUG 分叉。
_CFLAGS_PIN = "-O3 -pipe -DNDEBUG"
_CXXFLAGS_PIN = "-O3 -pipe -DNDEBUG"


class CoinorSymphonyConan(ConanFile):
    name = "coinor-symphony"
    version = "5.7.2"
    description = "COIN-OR MILP solver framework with branch-cut-and-price (symphony)"
    license = "EPL-1.0"  # 上游 LICENSE = Eclipse Public License -v 1.0
    homepage = "https://github.com/coin-or/SYMPHONY"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 库（libSym.a / libOsiSym.a，静态交付同族）+ CLI 求解器 bin/symphony
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 与已发布闭包完全同钉版（cgl/0.60.10.1 → clp/1.17.10 → coin-or/0.108.12 →
        # coinutils/2.11.13），任何一侧改版都会造成双版本图；口径与 coinor-cbc 一致：
        # 公共头裸引用 Osi/CoinUtils/Clp 头 → transitive_headers=True；静态交付要求
        # 消费者拿到完整静态闭包 → transitive_libs=True。
        self.requires("coinutils/2.11.13", transitive_headers=True, transitive_libs=True)
        self.requires("coin-or/0.108.12", transitive_headers=True, transitive_libs=True)
        self.requires("clp/1.17.10", transitive_headers=True, transitive_libs=True)
        self.requires("cgl/0.60.10.1", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1", transitive_libs=True)

    def layout(self):
        # HMDFS 上 autotools 不支持 out-of-source（config.status 临时文件），
        # 与同族 coinutils/clp/coinor-cbc 一律 in-source：全部步骤显式 cd
        # source_folder/SYMPHONY。
        pass

    def source(self):
        data = self.conan_data["sources"]
        get(self, data["url"], sha256=data["sha256"], strip_root=True)
        # 官方测试数据包（make test 的 -mpsDir 数据面，激活 COIN_HAS_SAMPLE）
        get(self, data["data_sample"]["url"], sha256=data["data_sample"]["sha256"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "data-stage", "Sample"))

    def generate(self):
        # 合并 include staging：四个依赖包统一安装到各自 include/coin，configure 的
        # --with-*-incdir 只接受单目录 → 合并成一份（coinor-cbc 同款；HMDFS 硬链接
        # 不可用，逐文件拷贝）。
        self._coin_include = os.path.join(self.generators_folder, "coin-include")
        for name in ("coinutils", "coin-or", "clp", "cgl"):
            inc = os.path.join(self.dependencies[name].package_folder, "include", "coin")
            if os.path.isdir(inc):
                copy(self, "*", src=inc, dst=self._coin_include)
        self._deps = {
            name: self.dependencies[name].package_folder
            for name in ("coinutils", "coin-or", "clp", "cgl", "zlib")
        }

    # ── OHOS ELF 自签（coinor-cbc 同款口径）──────────────────────────────
    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not (os.path.isfile(signer) and os.path.isfile(readelf)):
            raise ConanException("required OHOS signing tools are missing")
        if not os.path.isfile(path):
            return
        output = path + ".signed"
        if os.path.lexists(output):
            os.unlink(output)
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True, timeout=120,
        )
        sections = subprocess.run(
            [readelf, "-SW", output], check=True, capture_output=True, text=True, timeout=60,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def _fix_hmdfs_scripts(self, src):
        """E165/E160：shebang 与 config.guess 的 HarmonyOS 修复（coinor-cbc 同款）。"""
        _config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        _ohos_shell = os.environ.get("OHOS_SHELL", "/system/bin/sh")
        for d in (src, os.path.join(src, "SYMPHONY")):
            for script in ("configure", "install-sh", "config.sub",
                           "config.guess", "ltmain.sh", "missing", "depcomp"):
                sp = os.path.join(d, script)
                if not os.path.exists(sp):
                    continue
                self.run(f"sed -i '1s|#!/bin/bash|#!{_config_shell}|' '{sp}'")
                self.run(f"sed -i '1s|#!/bin/sh|#!{_ohos_shell}|' '{sp}'")
                self.run(f"sed -i '1s|#! /bin/sh|#!{_ohos_shell}|' '{sp}'")
        # config.guess 的 HarmonyOS 分支（--build 显式给出时不会触发，防御性保留）
        for d in (src, os.path.join(src, "SYMPHONY")):
            guess = os.path.join(d, "config.guess")
            if os.path.exists(guess):
                self.run(r"""sed -i '/^case $UNAME_SYSTEM in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """ + f"'{guess}'")
                self.run(r"""sed -i '/^case "${UNAME_SYSTEM}" in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """ + f"'{guess}'")

    # ── HMDFS config.status 修复（E114 / DRAFT-E678 同族）────────────────
    # autoconf 2.59 生成器内嵌三处临时目录逻辑：
    #   tmp=`(umask 077 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null` &&
    #   tmp=./confstat$$-$RANDOM                        （mktemp 不可用时的 fallback）
    #   (umask 077 && mkdir $tmp)
    # HMDFS 把 umask 077 的目录按共享属主落成 2700，写 subs/stdout 全部
    # Permission denied（探索期 explore-configure2.log 逐字实测；手工三轮
    # config-status-fix{,2,3} 收敛、fix3 无错误收尾为修法实证）。
    # 在 configure **之前**改生成器，AC_OUTPUT 内联跑的与生成出的 config.status
    # 即同时继承修复；configure 之后对 config.status 幂等补一遍兜底。
    def _fix_config_tmp_mechanism(self, path):
        if not os.path.exists(path):
            return
        edits = (
            ('umask 077 && mktemp -d -q "./confstatXXXXXX"',
             'umask 022 && mkdir -p ./conftmp'),
            ("tmp=./confstat$$-$RANDOM",
             "tmp=./conftmp"),
            ("umask 077 && mkdir $tmp",
             "umask 022 && mkdir -p $tmp"),
            ("umask 077",   # 残余（若有）一并剥掉，coinor-cbc sed -g 同款
             "umask 022"),
        )
        for search, repl in edits:
            try:
                replace_in_file(self, path, search, repl, strict=True)
            except ConanException:
                # strict 未命中 = 该形态不存在（不同 autoconf 版本形态差异/已修过）
                pass

    def build(self):
        apply_conandata_patches(self)  # patches: {} — 幂等空操作，保留防御
        src = self.source_folder
        sym_dir = os.path.join(src, "SYMPHONY")
        gen = self.generators_folder
        # HMDFS：TMPDIR 必须指向可写目录（设备 HiShell 注入值不可信，设备边界 §一.12）
        _tmpdir = os.environ.get("TMPDIR") or os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
        os.makedirs(_tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = _tmpdir
        os.environ["TMP"] = _tmpdir

        self._fix_hmdfs_scripts(src)
        # 修生成器 configure（先于 configure 运行），再清残留临时目录
        self._fix_config_tmp_mechanism(os.path.join(sym_dir, "configure"))
        self.run(f"cd '{sym_dir}' && rm -rf conftmp confstat*")

        d = self._deps
        inc = self._coin_include
        data_sample = os.path.join(src, "data-stage", "Sample")
        # 闭包用**直接 .a 路径**而非 -L/-l：依赖包 .la 固化 libdir='//'（prefix=/），
        # libtool 读到会报 "not a valid libtool archive"（coinor-cbc 探索轮实测）。
        closure = (f"{d['cgl']}/lib/libCgl.a {d['coin-or']}/lib/libOsi.a "
                   f"{d['coinutils']}/lib/libCoinUtils.a {d['zlib']}/lib/libz.a -lm")
        clp_lib = (f"{d['clp']}/lib/libOsiClp.a {d['clp']}/lib/libClpSolver.a "
                   f"{d['clp']}/lib/libClp.a {closure}")
        coinutils_lib = f"{d['coinutils']}/lib/libCoinUtils.a {d['zlib']}/lib/libz.a -lm"
        osi_lib = f"{d['coin-or']}/lib/libOsi.a {d['coinutils']}/lib/libCoinUtils.a {d['zlib']}/lib/libz.a -lm"
        ositests_lib = f"{d['coin-or']}/lib/libOsiCommonTests.a {closure}"
        _cc = os.environ.get("CC", "clang")
        _cxx = os.environ.get("CXX", "clang++")
        # R33 同款纪律：编译 flags 显式钉死、不继承未定义 shell 变量（防 CI 泄漏
        # -fPIC -O2 无 -DNDEBUG → #ifdef NDEBUG 编译期分叉，coinor-cbc !11827 教训）。
        # --build 用 -gnu：老 config.sub 无 musl 词表，-musl 报 Invalid configuration。
        self.run(
            f"cd '{sym_dir}' && . {gen}/conanbuild.sh && "
            f"CC={_cc} CXX={_cxx} TMPDIR={_tmpdir} "
            f"CFLAGS='{_CFLAGS_PIN}' CXXFLAGS='{_CXXFLAGS_PIN}' "
            f"./configure --prefix=/ "
            f"--build=aarch64-unknown-linux-gnu "
            f"--enable-static --disable-shared --disable-dependency-tracking "
            f"--with-coinutils-lib='{coinutils_lib}' "
            f"--with-coinutils-incdir='{inc}' "
            f"--with-osi-lib='{osi_lib}' "
            f"--with-osi-incdir='{inc}' "
            f"--with-clp-lib='{clp_lib}' "
            f"--with-clp-incdir='{inc}' "
            f"--with-cgl-lib='{closure}' "
            f"--with-cgl-incdir='{inc}' "
            f"--with-ositests-lib='{ositests_lib}' "
            f"--with-ositests-incdir='{inc}' "
            f"--with-sample-datadir='{data_sample}'",
            env="conanbuild",
        )
        # 兜底：生成出的 config.status 幂等补一遍（未命中形态自动跳过）并清残留
        self._fix_config_tmp_mechanism(os.path.join(sym_dir, "config.status"))
        self.run(f"cd '{sym_dir}' && rm -rf conftmp confstat*")

        # R33：MAKEFLAGS='' 单线程规避 HMDFS 对 libtool .lo 的并发截断（§一.7/§一.13）
        self.run(f"cd '{sym_dir}' && . {gen}/conanbuild.sh && "
                 f"CC={_cc} CXX={_cxx} TMPDIR={_tmpdir} "
                 f"CFLAGS='{_CFLAGS_PIN}' CXXFLAGS='{_CXXFLAGS_PIN}' "
                 f"MAKEFLAGS='' make -j1", env="conanbuild")

        # ── 上游测试（test/Makefile.am 的 `test:` 目标 → unitTest）────────
        if not can_run(self):
            self.output.warning("Cannot run the upstream SYMPHONY test suite on this host")
            return
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(os.path.join(sym_dir, "src", "symphony"))
            self._sign_ohos_elf(os.path.join(sym_dir, "test", "unitTest"))
            self._sign_ohos_elf(os.path.join(sym_dir, "test", "punitTest"))
        self.run(f"cd '{sym_dir}' && . {gen}/conanbuild.sh && "
                 f"TMPDIR={_tmpdir} MAKEFLAGS='' make -j1 test", env="conanbuild")

    def package(self):
        sym_dir = os.path.join(self.source_folder, "SYMPHONY")
        self.run(f"cd '{sym_dir}' && . {self.generators_folder}/conanbuild.sh && "
                 f"MAKEFLAGS='' make -j1 install DESTDIR={self.package_folder}",
                 env="conanbuild")
        copy(self, "LICENSE", src=sym_dir,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include/coin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # 静态闭包：本包两库 + 依赖闭包（requires transitive_libs 已带 Cgl/Osi/Clp/
        # CoinUtils/zlib）；-lm 本层兜底（OHOS 与 Linux 同为合法 system lib，R32）。
        self.cpp_info.libs = ["Sym", "OsiSym"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "Symphony")
        self.cpp_info.set_property("cmake_target_name", "Symphony::Symphony")
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
