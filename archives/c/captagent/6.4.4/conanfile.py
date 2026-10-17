#!/usr/bin/env python3
"""Conan recipe — captagent 6.4.4（SIP/RTP 抓包代理，HEP 封装器）

captagent 是 sipcapture 出品的抓包代理：从 pcap 接口捕获 SIP/RTP/RTCP 等
报文，封装为 HEP（Homer Encapsulation Protocol）发送给 Homer 服务器。
C 语言，autotools 构建，主产物为可执行文件 captagent + 14 个动态模块
（socket/protocol/transport/interface/database 各插件 .so）。

依赖：
  - expat: XML 配置解析（硬依赖）
  - libpcap: 抓包（硬依赖）
  - json-c: JSON 输出模块（硬依赖）
  - libuv: 事件循环（硬依赖，configure.ac 无条件检查）
  - flex/bison: configure 硬性程序检查（AC_PROG_LEX/AC_PROG_YACC）
可选功能（默认关闭，不引入）：--enable-compression(zlib) / --enable-ssl
(openssl) / --enable-epan(wireshark) / --enable-pcre / --enable-redis
(hiredis) / --enable-tls(gcrypt) / --enable-extramodules。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, rm, rmdir, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain, Autotools, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class CaptagentConan(ConanFile):
    name = "captagent"
    version = "6.4.4"
    description = "SIP/RTP/RTCP packet capture agent with HEP encapsulation (sipcapture)"
    license = "AGPL-3.0"
    homepage = "https://github.com/sipcapture/captagent"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("expat/2.8.2.1.1")
        self.requires("libpcap/1.10.6")
        self.requires("json-c/0.18")
        self.requires("libuv/1.52.1")

    def build_requirements(self):
        # tarball 不带 configure：autoreconf -fi 需要
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("pkgconf/3.0.5")
        # configure.ac 硬性检查 flex(>=2.5.33)/bison，CI 无系统级，tool_requires 补齐
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E007: config.guess 无法识别 HarmonyOS，显式指定三元组
        # （build=linux-gnu 与 host=ohos 不同 → configure 识别为交叉编译，
        #   不会尝试运行目标二进制；两个都写 ohos 会导致 "cannot run C compiled programs"）
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
        ])
        tc.generate()

        deps = AutotoolsDeps(self)
        deps.generate()

        pkgdeps = PkgConfigDeps(self)
        pkgdeps.generate()

    def _drop_umask_077(self):
        """删掉 configure 里的 umask 077，避免 HMDFS 临时目录不可写（E011/E114）"""
        for _p in (os.path.join(self.source_folder, "configure"),
                   os.path.join(self.build_folder, "configure")):
            if not os.path.exists(_p):
                continue
            _data = open(_p, encoding="utf-8", errors="replace").read()
            _orig = _data
            _data = _data.replace(
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
            _data = _data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
            if _data != _orig:
                open(_p, "w", encoding="utf-8").write(_data)

    def _fix_captagentconf_data(self):
        """修复上游 out-of-source 构建缺陷：captagentconf_DATA 指向源目录。

        src/Makefile.am 的 `captagentconf_DATA = $(top_srcdir)/conf/$(sbin_PROGRAMS).xml`
        指向源目录 conf/captagent.xml，但该文件是 configure 生成物（config.status
        从 conf/captagent.xml.in 生成），out-of-source 构建时只在 build 目录存在，
        源 tar 里没有 → make 报 "No rule to make target .../conf/captagent.xml"。
        改为指向 $(top_builddir)/conf/（config.status 的生成位置）。必须在 autoreconf
        之前调用，让 automake 重新生成 Makefile.in 时带上修改。"""
        _p = os.path.join(self.source_folder, "src", "Makefile.am")
        if not os.path.exists(_p):
            return
        data = open(_p, encoding="utf-8", errors="replace").read()
        orig = data
        data = data.replace(
            "captagentconf_DATA = $(top_srcdir)/conf/$(sbin_PROGRAMS).xml",
            "captagentconf_DATA = $(top_builddir)/conf/$(sbin_PROGRAMS).xml")
        if data != orig:
            open(_p, "w", encoding="utf-8").write(data)

    def build(self):
        apply_conandata_patches(self)

        # 上游 out-of-source 缺陷：captagentconf_DATA 指向源目录（autoreconf 前修复）
        self._fix_captagentconf_data()

        # tarball 不带 configure：autoreconf -fi 生成
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")

        # HMDFS umask 077 解法（必须在 configure 运行前）
        self._drop_umask_077()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

        # 上游无集成测试（tests/ 只有 1 个孤儿源文件且未挂 Makefile），
        # make check 各子目录均为 "Nothing to be done"，此处执行以留证据
        self.run("make check", cwd=self.build_folder, env="conanbuild")

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

        autotools = Autotools(self)
        autotools.install()

        # 删除 libtool 辅助文件（模块插件 .la/.a 无用途）
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        rm(self, "*.a", os.path.join(self.package_folder, "lib"), recursive=True)

    def package_info(self):
        # 应用类：无可链接库，仅提供可执行文件路径
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin", "sbin"]

        # Conan2 runenv 注入，供下游 test_package 运行
        # （conan Autotools 归一化：安装到 package/bin，即便上游 sbin_prefix）
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
        _sbin = os.path.join(self.package_folder, "sbin")
        if os.path.isdir(_sbin):
            self.runenv_info.append_path("PATH", _sbin)
