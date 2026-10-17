#!/usr/bin/env python3
"""Conan recipe — tcpflow 1.6.1

TCP/IP packet demultiplexer (network forensics / flow reassembly).
Upstream: https://github.com/simsong/tcpflow (tag tcpflow-1.6.1)
License: GPL-3.0

适配要点：
- 官方 GitHub release tarball 不含 git submodule（src/http-parser）内容，
  在 conandata.yml submodules 段声明固定 commit 源码并在 source() 合并；
- GitHub archive tarball 无预生成 configure，build() 中先 autoreconf 自举
  （需要 tool_requires automake/libtool）；
- 依赖（R27 格式）：zlib、openssl、libpcap、boost（configure.ac 强制检查）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class TcpflowConan(ConanFile):
    name = "tcpflow"
    version = "1.6.1"
    description = "TCP/IP packet demultiplexer - captures data transmitted as part of TCP connections (flows)"
    license = "GPL-3.0"
    homepage = "https://github.com/simsong/tcpflow"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # R32: settings.os must accept Linux and OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac 强制检查 zlib/openssl/boost；libpcap 为抓包核心依赖
        self.requires("zlib/1.3.1")
        self.requires("openssl/3.5.6")
        self.requires("libpcap/1.10.6")
        self.requires("boost/1.84.0")

    def build_requirements(self):
        # GitHub archive tarball 无 configure，需 autoreconf 自举
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        # 主源码包
        sources = self.conan_data["sources"]
        get(self, **{k: v for k, v in sources.items()
                      if k not in ("submodules",)},
            strip_root=True)
        # submodule（http-parser）固定 commit 源码合并到 src/http-parser/
        for sub in sources.get("submodules", []):
            sub_path = os.path.join(self.source_folder, sub["path"])
            os.makedirs(sub_path, exist_ok=True)
            get(self, url=sub["url"], sha256=sub["sha256"],
                strip_root=True, destination=sub_path)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: 终端工具默认静态链接（依赖链由 Conan 管理）
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 关闭 netviz（cairo 依赖链不在制品仓，非核心功能）与 wifi 解码
        tc.configure_args.append("--enable-cairo=false")
        tc.configure_args.append("--disable-wifi")
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # GitHub archive tarball 无 configure（autoreconf 产物不进版本库），先自举
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            autotools.autoreconf()
        # E175/E046: setgid/HMDFS 下 `(umask 077 && mktemp -d ./confXXXXXX)` 会创建
        # 2700 权限目录，config.status 写入 subs1.awk 时 Permission denied。
        # 必须在 autoreconf 之后修改（autoreconf 会重新生成 configure，改早了被覆盖）。
        import glob
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
                self.output.info(f"已修复 {_cfg}: umask 077 -> umask 022")
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # GPL-3.0 许可证文件
        license_src = os.path.join(self.source_folder, "COPYING")
        if os.path.isfile(license_src):
            copy(self, "COPYING", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))
        # 测试夹具：从上游源码（tests/test1.pcap）复制到包内测试专用目录
        # test/fixtures/。该目录不进入 cpp_info.bindirs，不作为生产 CLI 产物；
        # 仅供 test_package 通过 package_folder 定位（避免二进制夹具进入 PR diff）。
        upstream_fixture = os.path.join(self.source_folder, "tests", "test1.pcap")
        if os.path.isfile(upstream_fixture):
            copy(self, "test1.pcap",
                 src=os.path.join(self.source_folder, "tests"),
                 dst=os.path.join(self.package_folder, "test", "fixtures"))
            self.output.info("test1.pcap fixture packaged to test/fixtures/")

    def package_info(self):
        # 命令行工具：产物在 bin/，无库文件；测试夹具目录不暴露
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
