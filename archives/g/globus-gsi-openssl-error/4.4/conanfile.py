#!/usr/bin/env python3
"""Conan recipe — globus-gsi-openssl-error 4.4 (Grid Community Toolkit).

Globus GSI OpenSSL 错误处理包装库（将 OpenSSL 错误队列条目包装为
globus_object_t 错误对象，供 GSI 链上层库使用）。

Build system: autotools (pkg-config based; openssl >= 1.0 + globus-common >= 14)
Source: Debian pool orig tarball (globus-gsi-openssl-error_4.4.orig.tar.gz)

Rules compliance:
  R1:  Minimal configure args (--prefix handled by AutotoolsToolchain)
  R27: 依赖 globus-common/18.15（制品仓已发布）+ openssl/3.5.6（仓内主流钉版）
  R32: settings.os validated with in ("Linux", "OHOS")
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, collect_libs, copy, get
from conan.tools.files import export_conandata_patches, replace_in_file, rm
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class GlobusGsiOpensslErrorConan(ConanFile):
    name = "globus-gsi-openssl-error"
    version = "4.4"
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
        # R27: configure.ac PKG_CHECK_MODULES 仅两项：
        #   [OPENSSL] openssl >= 1.0 + PACKAGE_DEPS="globus-common >= 14"
        # （无 libltdl 依赖——LT_INIT 仅 [dlopen win32-dll]，不含静态 ltdl）
        self.requires("globus-common/18.15")
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"globus-gsi-openssl-error only supports Linux/OHOS, "
                f"got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            strip_root=True)
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
        # PkgConfigDeps: 生成 openssl.pc / globus-common.pc（configure 的
        # PKG_CHECK_MODULES 需 .pc 进 PKG_CONFIG_PATH——仅 AutotoolsDeps
        # 不生成 .pc）
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Keep build and host distinct（同 globus-common/globus-callout 先例）
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
        autotools = Autotools(self)
        autotools.configure()
        # libtool 链接展开 -lglobus_common 时若解析到 .la（dependency_libs
        # 记录无效 libdir）会失败——同 globus-callout 4.3 先例：把 configure
        # 生成的 Makefile 中 -lglobus_common 替换为 globus-common 包内
        # libglobus_common.so 绝对路径，让 libtool 直接链接 .so 不再解析 .la。
        # openssl 无 .la，-lssl/-lcrypto 不受影响。必须在 make 之前替换
        # （Makefile 由 configure 生成）。
        gc = self.dependencies.get("globus-common")
        gc_pkg = gc.package_folder if gc else None
        if gc_pkg:
            gc_so = os.path.join(gc_pkg, "lib", "libglobus_common.so")
            for _mk_rel in ("library", "test"):
                mf = os.path.join(self.build_folder, _mk_rel, "Makefile")
                if os.path.isfile(mf):
                    _c = open(mf).read()
                    _c = _c.replace("-lglobus_common", gc_so)
                    open(mf, "w").write(_c)
        autotools.make()
        # 上游单元测试实跑（审查 rule4，模式同 globus-callout 4.3 整改）：
        # test/ TESTS = globus-openssl-error-test.pl（automake parallel-tests
        # TAP，4 断言）：构建 globus_openssl_error_test 后由 perl 驱动运行
        # 并逐行比对 globus_openssl_error_test.stdout 期望正则（进程内测试，
        # 无网络/证书需求）。不用 make check 驱动：perl 驱动经 PATH 找到的
        # 是 libtool 包装脚本，其会重置 LD_LIBRARY_PATH 使依赖库加载失败
        # （同 callout 教训）；构建后用 .libs 真实二进制替换包装脚本（仅
        # 构建产物，不改上游源文件），并注入 LD_LIBRARY_PATH =
        # globus-common 包 lib + openssl 包 lib + 本包 library/.libs。
        # 实测 4/4 通过（见 CI 日志 TAP 输出）。
        if can_run(self):
            gc_lib = os.path.join(gc_pkg, "lib") if gc_pkg else None
            ssl = self.dependencies.get("openssl")
            ssl_lib = (
                os.path.join(ssl.package_folder, "lib")
                if ssl and ssl.package_folder else None)
            build_libs = os.path.join(self.build_folder, "library", ".libs")
            _ld = os.pathsep.join(
                _p for _p in (gc_lib, ssl_lib, build_libs) if _p)
            _test_dir = os.path.join(self.build_folder, "test")
            # check_PROGRAMS 仅由 make check 触发构建，这里显式构建
            self.run(
                f"cd '{_test_dir}' && make -j1 globus_openssl_error_test",
                env="conanbuild",
            )
            # 用 .libs 真实 ELF 替换 libtool 包装脚本，避免运行时被重置
            # LD_LIBRARY_PATH（构建产物替换，上游测试脚本/数据不动）
            self.run(
                f"cd '{_test_dir}' && "
                f"cp -f .libs/globus_openssl_error_test "
                f"globus_openssl_error_test",
                env="conanbuild",
            )
            # VPATH 构建：perl 驱动与期望输出 .stdout 位于源码 test/ 目录
            # （构建目录只有生成的 Makefile 与产物）
            self.run(
                f"cd '{_test_dir}' && "
                f"LD_LIBRARY_PATH='{_ld}' "
                f"perl '{os.path.join(self.source_folder, 'test', 'globus-openssl-error-test.pl')}'",
                env="conanbuild",
            )

    def package(self):
        copy(self, "GLOBUS_LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        Autotools(self).install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        libs = collect_libs(self)
        self.cpp_info.libs = [
            lib for lib in libs if "openssl_error" in lib
        ] or ["globus_openssl_error"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "GlobusGsiOpensslError")
        self.cpp_info.set_property("cmake_target_name",
                                   "Globus::GsiOpensslError")
        self.cpp_info.set_property("pkg_config_name",
                                   "globus-gsi-openssl-error")
        # 向消费者传递依赖 traits（headers/libs/run）：下游 test_package/
        # 消费者才能继续拿到 openssl/globus-common 的头文件与库（否则这些
        # 依赖在下游图中被跳过，package_folder 为 None）。格式 pkg::pkg，
        # 同 abiword-plugin-openwriter 3.0.8 先例。
        self.cpp_info.requires = [
            "globus-common::globus-common",
            "openssl::openssl",
        ]
        if str(self.settings.os) in ("Linux", "FreeBSD", "OHOS"):
            self.cpp_info.system_libs.extend(["pthread", "dl"])
