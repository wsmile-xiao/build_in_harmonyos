#!/usr/bin/env python3
"""Conan recipe — bcp 1.4.4（COIN-OR Bcp 分支-切割-价格 MILP 框架，autotools）。

集成形态（W0 实核 2026-09-23，证据 $HOME/tmp/bcp-1.4.4/w0/）：
- 官方发行 tarball（www.coin-or.org/download/source/Bcp/Bcp-1.4.4.tgz，
  双域独立下载 sha256 全等 8b490ad3…906e）自带 5 个捆绑依赖子树
  （CoinUtils/Osi/Vol/Clp/Cgl）；捆绑 Clp/ 内含 x86 专属 immintrin.h 无条件
  include（ClpSimplexDual.cpp:3556、ClpPackedMatrix.cpp:6753），设备 aarch64
  clang15 探针 rc=1（#error x86 only）→ **必须走外部依赖 flags 模式**
  （同已发布 coinor-cbc 2.10.13 先例）：直接驱动 Bcp/configure，
  --with-{clp,vol,cgl}-incdir/-lib 置 coin_has_*=yes 后，捆绑子树不进
  SUBDIRS（顶层 configure 仅 bundled 分支 subdirs="$subdirs Clp"，
  Bcp/Makefile.am 只有 src），Clp/ 全目录不进编译面。
- 依赖闭包与已发布 coinor-cbc 2.10.13 完全同钉版（避免双版本图）：
  coinutils/2.11.13、coin-or/0.108.12（=Osi）、clp/1.17.10、cgl/0.60.10.1、
  zlib/1.3.1，外加 Bcp 特有的 vol/1.5.4。W0-2 真实 conan install rc=0。
- Bcp/configure（旧式 AC_COIN_CHECK_PACKAGE）只查 Clp（必填，Cpx 备选）/Vol/Cgl，
  不提供 coinutils/osi 的 flags 分支 → 五包头文件合并到单一 staging 供三个
  incdir 共用；链接闭包串按「依赖方在前」用**直接 .a 路径**展开（已发布依赖包
  的 .la 固化 prefix=/，-L/-l 会被 libtool 解析成 //lib/*.la 死路，同 cbc 探索轮实测）。
- HMDFS 修复（shebang/config.guess/config.status umask+mktemp/libtool .lo）在
  build() 内完成，不改上游源码（patches: {}）。
- CFLAGS/CXXFLAGS 显式钉 `-O3 -pipe -DNDEBUG`：CI worker 进程环境泄漏
  `-fPIC -O2`（无 -DNDEBUG），不钉则 CI 偏离设备/W3 已验证配置并在 NDEBUG
  分支上行为分叉（coinor-cbc/ositests Segv 同族教训，R33 纪律）。
- 上游测试：Bcp/Makefile.am `TESTS = BAC` → `make test` 驱动
  test/BAC/unitTest -param bb.par（Benders 分解 bac.lp/bac.mps 场景）；
  test/BAC 不在默认 SUBDIRS（ALWAYS_FALSE），按「显式编译 → 签名 → make test」
  三步驱动；OHOS 运行前 ELF 必须 binary-sign-tool 自签，否则加载器 EPERM。
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
)


class BcpConan(ConanFile):
    name = "bcp"
    version = "1.4.4"
    description = "COIN-OR Branch, Cut, and Price Framework (Bcp)"
    license = "CPL-1.0"  # 上游 Bcp/LICENSE = Common Public License Version 1.0
    homepage = "https://projects.coin-or.org/Bcp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 库形态（libBcp.a + include/coin + bcp.pc）；上游 test/BAC 的 unitTest 是
    # noinst_PROGRAM 不安装；无 bin/ 交付。
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 与已发布 coinor-cbc 2.10.13 闭包完全同钉版；vol 是 Bcp 特有硬依赖
        # （Bcp/configure.ac:72 AC_COIN_CHECK_PACKAGE(Vol, [osi-vol], [BcpLib])）。
        # transitive_headers/transitive_libs：Bcp 公共头（BCP_cut.hpp 等）裸引用
        # Osi/CoinUtils/Cgl 头；静态交付要求消费者拿到完整静态闭包。
        self.requires("coinutils/2.11.13", transitive_headers=True, transitive_libs=True)
        self.requires("coin-or/0.108.12", transitive_headers=True, transitive_libs=True)
        self.requires("clp/1.17.10", transitive_headers=True, transitive_libs=True)
        self.requires("cgl/0.60.10.1", transitive_headers=True, transitive_libs=True)
        self.requires("vol/1.5.4", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1", transitive_libs=True)

    def layout(self):
        # HMDFS 上 autotools 不支持 out-of-source（config.status 临时文件），
        # 与同族 coinutils/clp/cbc 一律 in-source（build_folder == source_folder）。
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── OHOS ELF 自签（同 coinor-cbc 配方口径）──────────────────────────
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
        os.chmod(output, (os.stat(output).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def _fix_hmdfs_scripts(self, src):
        """E165/E160：shebang 与 config.guess 的 HarmonyOS 修复（同族 coinutils/cbc 口径）。"""
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        ohos_shell = os.environ.get("OHOS_SHELL", "/system/bin/sh")
        for d in (src, os.path.join(src, "Bcp")):
            for script in ("configure", "install-sh", "config.sub",
                           "config.guess", "ltmain.sh", "missing", "depcomp"):
                sp = os.path.join(d, script)
                if not os.path.exists(sp):
                    continue
                self.run(f"sed -i '1s|#!/bin/bash|#!{config_shell}|' '{sp}'")
                self.run(f"sed -i '1s|#!/bin/sh|#!{ohos_shell}|' '{sp}'")
                self.run(f"sed -i '1s|#! /bin/sh|#!{ohos_shell}|' '{sp}'")
            guess = os.path.join(d, "config.guess")
            if os.path.exists(guess):
                self.run(r"""sed -i '/^case $UNAME_SYSTEM in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """ + f"'{guess}'")
                self.run(r"""sed -i '/^case "${UNAME_SYSTEM}" in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """ + f"'{guess}'")

    def _fix_config_status(self, bcp_dir, tmpdir):
        """HMDFS：config.status 的 umask 077 + mktemp ./confstatXXXXXX 会在目录模式
        落盘 2700 后不可写（设备边界 §一.10）→ 改 umask 022 + 固定 ./conftmp 并重跑
        （autoconf 2.59 生成的 config.status 与同族 coinutils/cbc 完全同构）。"""
        sp = os.path.join(bcp_dir, "config.status")
        if not os.path.exists(sp):
            return
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"sed -i 's|mktemp -d -q \"\\./confstatXXXXXX\"|mkdir -p ./conftmp|' '{sp}'")
        self.run(f"sed -i 's|tmp=\\./confstat\\$\\$-\\$\\$RANDOM|tmp=./conftmp|' '{sp}'")
        self.run(f"sed -i 's|umask 077|umask 022|g' '{sp}'")
        self.run(f"cd '{bcp_dir}' && rm -rf conftmp confstat* && "
                 f"TMPDIR={tmpdir} CONFIG_SHELL={config_shell} {config_shell} config.status")

    def _fix_lo_files(self, bcp_dir):
        """HMDFS 会截断 libtool .lo 写入（同族 coinutils/cbc 口径）。加 [ -e ] 守卫
        避免无匹配时在字面 '*.lo' 上误建文件。"""
        for sub in ("src", os.path.join("test", "BAC")):
            sd = os.path.join(bcp_dir, sub)
            if not os.path.isdir(sd):
                continue
            self.run(
                f"cd '{sd}' && for f in *.lo; do [ -e \"$f\" ] || continue; "
                f"grep -q pic_object \"$f\" || {{ "
                f"n=${{f%.lo}}; "
                f"printf '# %s - libtool object\\npic_object=.libs/%s.o\\nnon_pic_object=%s.o\\n' \"$f\" \"$n\" \"$n\" > \"$f\"; "
                f"}}; done"
            )

    def generate(self):
        # 合并 include staging：五个 coin 包头文件分居各自 include/coin，而
        # Bcp/configure 的 --with-*-incdir 只接受单目录 → 合并成一份。
        # HMDFS 硬链接不可用（§一.21，cp -al 会整树复制），逐文件 conan copy。
        self._coin_include = os.path.join(self.generators_folder, "coin-include")
        for name in ("coinutils", "coin-or", "clp", "cgl", "vol"):
            inc = os.path.join(self.dependencies[name].package_folder, "include", "coin")
            if os.path.isdir(inc):
                copy(self, "*", src=inc, dst=self._coin_include)
        self._deps = {
            name: self.dependencies[name].package_folder
            for name in ("coinutils", "coin-or", "clp", "cgl", "vol", "zlib")
        }

    def build(self):
        apply_conandata_patches(self)  # 4 个 config.guess/config.sub portability 补丁
        src = self.source_folder
        bcp_dir = os.path.join(src, "Bcp")
        gen = self.generators_folder
        # HMDFS：TMPDIR 必须指向可写目录（HiShell 注入值不可信，设备边界 §一.12）
        tmpdir = os.environ.get("TMPDIR") or os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir

        self._fix_hmdfs_scripts(src)

        d = self._deps
        inc = self._coin_include
        # 闭包用直接 .a 路径而非 -L/-l：已发布依赖包的 .la 固化 libdir='//'
        # （prefix=/），libtool 看到 -l<name> 会读 <pkg>/lib/lib<name>.la 并按其
        # libdir 解析出 '//lib/libX.la' 直接报 "not a valid libtool archive"
        # （coinor-cbc 探索轮实测）。直连 .a 与上游 .pc 的写法一致。
        # 各串按「依赖方在前、被依赖方在后」展开（静态链接单遍解析方向）：
        _base = (f"{d['coin-or']}/lib/libOsi.a {d['coinutils']}/lib/libCoinUtils.a "
                 f"{d['zlib']}/lib/libz.a -lm")
        #   Clp 组（BcpLib）：OsiClp → ClpSolver → Clp → Osi/CoinUtils/z
        clp_lib = (f"{d['clp']}/lib/libOsiClp.a {d['clp']}/lib/libClpSolver.a "
                   f"{d['clp']}/lib/libClp.a {_base}")
        #   Vol 组（BcpLib）：OsiVol → Vol → Osi/CoinUtils/z
        vol_lib = (f"{d['vol']}/lib/libOsiVol.a {d['vol']}/lib/libVol.a {_base}")
        #   Cgl 组（Bac）：Cgl → Osi/CoinUtils/z（同 cbc closure 口径）
        cgl_lib = f"{d['cgl']}/lib/libCgl.a {_base}"

        cc = os.environ.get("CC", "clang")
        cxx = os.environ.get("CXX", "clang++")
        # R33 同款纪律：编译 flags 显式钉死，不继承未定义 shell 变量。CI worker
        # 进程环境泄漏 CFLAGS/CXXFLAGS='-fPIC -O2'（无 -DNDEBUG），配方不钉则 CI
        # 偏离设备/W3 已验证配置（-O3 -pipe -DNDEBUG）并触发 NDEBUG 分支分叉
        # （coinor-cbc ositests Segv 教训）。钉死值 = 设备基座配置，三方同源。
        cflags = "-O3 -pipe -DNDEBUG"
        cxxflags = "-O3 -pipe -DNDEBUG"
        # 直接驱动 Bcp 子包 configure：顶层 configure 仅做子包编排（coinutils/osi/
        # vol/clp/cgl/bcp），跑它会多绕一层 HMDFS 脆弱的老 autoconf config.status；
        # Bcp/configure 自带 AC_CONFIG_FILES 生成本目录全部 Makefile（含 test/BAC）。
        # 不给 --with-mpi → AC_COIN_CHECK_USER_LIBRARY 探不到 mpi.h 置
        # coin_has_mpi=no（MPI 的 AM_CPPFLAGS 有 conditional 包裹，安全）。
        self.run(
            f"cd '{bcp_dir}' && . {gen}/conanbuild.sh && "
            f"CC={cc} CXX={cxx} TMPDIR={tmpdir} "
            f"CFLAGS='{cflags}' CXXFLAGS='{cxxflags}' "
            f"./configure --prefix=/ "
            f"--build=aarch64-unknown-linux-musl "
            f"--enable-static --disable-shared --disable-dependency-tracking "
            f"--with-clp-incdir='{inc}' --with-clp-lib='{clp_lib}' "
            f"--with-vol-incdir='{inc}' --with-vol-lib='{vol_lib}' "
            f"--with-cgl-incdir='{inc}' --with-cgl-lib='{cgl_lib}'",
            env="conanbuild",
        )
        self._fix_config_status(bcp_dir, tmpdir)
        # R33：编译器/标志经显式环境传入；-j1 规避 HMDFS 对 libtool .lo 的并发
        # 截断（设备边界 §一.7/§一.13）；MAKEFLAGS='' 防 jobserver 继承。
        self.run(f"cd '{bcp_dir}' && . {gen}/conanbuild.sh && "
                 f"CC={cc} CXX={cxx} MAKEFLAGS='' make -j1", env="conanbuild")
        self._fix_lo_files(bcp_dir)

        # ── 上游测试（Bcp/Makefile.am `TESTS = BAC`）────────────────────
        # test/BAC 不在默认 SUBDIRS（if ALWAYS_FALSE），`make all` 不编译
        # unitTest → 按「显式编译 → ELF 签名 → make test」三步：确保 make test
        # 执行 ./unitTest 时拿到的已是签名成品（签名后不重编）。
        if not can_run(self):
            self.output.warning("Cannot run the upstream Bcp test suite on this host")
            return
        self.run(f"cd '{bcp_dir}' && . {gen}/conanbuild.sh && "
                 f"CC={cc} CXX={cxx} MAKEFLAGS='' make -j1 -C test/BAC unitTest",
                 env="conanbuild")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(os.path.join(bcp_dir, "test", "BAC", "unitTest"))
        # make test → cd test/$t && make test → ./unitTest -param bb.par
        #（unitTest 已建成且已签名，make 判 up-to-date 不重编直接执行）
        self.run(f"cd '{bcp_dir}' && . {gen}/conanbuild.sh && "
                 f"CC={cc} CXX={cxx} MAKEFLAGS='' make -j1 test", env="conanbuild")

    def package(self):
        bcp_dir = os.path.join(self.source_folder, "Bcp")
        # install 前再修一次 .lo（libtool --mode=install 读取）
        self._fix_lo_files(bcp_dir)
        self.run(f"cd '{bcp_dir}' && . {self.generators_folder}/conanbuild.sh && "
                 f"MAKEFLAGS='' make -j1 install DESTDIR={self.package_folder}",
                 env="conanbuild")
        copy(self, "LICENSE", src=os.path.join(self.source_folder, "Bcp"),
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include/coin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = []
        # 静态闭包：本包 1 库 + 依赖闭包（requires transitive_libs 已带
        # Cgl/Osi/Clp/OsiClp/CoinUtils/Vol/OsiVol/zlib）；-m 由本层兜底（R32）。
        self.cpp_info.libs = ["Bcp"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "Bcp")
        self.cpp_info.set_property("cmake_target_name", "Bcp::Bcp")
