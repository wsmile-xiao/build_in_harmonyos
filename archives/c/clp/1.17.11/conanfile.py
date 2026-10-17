#!/usr/bin/env python3
"""Conan recipe for COIN-OR Clp 1.17.11 - OpenHarmony aarch64 port.

Clp is the COIN-OR Linear Programming solver. Autotools build, depends on
CoinUtils and Osi (both already ported in this repo).
"""

import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rm,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


required_conan_version = ">=2.28"


class ClpConan(ConanFile):
    name = "clp"
    version = "1.17.11"
    description = "COIN-OR Linear Programming Solver (Clp)"
    topics = ("coin-or", "clp", "lp", "solver")
    url = "https://github.com/coin-or/Clp"
    homepage = "https://github.com/coin-or/Clp"
    license = "EPL-2.0"
    package_type = "library"

    settings = "os", "arch", "build_type", "compiler"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
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
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("coinutils/2.11.13", transitive_headers=True)
        self.requires("coin-or/0.108.12", transitive_headers=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-blas",
            "--without-lapack",
            "--without-glpk",
            "--without-pthread",
            "--disable-dependency-tracking",
        ])
        # 必须 -fPIC：静态库会链接进 PIE 可执行文件（test_package 消费者），
        # 非 PIC 库导致运行时 text 重定位 SegFault（libClp.a 有 12 处
        # R_AARCH64_ADDR_PREL/ABS 重定位可证）。coin-osi 先例同样带 -fPIC。
        if self.options.get_safe("fPIC"):
            tc.extra_cxxflags.append("-fPIC")
            tc.extra_cflags.append("-fPIC")
        env = tc.environment()
        tc.generate(env)

        # CoinUtils/Osi 依赖通过 pkg-config 暴露（Clp configure 用
        # AC_COIN_CHECK_PACKAGE 查找 coinutils/osi 的 .pc 文件）
        deps = PkgConfigDeps(self)
        deps.generate()
        env.define("PKG_CONFIG_PATH", self.generators_folder)

    def build(self):
        if str(self.settings.os) == "OHOS":
            work_folder = self._ohos_work_folder()
            previous_umask = os.umask(0o002)
            try:
                os.makedirs(work_folder, mode=0o775, exist_ok=True)
            finally:
                os.umask(previous_umask)

            # HMDFS umask 077 会让 configure 的临时目录不可写，改为 002
            for configure in (
                os.path.join(self.source_folder, "configure"),
                os.path.join(self.source_folder, "Clp", "configure"),
            ):
                if not os.path.isfile(configure):
                    continue
                replace_in_file(
                    self,
                    configure,
                    "(umask 077 && mkdir $tmp)",
                    "(umask 002 && mkdir $tmp)",
                )
                replace_in_file(
                    self,
                    configure,
                    "umask 077 && mktemp -d",
                    "umask 002 && mktemp -d",
                )

            configure_args = load_toolchain_args(self.generators_folder).get(
                "configure_args", ""
            )
            configure = os.path.join(self.source_folder, "configure")
            config_shell = "/system/bin/sh"
            command = shlex.join([config_shell, configure])
            command = f"CONFIG_SHELL={shlex.quote(config_shell)} {command}"
            # 依赖头文件显式注入：PkgConfigDeps 生成的 coinutils.pc Cflags
            # 只含 ${prefix}/include，而 COIN-OR 头文件实际在 include/coin/
            # 子目录（CoinPragma.hpp 等）——必须 --with-*-incdir 注入，
            # 否则 ClpCholeskyBase.cpp 编译报 CoinPragma.hpp not found
            # （1.17.10 已合入配方同款做法）。
            _cu = self.dependencies["coinutils"]
            _osi = self.dependencies["coin-or"]
            _zl = self.dependencies["zlib"]
            command += (
                f" --with-coinutils-incdir={_cu.package_folder}/include/coin"
                f" --with-coinutils-lib='{_cu.package_folder}/lib/libCoinUtils.a"
                f" {_zl.package_folder}/lib/libz.a -lm'"
                f" --with-osi-incdir={_osi.package_folder}/include/coin"
                f" --with-osi-lib='{_osi.package_folder}/lib/libOsi.a"
                f" {_cu.package_folder}/lib/libCoinUtils.a"
                f" {_zl.package_folder}/lib/libz.a -lm'"
            )
            if configure_args:
                command = f"{command} {configure_args}"
            self.run(command, cwd=work_folder)
            self.run("make -j1", cwd=work_folder)
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if str(self.settings.os) == "OHOS":
            destination = shlex.quote(self.package_folder)
            self.run(
                f"make install DESTDIR={destination} -j1",
                cwd=self._ohos_work_folder(),
            )
        else:
            autotools = Autotools(self)
            autotools.install(args=["-j1"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        self._sign_shared_libraries()

    def _ohos_work_folder(self):
        return os.path.join(self.build_folder, "ohos-work")

    def _sign_shared_libraries(self):
        if str(self.settings.os) != "OHOS" or not self.options.get_safe("shared"):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS shared libraries require llvm-objcopy and binary-sign-tool"
            )
        libraries = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
        )
        for library in libraries:
            if os.path.islink(library):
                continue
            original_mode = os.stat(library).st_mode
            temporary = f"{library}.signing"
            try:
                shutil.copy2(library, temporary)
                self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
                self.run(
                    f'"{signer}" sign -inFile "{temporary}" '
                    f'-outFile "{temporary}" -selfSign 1'
                )
                os.chmod(temporary, original_mode)
                os.replace(temporary, library)
            finally:
                if os.path.exists(temporary):
                    os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "clp")
        self.cpp_info.libs = ["Clp", "ClpSolver", "OsiClp"]
        self.cpp_info.includedirs = [os.path.join("include", "coin")]
        # OsiClpSolverInterface.hpp 引用 OsiSolverInterface.hpp（coin-or 包
        # include/coin 下，coin-or 配方只暴露了自己的 include/ 未含 coin
        # 子目录）——显式暴露依赖头目录（同 coin-or 暴露 coinutils 做法）
        _osi = self.dependencies["coin-or"]
        self.cpp_info.includedirs.append(
            os.path.join(_osi.package_folder, "include", "coin"))
        self.cpp_info.requires = [
            "coinutils::coinutils",
            "coin-or::coin-or",
        ]
