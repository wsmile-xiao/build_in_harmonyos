#!/usr/bin/env python3
"""Conan recipe — Vol 1.5.4 (COIN-OR LP Volume Algorithm, autotools).

Vol is a C library implementing the Volume Algorithm for linear programming.
Build system: autotools. Dependencies: CoinUtils + Osi (both published).

Rules compliance:
  R27: 依赖 coinutils/2.11.13 + coin-or/0.108.12（均已发布）
  R32: settings.os validated with in ("Linux", "OHOS")
"""
import os
import shutil as _shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class VolConan(ConanFile):
    name = "vol"
    version = "1.5.4"
    description = "COIN-OR Vol: Volume Algorithm for linear programming"
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/Vol"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)
        # 上游 osiUnitTest 需 COIN Sample 数据 exmip1.mps（8 列标准 MIP）——
        # CI worker 无法访问 github.com，样本随配方传递（test_package/exmip1.mps）
        copy(self, "test_package/exmip1.mps", self.recipe_folder,
             self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if not self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("coinutils/2.11.13")
        self.requires("coin-or/0.108.12")

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"vol only supports Linux/OHOS, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        # osi.pc 别名（coin-or 包名不匹配 configure 探测）
        coin_or_pc = os.path.join(self.generators_folder, "coin-or.pc")
        osi_pc = os.path.join(self.generators_folder, "osi.pc")
        if os.path.isfile(coin_or_pc) and not os.path.exists(osi_pc):
            with open(coin_or_pc, encoding="utf-8") as f:
                ver = next((l.split(":",1)[1].strip() for l in f if l.startswith("Version:")), "0")
            with open(osi_pc, "w") as f:
                f.write(f"Name: osi\nDescription: Osi compatibility alias\nVersion: {ver}\nRequires: coin-or\n")
        tc = AutotoolsToolchain(self)
        # VolVolume.hpp uses C++17-deprecated 'register' storage class specifier
        # (clang 15 with -std=c++17 errors on -Wregister by default)
        tc.extra_cxxflags.append("-Wno-register")
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-dependency-tracking")
        if not self.options.shared:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        else:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        tmpdir = os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        src = self.source_folder
        # GitCode 镜像（conandata 第一项）archive 顶层为
        # build_in_harmonyos-vol-src-raw/，strip_root 后源码落在 src/ 子目录
        # （同 clp-src-raw 先例）；官方 GitHub tarball 则直接落在根目录。
        # 统一探测 configure 位置，两种来源均可构建。
        if os.path.exists(os.path.join(src, "src", "configure")):
            src = os.path.join(src, "src")
        coinutils = self.dependencies["coinutils"].package_folder
        osi = self.dependencies["coin-or"].package_folder
        # config.guess/config.sub 动态修补（同 COIN-OR 系列）
        for root, _, files in os.walk(src):
            if "config.guess" in files:
                guess = os.path.join(root, "config.guess")
                self.run(r"sed -i '/^case $UNAME_SYSTEM in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' " + f"'{guess}'")
                self.run(r"""sed -i '/^case "${UNAME_SYSTEM}" in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """ + f"'{guess}'")
            if "config.sub" in files:
                sub = os.path.join(root, "config.sub")
                self.run(r"""sed -i '/nto-qnx\* | linux-gnu\*/s/linux-gnu\*/linux-gnu* | linux-musl*/' """ + f"'{sub}'")
                self.run(r"""sed -i '/-mingw32\* | -linux-gnu\*/s/-linux-gnu\*/-linux-gnu* | -linux-musl*/' """ + f"'{sub}'")
        # chmod +x (E165: Conan copy drops bits)
        self.run(f"find '{src}' -name configure -o -name config.guess -o -name config.sub -o -name install-sh -o -name ltmain.sh | xargs chmod +x 2>/dev/null; true")
        # C++17 兼容：std::bind2nd 在 C++17 被移除（CI profile cppstd=17），
        # OsiVolSolverInterface.cpp 的 std::transform 标量乘法用它——替换为
        # lambda，捕获 this（objsense_ 为成员变量，不能直接按值捕获）
        _osi_src = os.path.join(
            src, "Vol", "src", "OsiVol", "OsiVolSolverInterface.cpp")
        if os.path.isfile(_osi_src):
            _c = open(_osi_src, encoding="utf-8").read()
            _old = "std::bind2nd(std::multiplies<double>(), objsense_)"
            _new = "[this](double x) { return x * objsense_; }"
            if _old in _c:
                open(_osi_src, "w", encoding="utf-8").write(
                    _c.replace(_old, _new))
                self.output.info(
                    "patched OsiVolSolverInterface.cpp: bind2nd -> lambda")
        # manual configure（COIN-OR recursive 模式）
        self.run(
            f"cd '{src}' && TMPDIR={tmpdir} "
            f"PKG_CONFIG_PATH={self.generators_folder} "
            f"CPPFLAGS='-I{coinutils}/include/coin -I{osi}/include/coin' "
            f"./configure --prefix=/ "
            f"--build=aarch64-unknown-linux-musl "
            f"--disable-dependency-tracking "
            f"--disable-shared --enable-static "
            f"--with-coinutils-incdir='{coinutils}/include/coin' "
            f"--with-coinutils-lib='{coinutils}/lib/libCoinUtils.a -lm' "
            f"--with-osi-incdir='{osi}/include/coin' "
            f"--with-osi-lib='{osi}/lib/libOsi.a {coinutils}/lib/libCoinUtils.a -lm'"
        )
        # config.status umask 修复（HMDFS）
        for cs in ["config.status", "Vol/config.status"]:
            csp = os.path.join(src, cs)
            if os.path.isfile(csp):
                self.run(f"sed -i 's|mktemp -d -q \"\\./confstatXXXXXX\"|mkdir -p ./conftmp|' '{csp}'")
                self.run(f"sed -i 's|umask 077|umask 022|g' '{csp}'")
                self.run(f"cd '{os.path.dirname(csp)}' && mkdir -p conftmp && TMPDIR={tmpdir} sh config.status")
        # Makefile -l → absolute .a（libtool .la libdir='//lib' 修复）
        for _root, _dirs, _files in os.walk(src):
            if "Makefile" not in _files:
                continue
            _mf = os.path.join(_root, "Makefile")
            _c = open(_mf, encoding="utf-8").read()
            _orig = _c
            for _lib, _abs in [
                ("-lOsi", f"{osi}/lib/libOsi.a"),
                ("-lCoinUtils", f"{coinutils}/lib/libCoinUtils.a"),
            ]:
                _c = _c.replace(_lib, _abs)
            if _c != _orig:
                open(_mf, "w", encoding="utf-8").write(_c)
                os.utime(_mf, None)
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1")
        # 上游单元测试实跑（审查 rule4）：test/osiUnitTest 3 组测试
        # （OsiRowCut/OsiColCut/OsiVol 通用单元测试）。configure 的
        # COIN_HAS_OSITESTS 探测依赖 osi-unittests.pc（ohpcd 无独立包），
        # automake 不会构建该程序——手工编译运行；测试组件
        # OsiUnitTests.hpp/libOsiCommonTests.a 随 coin-or 包提供。
        # 静态链接（--disable-shared），运行无需 LD_LIBRARY_PATH。
        _compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cxx = _compilers.get("cpp", "clang++")
        # CoinUtils 的 gzip I/O 需 zlib（transitive 依赖，链接需显式 -lz）
        try:
            _zlib_link = f"{self.dependencies['zlib'].package_folder}/lib/libz.a"
        except Exception:
            _zlib_link = "-lz"
        if can_run(self):
            _test_src_dir = os.path.join(src, "Vol", "test")
            _test_bin = os.path.join(_test_src_dir, "osiUnitTest")
            _vol_lib = os.path.join(src, "Vol", "src")
            # osiUnitTest 用相对路径 ../../Data/Sample/exmip1.mps 找样本——
            # 从配方随带的样本复制到源码树 Data/Sample/（CI 无 github 访问）
            _sample = os.path.join(
                self.export_sources_folder, "test_package", "exmip1.mps")
            if os.path.isfile(_sample):
                _sample_dir = os.path.join(src, "Data", "Sample")
                os.makedirs(_sample_dir, exist_ok=True)
                _shutil.copy2(_sample, os.path.join(_sample_dir, "exmip1.mps"))
            if (os.path.isfile(os.path.join(_test_src_dir, "osiUnitTest.cpp"))
                    and os.path.isfile(os.path.join(
                        _vol_lib, "OsiVol", ".libs", "libOsiVol.a"))):
                self.run(
                    f"cd '{_test_src_dir}' && "
                    f"{cxx} -std=c++17 -stdlib=libc++ -Wno-register "
                    f"-I{os.path.join(_vol_lib, '..', 'src')} "
                    f"-I{os.path.join(_vol_lib, 'OsiVol')} "
                    f"-I{osi}/include/coin -I{coinutils}/include/coin "
                    f"osiUnitTest.cpp OsiVolSolverInterfaceTest.cpp "
                    f"-o {_test_bin} "
                    f"{os.path.join(_vol_lib, 'OsiVol', '.libs', 'libOsiVol.a')} "
                    f"{os.path.join(_vol_lib, '.libs', 'libVol.a')} "
                    f"{osi}/lib/libOsiCommonTests.a {osi}/lib/libOsi.a "
                    f"{coinutils}/lib/libCoinUtils.a {_zlib_link} -lm"
                )
                self.run(
                    f"cd '{_test_src_dir}' && ./osiUnitTest",
                    env="conanbuild",
                )

    def package(self):
        src = self.source_folder
        # 与 build() 一致的 src/ 子目录探测：GitCode 镜像（conandata 第一项）
        # strip_root 后源码落在 src/ 子目录，Makefile 亦在 src/ 下；
        # 官方 tarball 则落在根目录。统一探测后再执行 make install。
        if os.path.exists(os.path.join(src, "src", "Makefile")):
            src = os.path.join(src, "src")
        self.run(f"find '{src}' -name install-sh -type f -exec chmod +x {{}} \\;")
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1 install DESTDIR='{self.package_folder}'")

    def package_info(self):
        self.cpp_info.libs = ["Vol"]
        # VolVolume.hpp 等头文件经 make install 装在 include/coin/（COIN-OR
        # 布局）；includedirs 需含 include/coin，下游 `#include <VolVolume.hpp>`
        # 才能解析（与 coinutils/coin-or 的 include/coin 惯例一致）
        self.cpp_info.includedirs = ["include", "include/coin"]
        self.cpp_info.libdirs = ["lib"]
