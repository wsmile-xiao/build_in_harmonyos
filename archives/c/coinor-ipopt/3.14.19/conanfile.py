#!/usr/bin/env python3
"""Conan recipe — coinor-ipopt 3.14.19 (Autotools, mumps + openblas)

IPOPT (Interior Point Optimizer) 是 COIN-OR 的非线性优化求解器。
本配方：
  - requires mumps/5.9.1（稀疏线性求解器硬依赖）+ openblas/0.3.28（BLAS/LAPACK）
  - 通过生成的 coinmumps.pc 让 configure 的 AC_COIN_CHK_PKG(Mumps,...) 检测到 MUMPS
  - 平台补丁：config.guess/config.sub 支持 aarch64-unknown-linux-ohos；
    configure 的 tmp 目录创建改为 mkdir（HMDFS 上 mktemp 0700 目录不可写）
  - 链接期加 -lclang_rt.builtins（共享库内 128 位运算辅助符号）
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IpoptConan(ConanFile):
    name = "coinor-ipopt"
    version = "3.14.19"
    description = "Interior point optimizer - COIN-OR linear and nonlinear optimizer"
    license = "EPL-2.0"
    homepage = "https://coin-or.github.io/Ipopt/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("mumps/5.9.1")
        self.requires("openblas/0.3.28")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 生成 coinmumps.pc：IPOPT configure 通过 pkg-config coinmumps 检测 MUMPS
        mumps = self.dependencies["mumps"]
        blas = self.dependencies["openblas"]
        pc_dir = os.path.join(self.build_folder, "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        pc = os.path.join(pc_dir, "coinmumps.pc")
        with open(pc, "w") as f:
            f.write("""prefix=%s
libdir=${prefix}/lib
includedir=${prefix}/include

Name: coinmumps
Description: COIN-OR MUMPS interface (MUMPS 5.9.1 sparse direct solver)
Version: 5.9.1
Libs: -L${libdir} -ldmumps -lmumps_common -lpord -lmpiseq -lFortranRuntime -lFortranDecimal -lFortranCommon -L%s/lib -lopenblas -lpthread
Cflags: -I${includedir}
""" % (mumps.package_folder, blas.package_folder))
        self.output.info("coinmumps.pc -> %s" % pc)

        tc = AutotoolsToolchain(self)
        tc.configure_args.append(
            "--with-lapack-lflags=-L%s/lib -lopenblas" % blas.package_folder)
        # IPOPT 共享库内的 128 位运算需要 compiler-rt builtins（clang 链接共享库默认不自动带）
        sdk_lib = ""
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos"))
        if g:
            sdk_lib = g[-1]
        if sdk_lib:
            tc.extra_ldflags.append("-L%s -lclang_rt.builtins" % sdk_lib)
        tc.generate()

        # 让 configure 阶段能找到 coinmumps.pc
        from conan.tools.env import Environment
        env = Environment()
        env.append_path("PKG_CONFIG_PATH", pc_dir)
        env.vars(self).save_script("conanbuild_ipopt")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 移除 .la 文件（libtool 绝对路径烤死，.pc/cpp_info 已提供链接信息）
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["ipopt"]
        self.cpp_info.set_property("cmake_file_name", "coinor-ipopt")
        self.cpp_info.set_property("cmake_target_name", "coinor-ipopt::coinor-ipopt")
        self.cpp_info.set_property("pkg_config_name", "ipopt")
        self.cpp_info.includedirs.append("include/coin-or")

        # 运行期：libipopt.so 依赖系统 libc++_shared.so（OHOS aarch64）。
        # 用 prepend_path 把干净 /system/lib64 排在父环境所有路径之前：
        # 父环境 LD_LIBRARY_PATH 自带的 `/system/lib64` 带前导空格会被加载器跳过，
        # 且其 ->bundle 目录位于干净 /system/lib64 之前，导致先加载不匹配的 libc++。
        # （实测：干净 /system/lib64 在前则运行成功；bundle 在前则 relocation 失败）
        for _d in ("/data/storage/el1/bundle/libs/arm64", "/system/lib64"):
            if os.path.isdir(_d):
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", _d)
        self.output.info("runenv: LD_LIBRARY_PATH prepend 干净 /system/lib64（优先于父环境）")
