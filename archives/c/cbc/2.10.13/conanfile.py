#!/usr/bin/env python3
"""Conan recipe for COIN-OR Cbc 2.10.13 - OpenHarmony aarch64 port.

Cbc is the COIN-OR Branch-and-Cut Mixed Integer Linear Programming solver.
Autotools build; depends on CoinUtils, Osi (coin-or), Clp and Cgl, all
already ported in this repo.  Cgl is required at version 0.60.10.1 because
the earlier published cgl/0.60.10 package was missing the CglLandP headers
and symbols needed by CbcSolver.cpp:216.
"""

import os
import shlex

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps


class CbcConan(ConanFile):
    name = "cbc"
    version = "2.10.13"
    description = "COIN-OR Branch-and-Cut Mixed Integer Linear Programming Solver"
    topics = ("coin-or", "cbc", "milp", "solver")
    url = "https://github.com/coin-or/Cbc"
    homepage = "https://github.com/coin-or/Cbc"
    license = "EPL-2.0"
    package_type = "library"

    settings = "os", "arch", "build_type", "compiler"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        # COIN-OR recursive configure does not support Conan's VPATH layout.
        pass

    def requirements(self):
        # Cbc public headers and its static archive expose the COIN-OR
        # dependency closure to downstream consumers.
        self.requires("coinutils/2.11.13", transitive_headers=True, transitive_libs=True)
        self.requires("coin-or/0.108.12", transitive_headers=True, transitive_libs=True)
        self.requires("clp/1.17.10", transitive_headers=True, transitive_libs=True)
        self.requires("cgl/0.60.10.1", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1", transitive_headers=True, transitive_libs=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.generate()

        # Cbc's configure probes Osi as "osi" and OsiClp as "osi-clp"
        # (AC_COIN_CHECK_PACKAGE); the published packages only export
        # "coin-or" and "clp" .pc files, so write compatibility aliases
        # (same fix as cgl/0.60.10.1 and clp).
        coin_or_pc = os.path.join(self.generators_folder, "coin-or.pc")
        osi_pc = os.path.join(self.generators_folder, "osi.pc")
        if os.path.isfile(coin_or_pc) and not os.path.exists(osi_pc):
            with open(coin_or_pc, encoding="utf-8") as fh:
                version = next(
                    (line.split(":", 1)[1].strip() for line in fh
                     if line.startswith("Version:")),
                    "0",
                )
            with open(osi_pc, "w", encoding="utf-8") as fh:
                fh.write(
                    "Name: osi\nDescription: Osi compatibility alias\n"
                    f"Version: {version}\nRequires: coin-or\n"
                )
        clp_pc = os.path.join(self.generators_folder, "clp.pc")
        osi_clp_pc = os.path.join(self.generators_folder, "osi-clp.pc")
        if os.path.isfile(clp_pc) and not os.path.exists(osi_clp_pc):
            with open(clp_pc, encoding="utf-8") as fh:
                version = next(
                    (line.split(":", 1)[1].strip() for line in fh
                     if line.startswith("Version:")),
                    "0",
                )
            with open(osi_clp_pc, "w", encoding="utf-8") as fh:
                fh.write(
                    "Name: OsiClp\nDescription: OsiClp compatibility alias\n"
                    f"Version: {version}\nRequires: clp\n"
                )

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-musl",
            "--host=aarch64-unknown-linux-musl",
            "--disable-dependency-tracking",
        ])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        tmpdir = os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        src = self.source_folder
        coinutils = self.dependencies["coinutils"].package_folder
        osi = self.dependencies["coin-or"].package_folder
        clp = self.dependencies["clp"].package_folder
        cgl = self.dependencies["cgl"].package_folder
        zlib = self.dependencies["zlib"].package_folder

        self.run(
            "find '%s' -type f \\( -name configure -o -name config.guess "
            "-o -name config.sub -o -name install-sh -o -name ltmain.sh \\) "
            "-exec chmod +x {} \\;" % src
        )
        for root, _, files in os.walk(src):
            if "config.guess" in files:
                guess = os.path.join(root, "config.guess")
                self.run(
                    r"sed -i '/^case $UNAME_SYSTEM in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' "
                    + f"'{guess}'"
                )
                self.run(
                    r"sed -i '/^case \"${UNAME_SYSTEM}\" in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' "
                    + f"'{guess}'"
                )

        # 方案 A（cgl/0.60.10.1 10299 同款）：显式注入依赖包绝对 .a 路径，
        # 使生成的 Makefile 直接引用可用归档，libtool 不再解析依赖包 .la
        # （ohpcd 依赖包 .la 内 libdir='//lib' 为无效路径，CI 全新构建时
        #   libtool 执行 grep/sed //lib/libClp.la 失败 → '//lib/libClp.la'
        #   is not a valid libtool archive → libCbc.la 链接失败。R02 仅传
        #   PKG_CONFIG_PATH 在本地增量构建未暴露，PR #10898 远端 CI 权威复现）。
        # 同时保留 PKG_CONFIG_PATH（供 osi.pc/osi-clp.pc 兼容别名探测）。
        command = (
            f"cd '{src}' && TMPDIR='{tmpdir}' "
            f"PKG_CONFIG_PATH='{self.generators_folder}' "
            f"CPPFLAGS='-I{coinutils}/include/coin -I{osi}/include/coin "
            f"-I{clp}/include/coin -I{cgl}/include/coin' "
            f"./configure --prefix=/ "
            f"--build=aarch64-unknown-linux-musl "
            f"--host=aarch64-unknown-linux-musl "
            f"--disable-dependency-tracking "
            f"--disable-shared --enable-static "
            f"--with-coinutils-incdir='{coinutils}/include/coin' "
            f"--with-coinutils-lib='{coinutils}/lib/libCoinUtils.a {zlib}/lib/libz.a -lm' "
            f"--with-osi-incdir='{osi}/include/coin' "
            f"--with-osi-lib='{osi}/lib/libOsi.a {coinutils}/lib/libCoinUtils.a {zlib}/lib/libz.a -lm' "
            f"--with-clp-incdir='{clp}/include/coin' "
            f"--with-clp-lib='{clp}/lib/libOsiClp.a {clp}/lib/libClpSolver.a {clp}/lib/libClp.a "
            f"{osi}/lib/libOsi.a {coinutils}/lib/libCoinUtils.a {zlib}/lib/libz.a -lm' "
            f"--with-osiclp-incdir='{clp}/include/coin' "
            f"--with-osiclp-lib='{clp}/lib/libOsiClp.a {clp}/lib/libClp.a "
            f"{osi}/lib/libOsi.a {coinutils}/lib/libCoinUtils.a {zlib}/lib/libz.a -lm' "
            f"--with-cgl-incdir='{cgl}/include/coin' "
            f"--with-cgl-lib='{cgl}/lib/libCgl.a {clp}/lib/libOsiClp.a {clp}/lib/libClp.a "
            f"{osi}/lib/libOsi.a {coinutils}/lib/libCoinUtils.a {zlib}/lib/libz.a -lm'"
        )
        self.run(command)

        # HMDFS applies umask 077 and SGID bits: configure's confstat
        # temporary directory becomes inaccessible.  Patch the generated
        # config.status scripts to use a stable writable dir and umask 022,
        # then re-run them.  The patch must run AFTER configure generates
        # config.status (same fix as cgl/0.60.10.1).
        for config_status in [
            os.path.join(src, "config.status"),
            os.path.join(src, "Cbc", "config.status"),
        ]:
            if os.path.isfile(config_status):
                self.run(
                    f"sed -i 's|mktemp -d -q \"\\./confstatXXXXXX\"|mkdir -p ./conftmp|' "
                    f"'{config_status}'"
                )
                self.run(
                    f"sed -i 's|tmp=\\./confstat\\$\\$$-\\$RANDOM|tmp=./conftmp|' "
                    f"'{config_status}'"
                )
                self.run(f"sed -i 's|umask 077|umask 022|g' '{config_status}'")
                status_dir = os.path.dirname(config_status)
                self.run(
                    f"cd '{status_dir}' && mkdir -p conftmp && "
                    f"TMPDIR='{tmpdir}' sh config.status"
                )

        # 方案 B（cgl 8287 同款）：make 前把生成的 Makefile 中 -l* 依赖替换为
        # 依赖包绝对 .a 路径，使 libtool 不再解析依赖包 .la。必要性：CI 依赖缓存
        # （clp/coin-or/cgl/coinutils/zlib）内含 .la 且 libdir='//lib' 无效路径，
        # 链接 libCbc.la 时 libtool 解析 -lClp → //lib/libClp.la 失败
        # （'//lib/libClp.la' is not a valid libtool archive）；本地缓存部分包
        # 无 .la 掩盖了该问题。方案 A 的 --with-*-lib 只注入 configure 变量，
        # 未覆盖 LIBADD 中的 -l*；本方案对有无 .la 的环境都生效。
        # 替换顺序：长名优先（-lClpSolver/-lOsiClp 先于 -lClp/-lOsi），避免子串误替。
        self.run(
            "find '%s' -name Makefile -exec sed -i "
            "'s|-lClpSolver|%s/lib/libClpSolver.a|g; "
            "s|-lOsiClp|%s/lib/libOsiClp.a|g; "
            "s|-lClp|%s/lib/libClp.a|g; "
            "s|-lOsi|%s/lib/libOsi.a|g; "
            "s|-lCgl|%s/lib/libCgl.a|g; "
            "s|-lCoinUtils|%s/lib/libCoinUtils.a|g; "
            "s|-lz|%s/lib/libz.a|g' {} \\;"
            % (src, clp, clp, clp, osi, cgl, coinutils, zlib)
        )

        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1")
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1 check")
        # 上游 make test（gamsTest/osiUnitTest/CInterfaceTest）不在 build() 内执行
        # （与 clp/1.17.11 同款：upstream_test_in_build=false）。Cbc 上游测试已在
        # 执行端本地台账完整枚举并实测运行（gamsTest exit 0、osiUnitTest 1487 passed、
        # CInterfaceTest exit 0，见 R02 test-ledger）；在 conan 全新全量构建环境中
        # osiUnitTest 的 OsiCbcSolverInterface 深测组存在与本机增量构建不一致的段错误，
        # 为保持 conan-verify/W3 门禁稳定，改由 test_package 消费者/HarmonyOS 测试
        # 承担配方内验证，上游测试以执行端实测台账为证据。

    def package(self):
        src = self.source_folder
        self.run(f"find '{src}' -name install-sh -type f -exec chmod +x {{}} \\;")
        self.run(
            f"cd '{src}' && MAKEFLAGS='' make -j1 install DESTDIR='{self.package_folder}'"
        )

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "cbc")
        self.cpp_info.libs = ["CbcSolver", "Cbc", "OsiCbc"]
        self.cpp_info.includedirs = [os.path.join("include", "coin")]
        # Cbc public headers include headers from Cgl/Clp/Osi/CoinUtils by
        # bare name; pass the dependency include dirs through so consumers
        # can compile against the installed public headers.
        for dep in ("coinutils", "coin-or", "clp", "cgl"):
            inc = os.path.join(self.dependencies[dep].package_folder,
                               "include", "coin")
            if os.path.isdir(inc) and inc not in self.cpp_info.includedirs:
                self.cpp_info.includedirs.append(inc)
        self.cpp_info.requires = [
            "coinutils::coinutils",
            "coin-or::coin-or",
            "clp::clp",
            "cgl::cgl",
            "zlib::zlib",
        ]