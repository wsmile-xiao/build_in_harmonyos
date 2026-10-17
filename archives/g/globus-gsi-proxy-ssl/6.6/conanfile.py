#!/usr/bin/env python3
"""Conan recipe — globus-gsi-proxy-ssl 6.6 (Grid Community Toolkit).

Globus GSI Proxy SSL 库：PROXYCERTINFO / PROXYPOLICY 两个 ASN.1 结构的
DER 编解码（RFC 3820 代理证书扩展），供 X.509 证书扩展处理使用。

Build system: autotools (pkg-config based; openssl >= 1.0)
Source: Debian pool orig tarball (globus-gsi-proxy-ssl_6.6.orig.tar.gz)

Rules compliance:
  R1:  Minimal configure args (--prefix handled by AutotoolsToolchain)
  R27: 仅依赖 openssl/3.5.6（configure.ac 唯一 PKG_CHECK_MODULES([OPENSSL],
       [openssl >= 1.0])；无 globus-common / thr/nothr 变体 / libltdl）
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


class GlobusGsiProxySslConan(ConanFile):
    name = "globus-gsi-proxy-ssl"
    version = "6.6"
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
        # R27: configure.ac 唯一外部依赖 PKG_CHECK_MODULES([OPENSSL],
        # [openssl >= 1.0])（无 globus-common 检查、无 thr/nothr 变体、
        # LT_INIT 仅 [dlopen win32-dll]，不含静态 ltdl）
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"globus-gsi-proxy-ssl only supports Linux/OHOS, "
                f"got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            strip_root=True)
        # configure 内 mktemp/mkdir 两处 umask 077（一次 replace_in_file
        # 全量替换；同 globus-common / globus-callout /
        # globus-gsi-openssl-error 先例）
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
        # PkgConfigDeps: 生成 openssl.pc（configure 的 PKG_CHECK_MODULES
        # 需 .pc 进 PKG_CONFIG_PATH——仅 AutotoolsDeps 不生成 .pc）
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Keep build and host distinct（同 globus-common / globus-callout
            # / globus-gsi-openssl-error 先例）
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
        # 本库 libglobus_proxy_ssl_la_LIBADD 仅 $(OPENSSL_LIBS)
        # （-lssl -lcrypto），openssl 无 .la，无需 .la 替换 hack。
        autotools.make()
        # 上游单元测试实跑（审查 rule4，模式同 globus-gsi-openssl-error 4.4）：
        # test/ TESTS = test_pci.pl（perl 驱动 Test::More，plan 4*5=20）：
        # 每个用例 4 断言（encode 运行 / decode 运行 / DER 往返比对 /
        # 两轮 stdout 自比），5 个用例共 20 断言；纯本地确定性，无网络/
        # 证书需求。不用 make check 驱动：perl 驱动经 PATH 找到的是 libtool
        # 包装脚本，其会重置 LD_LIBRARY_PATH 使依赖库加载失败（同 run
        # globus-gsi-openssl-error 4.4 教训）；构建后用 .libs 真实二进制
        # 替换包装脚本（仅构建产物，不改上游源文件），并注入
        # LD_LIBRARY_PATH = openssl 包 lib + 本包 library/.libs。
        if can_run(self):
            ssl = self.dependencies.get("openssl")
            ssl_lib = (
                os.path.join(ssl.package_folder, "lib")
                if ssl and ssl.package_folder else None)
            build_libs = os.path.join(self.build_folder, "library", ".libs")
            _ld = os.pathsep.join(
                _p for _p in (ssl_lib, build_libs) if _p)
            _test_dir = os.path.join(self.build_folder, "test")
            # check_PROGRAMS 仅由 make check 触发构建，这里显式构建
            self.run(
                f"cd '{_test_dir}' && make -j1 test_pci",
                env="conanbuild",
            )
            # 用 .libs 真实 ELF 替换 libtool 包装脚本，避免运行时被重置
            # LD_LIBRARY_PATH（构建产物替换，上游测试脚本/数据不动）
            self.run(
                f"cd '{_test_dir}' && cp -f .libs/test_pci test_pci",
                env="conanbuild",
            )
            # VPATH 构建：perl 驱动与期望输出 .stdout 位于源码 test/ 目录；
            # 驱动自行将 dirname($0) 与 . prepend 进 PATH
            self.run(
                f"cd '{_test_dir}' && "
                f"LD_LIBRARY_PATH='{_ld}' "
                f"perl '{os.path.join(self.source_folder, 'test', 'test_pci.pl')}'",
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
            lib for lib in libs if "proxy_ssl" in lib
        ] or ["globus_proxy_ssl"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "GlobusGsiProxySsl")
        self.cpp_info.set_property("cmake_target_name",
                                   "Globus::GsiProxySsl")
        self.cpp_info.set_property("pkg_config_name",
                                   "globus-gsi-proxy-ssl")
        # 向消费者传递依赖 traits（headers/libs/run）：下游 test_package/
        # 消费者才能继续拿到 openssl 的头文件与库（否则该依赖在下游图中
        # 被 skip，package_folder 为 None）。格式 pkg::pkg，同
        # globus-gsi-openssl-error 4.4 先例。
        self.cpp_info.requires = ["openssl::openssl"]
        # 纯 ASN.1 编解码库：无 pthread/dl 需求（.pc 亦仅
        # Requires.private: openssl）
