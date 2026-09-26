#!/usr/bin/env python3
"""Conan recipe — coinor-cbc 2.10.13（COIN-OR 分支切割 MILP 求解器，autotools）。

集成形态（W0 实核 2026-09-21）：
- 上游 release tag tarball **不捆绑**依赖（.coin-or/Dependencies 声明 CoinUtils/Osi/Clp/Cgl）。
- 四个硬依赖全部已发布 ohpcd（二进制 + 原版 autotools 布局 include/coin + 原生 .pc）：
  coinutils/2.11.13、coin-or/0.108.12（即 Osi）、clp/1.17.10、cgl/0.60.10.1，闭包钉版一致。
- 子包 Cbc/configure 为新式 AC_COIN_CHECK_PACKAGE（pkg-config 模块名 cgl/osi/coinutils/clp/
  osi-clp/osi-unittests）。但已发布包 prefix=/ 固化在 .pc 里，pkg-config 路径不可用 →
  改用 **flags 模式**：--with-<pkg>-incdir / --with-<pkg>-lib 显式注入（configure 中
  flags 分支直接置 coin_has_*=yes 并跳过 pkg-config）。
- 头文件合并 staging：configure 的 incdir 只接受单目录，而依赖头分居各包 include/coin，
  在 generate() 把四包头文件合并到 generators 目录单一 staging 供三个 incdir 共用。
- 直接驱动子包 <src>/Cbc/configure（顶层 configure 仅做子包编排，跳过可少一层
  HMDFS 脆弱的 autoconf 2.59 config.status）。
- 测试数据：Data-Sample 1.2.13 + Data-miplib3 1.2.9（官方 coin-or-tools 仓库）经
  --with-sample-datadir / --with-miplib3-datadir 注入，激活上游 make test 的
  test_cbc(-unitTest)/test_cbc_generic/ositests(-mpsDir)。
- Netlib（ositests 的 -testOsiSolverInterface 扩展面，约 40MB）不引入：数据体积与
  运行时长代价大，其余全部测试驱动程序可运行，netlib 扩展未运行在 PR/报告中如实申报。
- OHOS：构建产物（cbc/cbc-generic/gamsTest/osiUnitTest/CInterfaceTest）运行前必须
  binary-sign-tool 自签，否则加载器 EPERM。
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class CoinorCbcConan(ConanFile):
    name = "coinor-cbc"
    version = "2.10.13"
    description = "COIN-OR Branch-and-Cut mixed integer programming solver (cbc)"
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/Cbc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 库 + CLI 求解器（bin/cbc、bin/cbc-generic）；库形态与同族 clp/cgl 一致交付静态库
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 与已发布闭包完全同钉版（cgl/0.60.10.1 → clp/1.17.10 → coin-or/0.108.12 →
        # coinutils/2.11.13），任何一侧改版都会造成双版本图。
        # transitive_headers/transitive_libs：Cbc 公共头（CbcModel.hpp 等）裸引用
        # Osi/CoinUtils/Clp 头；静态交付要求消费者拿到完整静态闭包（同 cgl 配方口径）。
        self.requires("coinutils/2.11.13", transitive_headers=True, transitive_libs=True)
        self.requires("coin-or/0.108.12", transitive_headers=True, transitive_libs=True)
        self.requires("clp/1.17.10", transitive_headers=True, transitive_libs=True)
        self.requires("cgl/0.60.10.1", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1", transitive_libs=True)

    def layout(self):
        # HMDFS 上 autotools 不支持 out-of-source（config.status 临时文件），
        # 与同族 coinutils/clp 一律 in-source（self.build_folder == self.source_folder）。
        pass

    def source(self):
        data = self.conan_data["sources"]
        get(self, data["url"], sha256=data["sha256"], strip_root=True)
        # 官方测试数据包（make test 的 -dirSample/-dirMiplib3 数据面）
        for key, dest in (("data_sample", "data-stage/Sample"),
                          ("data_miplib3", "data-stage/miplib3")):
            get(self, data[key]["url"], sha256=data[key]["sha256"],
                strip_root=True, destination=os.path.join(self.source_folder, dest))

    def generate(self):
        # 合并 include staging：四个依赖包统一安装到各自 include/coin，configure 的
        # --with-*-incdir 只接受单目录 → 合并成一份。HMDFS 硬链接不可用（设备边界
        # §一.21，cp -al 会整树复制），用 conan copy 逐文件拷贝。
        self._coin_include = os.path.join(self.generators_folder, "coin-include")
        for name in ("coinutils", "coin-or", "clp", "cgl"):
            inc = os.path.join(self.dependencies[name].package_folder, "include", "coin")
            if os.path.isdir(inc):
                copy(self, "*", src=inc, dst=self._coin_include)
        self._deps = {
            name: self.dependencies[name].package_folder
            for name in ("coinutils", "coin-or", "clp", "cgl", "zlib")
        }

    # ── OHOS ELF 自签（同 libsndfile 配方口径）──────────────────────────
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
        """E165/E160：shebang 与 config.guess 的 HarmonyOS 修复（同族 coinutils 口径）。"""
        _config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        _ohos_shell = os.environ.get("OHOS_SHELL", "/system/bin/sh")
        for d in (src, os.path.join(src, "Cbc")):
            for script in ("configure", "install-sh", "config.sub",
                           "config.guess", "ltmain.sh", "missing", "depcomp"):
                sp = os.path.join(d, script)
                if not os.path.exists(sp):
                    continue
                self.run(f"sed -i '1s|#!/bin/bash|#!{_config_shell}|' '{sp}'")
                self.run(f"sed -i '1s|#!/bin/sh|#!{_ohos_shell}|' '{sp}'")
                self.run(f"sed -i '1s|#! /bin/sh|#!{_ohos_shell}|' '{sp}'")
        # config.guess 的 HarmonyOS 分支（--build 显式给出时通常不会触发，防御性保留）
        for d in (src, os.path.join(src, "Cbc")):
            guess = os.path.join(d, "config.guess")
            if os.path.exists(guess):
                self.run(r"""sed -i '/^case $UNAME_SYSTEM in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """ + f"'{guess}'")
                self.run(r"""sed -i '/^case "${UNAME_SYSTEM}" in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """ + f"'{guess}'")

    def _fix_config_status(self, cbc_dir, tmpdir):
        """HMDFS：config.status 的 umask 077 + mktemp ./confstatXXXXXX 会在目录模式
        落盘 2700 后不可写（设备边界 §一.10）→ 改 umask 022 + 固定 ./conftmp 并重跑。
        autoconf 2.59 生成的 config.status 与同族 coinutils 完全同构。"""
        csp = os.path.join(cbc_dir, "config.status")
        if not os.path.exists(csp):
            return
        _config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"sed -i 's|mktemp -d -q \"\\./confstatXXXXXX\"|mkdir -p ./conftmp|' '{csp}'")
        self.run(f"sed -i 's|tmp=\\./confstat\\$\\$$-\\$RANDOM|tmp=./conftmp|' '{csp}'")
        self.run(f"sed -i 's|umask 077|umask 022|g' '{csp}'")
        self.run(f"sed -i 's|\\`mkdir -p \\./conftmp\\`|./conftmp|' '{csp}'")
        self.run(f"cd '{cbc_dir}' && rm -rf conftmp confstat* && "
                 f"TMPDIR={tmpdir} CONFIG_SHELL={_config_shell} {_config_shell} config.status")

    def _fix_lo_files(self, cbc_dir):
        """HMDFS 会截断 libtool .lo 写入（同族 coinutils 口径）。加 [ -e ] 守卫避免
        无匹配时在字面 '*.lo' 上误建文件。"""
        for sub in ("src", os.path.join("src", "OsiCbc"), "test"):
            sd = os.path.join(cbc_dir, sub)
            if not os.path.isdir(sd):
                continue
            self.run(
                f"cd '{sd}' && for f in *.lo; do [ -e \"$f\" ] || continue; "
                f"grep -q pic_object \"$f\" || {{ "
                f"n=${{f%.lo}}; "
                f"printf '# %s - libtool object\\npic_object=.libs/%s.o\\nnon_pic_object=%s.o\\n' \"$f\" \"$n\" \"$n\" > \"$f\"; "
                f"}}; done"
            )

    def build(self):
        apply_conandata_patches(self)  # patches: {} — 幂等空操作，保留防御
        src = self.source_folder
        cbc_dir = os.path.join(src, "Cbc")
        gen = self.generators_folder
        # HMDFS：TMPDIR 必须指向可写目录（设备 HiShell 注入值不可信，设备边界 §一.12）
        _tmpdir = os.environ.get("TMPDIR") or os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
        os.makedirs(_tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = _tmpdir
        os.environ["TMP"] = _tmpdir

        self._fix_hmdfs_scripts(src)

        d = self._deps
        inc = self._coin_include
        data_sample = os.path.join(src, "data-stage", "Sample")
        data_miplib3 = os.path.join(src, "data-stage", "miplib3")
        # 闭包用**直接 .a 路径**而非 -L/-l：依赖包的 .la 文件固化 libdir='//'
        # （prefix=/），libtool 看到 -l<name> 会去读 <pkg>/lib/lib<name>.la 并按其
        # libdir 解析出 '//lib/libX.la' 直接报 "not a valid libtool archive"
        # （探索轮实测）。直连 .a 与上游 cgl.pc 的写法一致，libtool 不再解析 .la。
        closure = (f"{d['cgl']}/lib/libCgl.a {d['coin-or']}/lib/libOsi.a "
                   f"{d['coinutils']}/lib/libCoinUtils.a {d['zlib']}/lib/libz.a -lm")
        clp_lib = (f"{d['clp']}/lib/libOsiClp.a {d['clp']}/lib/libClpSolver.a "
                   f"{d['clp']}/lib/libClp.a {closure}")
        ositests_lib = f"{d['coin-or']}/lib/libOsiCommonTests.a {closure}"
        _cc = os.environ.get("CC", "clang")
        _cxx = os.environ.get("CXX", "clang++")
        # R33 同款纪律，编译 flags 一并显式钉死、不继承未定义 shell 变量：
        # CI worker 进程环境泄漏 CFLAGS/CXXFLAGS='-fPIC -O2'（**无 -DNDEBUG**，恰为
        # 仓库 knowledge/FAQ.md 记载的环境值），而 profile 与 ci/ 脚本均不设置——
        # 配方不钉 flags 时 CI 的 configure 会取到该泄漏值，使 CI 构建偏离设备/W3
        # 已验证配置（-O3 -pipe -DNDEBUG），并在 ositests 触发段错误：上游
        # OsiCbcSolverInterfaceTest.cpp:122 `if (!OsiCbcHasNDEBUG())`（库里
        # `#ifdef NDEBUG` 编译期常量）分支只在无 -DNDEBUG 时执行，设备跳过、CI 执行
        # 后 `make[1]: *** [Makefile:824: ositests] Segmentation fault (core dumped)`
        # → `make: *** [Makefile:988: test] Error 2`（2026-09-23 CI build#56630 实测；
        # 本地以 CI 同款 flags 逐字复现同款崩溃，日志留任务目录）。钉死值 = 本包设备
        # 验证配置的基座（configure 会自行追加 -DCBC_BUILD），CI/W3/设备三方同源。
        _cflags = "-O3 -pipe -DNDEBUG"
        _cxxflags = "-O3 -pipe -DNDEBUG"
        self.run(
            f"cd '{cbc_dir}' && . {gen}/conanbuild.sh && "
            f"CC={_cc} CXX={_cxx} TMPDIR={_tmpdir} "
            f"CFLAGS='{_cflags}' CXXFLAGS='{_cxxflags}' "
            f"./configure --prefix=/ "
            f"--build=aarch64-unknown-linux-musl "
            f"--enable-static --disable-shared --disable-dependency-tracking "
            f"--with-coindepend-incdir='{inc}' "
            f"--with-coindepend-lib='{closure}' "
            f"--with-clp-incdir='{inc}' "
            f"--with-clp-lib='{clp_lib}' "
            f"--with-ositests-incdir='{inc}' "
            f"--with-ositests-lib='{ositests_lib}' "
            f"--with-sample-datadir='{data_sample}' "
            f"--with-miplib3-datadir='{data_miplib3}' "
            f"--with-cbc-generic "
            f"--without-dylp --without-vol --without-cpx --without-glpk --without-grb "
            f"--without-highs --without-msk --without-spx --without-xpr "
            f"--without-asl --without-mumps --without-nauty --without-netlib",
            env="conanbuild",
        )
        self._fix_config_status(cbc_dir, _tmpdir)
        # R33：编译器/标志经显式环境传入，不依赖未定义 shell 变量；-j1 规避 HMDFS
        # 对 libtool .lo 的并发截断（设备边界 §一.7/§一.13）。
        self.run(f"cd '{cbc_dir}' && . {gen}/conanbuild.sh && "
                 f"CC={_cc} CXX={_cxx} MAKEFLAGS='' make -j1", env="conanbuild")
        self._fix_lo_files(cbc_dir)

        # ── 上游测试（test/Makefile.am 注册的 5 个目标）─────────────────
        # N=5：gamstests / ositests / ctests / test_cbc(-unitTest) / test_cbc_generic
        if not can_run(self):
            self.output.warning("Cannot run the upstream Cbc test suite on this host")
            return
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(os.path.join(cbc_dir, "src", "cbc"))
            self._sign_ohos_elf(os.path.join(cbc_dir, "src", "cbc-generic"))
            for t in ("gamsTest", "osiUnitTest", "CInterfaceTest"):
                self._sign_ohos_elf(os.path.join(cbc_dir, "test", t))
        self.run(f"cd '{cbc_dir}' && . {gen}/conanbuild.sh && "
                 f"MAKEFLAGS='' make -j1 test", env="conanbuild")

    def package(self):
        cbc_dir = os.path.join(self.source_folder, "Cbc")
        # install 前再修一次 .lo（libtool --mode=install 读取）；静态模式无 relink
        self._fix_lo_files(cbc_dir)
        self.run(f"cd '{cbc_dir}' && . {self.generators_folder}/conanbuild.sh && "
                 f"MAKEFLAGS='' make -j1 install DESTDIR={self.package_folder}",
                 env="conanbuild")
        copy(self, "LICENSE", src=cbc_dir,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include/coin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # 静态闭包：本包三库 + 依赖闭包（requires transitive_libs 已带 Cgl/Osi/Clp/
        # OsiClp/CoinUtils/zlib）；-lm 由本层兜底（OHOS 与 Linux 同为合法 system lib，R32）。
        self.cpp_info.libs = ["CbcSolver", "Cbc", "OsiCbc"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "Cbc")
        self.cpp_info.set_property("cmake_target_name", "Cbc::Cbc")
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
