#!/usr/bin/env python3
"""Conan recipe — globus-callout 4.3 (Grid Community Toolkit callout library).

Build system: autotools (pkg-config based, globus-common >= 15 dependency)
Source: Debian pool orig tarball (globus-callout_4.3.orig.tar.gz)

Rules compliance:
  R1:  Minimal configure args (--prefix handled by AutotoolsToolchain)
  R27: 依赖 globus-common/18.15（制品仓已发布）+ libtool/2.5.4
  R32: settings.os validated with in ("Linux", "OHOS")
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import collect_libs, copy, get, replace_in_file, rm
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class GlobusCalloutConan(ConanFile):
    name = "globus-callout"
    version = "4.3"
    package_type = "library"
    license = "Apache-2.0"
    homepage = "https://github.com/gridcf/gct"
    url = ""  # CI fills this
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # R27: 依赖 globus-common（configure.ac PACKAGE_DEPS="globus-common >= 15"）
        #      + libtool（提供 ltdl.h/libdl——configure.ac AC_CHECK_HEADERS([ltdl.h])）
        self.requires("globus-common/18.15")
        self.requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"globus-callout only supports Linux/OHOS, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
        )

    @staticmethod
    def _ohos_triplet(arch):
        triplet = {
            "armv8": "aarch64-unknown-linux-ohos",
            "x86_64": "x86_64-unknown-linux-ohos",
        }.get(str(arch))
        if triplet is None:
            raise ConanInvalidConfiguration("Unsupported OHOS architecture")
        return triplet

    @staticmethod
    def _build_triplet(arch):
        triplet = {
            "armv8": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-unknown-linux-gnu",
        }.get(str(arch))
        if triplet is None:
            raise ConanInvalidConfiguration("Unsupported build architecture")
        return triplet

    def generate(self):
        # PkgConfigDeps: 生成 globus-common 的 .pc（configure 用
        # PKG_CHECK_MODULES([PACKAGE_DEP], globus-common >= 15) 需 .pc
        # 进 PKG_CONFIG_PATH——仅 AutotoolsDeps 不生成 .pc）
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # configure.ac 的 AC_ARG_VAR(LIBLTDL/LTDLINCL/LTDLDEPS)：用
        # buildenv_info 注入（进 conanbuild.sh，configure 运行时加载——
        # build() 里 os.environ 注入会被 conanbuild 环境覆盖，无效）
        lt = self.dependencies.get("libtool")
        if lt:
            lt_pkg = lt.package_folder
            if lt_pkg:
                self.buildenv_info.define(
                    "LTDLINCL", f"-I{os.path.join(lt_pkg, 'include')}")
                self.buildenv_info.define(
                    "LIBLTDL",
                    f"{os.path.join(lt_pkg, 'lib', 'libltdl.so')}")
                self.buildenv_info.define(
                    "LTDLDEPS",
                    f"-L{os.path.join(lt_pkg, 'lib')} -lltdl")
        if str(self.settings.os) == "OHOS":
            # Keep build and host distinct (同 globus-common 先例)
            tc.configure_args.extend(
                [
                    "--build={}".format(
                        self._build_triplet(self.settings_build.arch)
                    ),
                    "--host={}".format(self._ohos_triplet(self.settings.arch)),
                ]
            )
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # configure.ac 用 AC_ARG_VAR(LIBLTDL/LTDLINCL/LTDLDEPS)——在 build()
        # 阶段依赖已解析，os.environ 注入真实 libtool 包路径，使 configure
        # 走 LIBLTDL 分支而非 AC_CHECK_LIB（后者会让 libtool 链接按
        # libltdl.la 内错误 libdir='//lib' 解析 .la 失败）
        lt = self.dependencies.get("libtool")
        if lt:
            lt_pkg = lt.package_folder
            if lt_pkg:
                os.environ["LTDLINCL"] = f"-I{os.path.join(lt_pkg, 'include')}"
                os.environ["LIBLTDL"] = (
                    f"{os.path.join(lt_pkg, 'lib', 'libltdl.so')}")
                os.environ["LTDLDEPS"] = (
                    f"-L{os.path.join(lt_pkg, 'lib')} -lltdl")
        autotools = Autotools(self)
        autotools.configure()
        # libtool 链接 libglobus_callout.la 时会展开依赖的
        # libglobus_common.la/liblibltdl.la——其 dependency_libs 记录无效
        # libdir='//lib'，libtool 尝试 grep //lib/*.la 失败。
        # 修复: configure 生成的 Makefile LIBS 中的 -lglobus_common/-lltdl
        # 替换为绝对 .so 路径，让 libtool 不再解析 .la（手动验证可行）。
        # 必须在 make 之前替换（Makefile 由 configure 生成，非 make 生成）
        lt_pkg = None
        lt = self.dependencies.get("libtool")
        if lt:
            lt_pkg = lt.package_folder
        gc_pkg = None
        gc = self.dependencies.get("globus-common")
        if gc:
            gc_pkg = gc.package_folder
        if lt_pkg and gc_pkg:
            gc_so = os.path.join(gc_pkg, "lib", "libglobus_common.so")
            lt_so = os.path.join(lt_pkg, "lib", "libltdl.so")
            for _mk_rel in ("library", "test"):
                mf = os.path.join(self.build_folder, _mk_rel, "Makefile")
                if os.path.isfile(mf):
                    _c = open(mf).read()
                    _c = _c.replace("-lltdl", lt_so).replace(
                        "-lglobus_common", gc_so)
                    open(mf, "w").write(_c)
        autotools.make()
        # 上游单元测试实跑（审查 rule4）：test/ 的两个测试二进制
        # （callout_test/callout_chain_test，TAP 共 6 个测试点），依赖
        # libtest/libchaina/b/c 四个 dlpreopen 模块（已 -dlpreopen 链接进
        # 二进制）。注意：不能用 `make check`——其 LOG_COMPILER 为
        # `$(LIBTOOL) --mode=execute`，libtool 包装器会重置
        # LD_LIBRARY_PATH，导致 libglobus_common.so.0/libltdl.so.7
        # 运行时加载失败；直接运行二进制则通过。运行时需：
        #   - LD_LIBRARY_PATH：globus-common/libtool 包 lib + 本包 .libs
        #     （libglobus_callout.so.0 未 install，位于 build 目录）
        #   - srcdir：指向源码 test/ 目录（测试读 test.conf）
        # 实测两二进制 6/6 通过（callout_test 2/2，callout_chain_test 4/4）。
        if can_run(self):
            _ld = os.pathsep.join(
                _p for _p in (
                    os.path.join(gc_pkg, "lib") if gc_pkg else None,
                    os.path.join(lt_pkg, "lib") if lt_pkg else None,
                    os.path.join(self.build_folder, "library", ".libs"),
                ) if _p)
            _test_dir = os.path.join(self.build_folder, "test")
            # 先构建测试二进制（check_PROGRAMS 仅由 make check 触发构建；
            # 不跑 make check——其 LOG_COMPILER 是 libtool --mode=execute，
            # 会重置 LD_LIBRARY_PATH 导致运行时加载失败）
            self.run(
                f"cd '{_test_dir}' && make -j1 callout_test callout_chain_test",
                env="conanbuild",
            )
            for _t in ("callout_test", "callout_chain_test"):
                self.run(
                    f"cd '{_test_dir}' && "
                    f"LD_LIBRARY_PATH='{_ld}' "
                    f"srcdir='{os.path.join(self.source_folder, 'test')}' "
                    f"./{_t}",
                    env="conanbuild",
                )

    def package(self):
        copy(self, "GLOBUS_LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        Autotools(self).install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        libs = collect_libs(self)
        self.cpp_info.libs = [lib for lib in libs if "callout" in lib] or ["globus_callout"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "GlobusCallout")
        self.cpp_info.set_property("cmake_target_name", "Globus::Callout")
        self.cpp_info.set_property("pkg_config_name", "globus-callout")
        if str(self.settings.os) in ("Linux", "FreeBSD", "OHOS"):
            self.cpp_info.system_libs.extend(["pthread", "dl"])
