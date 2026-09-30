#!/usr/bin/env python3
"""rsyslog-cisco 8.2604.0 — rsyslog Cisco 解析模块（pmciscoios + pmcisconames）Conan 配方。

打包口径（同族先例：archives/r/rsyslog-testing/8.2604.0 及 kamailio 模块型配方）：
  - 取官方 rsyslog 8.2604.0 源码包全量构建，仅编译打包两个 Cisco 模块：
      plugins/pmciscoios   → pmciscoios.so    (MODULE_TYPE_PARSER,
                                                PARSER_NAME "rsyslog.ciscoios", 入口 parse2)
      contrib/pmcisconames → pmcisconames.so  (MODULE_TYPE_PARSER,
                                                PARSER_NAME "rsyslog.cisconames", 入口 parse)
  - 不依赖 rsyslog 本体包：模块 .so 由 rsyslogd 运行时 loadmodule 加载（规则集内以
    ":pmciscoios:..." / ":pmcisconames:..." 指示符引用）；
  - package_type=shared-library，cpp_info.libs=[]（模块不作为链接库供消费者使用）；
  - 产物无命令行可执行文件 → 不建 commands.json（R38）。

构建体系：autotools
  ./configure --enable-pmciscoios --enable-pmcisconames <args> → 各模块 Makefile
  make -C plugins/pmciscoios   -j1 LIBS=  → plugins/pmciscoios/.libs/pmciscoios.so
  make -C contrib/pmcisconames -j1 LIBS=  → contrib/pmcisconames/.libs/pmcisconames.so

HarmonyOS / OHOS 适配要点：
1. config.guess/config.sub 补丁（0001/0002）：源码包自带脚本无法识别
   uname -s = "HarmonyOS"，configure 直接以 "cannot guess build type" 退出（E007）；
   补丁后 config.guess 输出 aarch64-unknown-linux-ohos。
2. configure 补丁（0003，E011）：临时目录块 "umask 077 && mktemp -d" 在 HMDFS 上
   创建的目录对构建进程不可写，umask 放宽为 000（先例：libestr / libfastjson /
   rsyslog 8.2404.0 / rsyslog-testing 8.2604.0）。
3. 模块链接显式清空 $(LIBS)：configure.ac 使 zlib 成为必需依赖并把 "-lz" 注入
   全局 LIBS，automake 默认给所有链接目标带上 $(LIBS)，会使模块产生
   DT_NEEDED libz.so；而目标机 /usr/lib 只有 libz.so.1（无 libz.so），该 NEEDED
   会让 rsyslogd loadmodule / dlopen 直接失败。两个模块均不引用任何 zlib 符号
   （llvm-nm -u 实测无 inflate/deflate/crc32/adler），故仅对模块目标传 LIBS=。
4. 依赖发现：libestr/libfastjson 的 .pc 记录 prefix="/"（DESTDIR 风格）会产出
   -I//include / -L//lib 这类不可用路径，且 cpp_info.libs 名与真实链接名不同
   （estr / fastjson）；沿用 rsyslog 8.2404.0 / rsyslog-testing 8.2604.0 先例，用
   pkg.m4 的 LIBESTR_*/LIBFASTJSON_* 覆盖变量直指 conan 包内真实路径。
5. 可选依赖全部显式关闭：探测结果随构建机环境漂移（同一配方在不同 worker 上开启
   不同特性），显式关闭使 CI 与本地可复现；--disable-impstats / --disable-impstats-push
   必需（impstats-push 默认自动启用并需要 protoc-c，CI 无该工具链）；
   --disable-fmhttp（libcurl 不在依赖集）。
6. 两个模块均为 Parser 类型（非 Output 模块），没有工作线程实例：消费侧 dlopen 后
   经 modInit 注册并 queryEtryPt 取 parse2 / parse 入口，rsyslogd 按 PARSER_NAME
   匹配规则指示符调用（test_package 按此真实链路验证）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# (模块源码目录, 模块名) —— configure 期以 --enable-<模块名> 开启
MODULES = (
    ("plugins/pmciscoios", "pmciscoios"),
    ("contrib/pmcisconames", "pmcisconames"),
)


class RsyslogCiscoConan(ConanFile):
    name = "rsyslog-cisco"
    version = "8.2604.0"
    description = ("rsyslog Cisco parser modules: pmciscoios (Cisco IOS syslog "
                   "message parsing) and pmcisconames (Cisco interface/hostname "
                   "name resolution)")
    license = "GPL-3.0-or-later"
    homepage = "https://www.rsyslog.com/"
    url = "https://github.com/rsyslog/rsyslog"

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")

    def requirements(self):
        # 模块编译期经 rsyslog 头文件解析这两个依赖的类型/宏
        self.requires("libestr/0.1.11")
        self.requires("libfastjson/1.2609.0")
        # configure 对 zlib 是硬性检查（PKG_CHECK_MODULES 失败后 AC_SEARCH_LIBS
        # 再失败即 AC_MSG_ERROR），CI 干净环境下缺 libz 会直接中断 configure；
        # 模块自身不引用任何 zlib 符号（见 docstring 第 3 条），链接期以 LIBS=
        # 清空，故仅作为 configure 期依赖存在，不进入模块 DT_NEEDED。
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # 源码下载加固：conan 默认仅重试 2 次 × 5s，不足以跨过 CI worker 到
        # www.rsyslog.com 的链路抖动（同 kamailio-outbound PR #12957 CI 实测）。
        # URL/sha256 保持官方源不变（R39/PF7）。
        get(self, **self.conan_data["sources"], strip_root=True, retry=6, retry_wait=20)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 与本地已验证的 configure 调用逐字一致（config.status 记录的 ac_cs_config）。
        # 显式开启目标模块、关闭全部可选特性，而非依赖自动探测：
        #   1) 探测结果随构建机环境漂移，显式关闭使 CI 与本地可复现；
        #   2) 探测命中的系统第三方库会把 -lxxx/-D 注入全局 LIBS/CPPFLAGS，进而
        #      出现在模块链接命令行上，给模块带上目标机不存在的动态依赖串
        #      （见 docstring 第 3 条的 zlib 问题）；
        #   3) --disable-impstats-push 必需：该特性默认自动启用并需要 protoc-c，
        #      CI 无该工具链；
        #   4) --disable-fmhttp / --disable-liblogging-stdlog：libcurl / liblogging
        #      未在依赖集内。
        for arg in ("--enable-pmciscoios", "--enable-pmcisconames",
                    "--disable-testbench", "--disable-uuid", "--disable-libgcrypt",
                    "--disable-openssl", "--disable-gnutls", "--disable-mbedtls",
                    "--disable-libsystemd", "--disable-jemalloc", "--disable-valgrind",
                    "--disable-diagtools", "--disable-usertools", "--disable-mysql",
                    "--disable-pgsql", "--disable-libdbi", "--disable-snmp",
                    "--disable-elasticsearch", "--disable-clickhouse",
                    "--disable-omhttp", "--disable-wolfssl", "--disable-libzstd",
                    "--disable-relp", "--disable-ksi-ls12", "--disable-rfc3195",
                    "--disable-fmhttp", "--disable-impstats-push",
                    "--disable-impstats", "--disable-mmdblookup",
                    "--disable-omfile-hardened", "--disable-liblogging-stdlog"):
            tc.configure_args.append(arg)

        env = tc.environment()

        # pkg-config 检查：用真实 conan 包路径覆盖（见 docstring 第 4 条）
        pkg_overrides = [
            ("libestr", "LIBESTR", "estr", ""),
            ("libfastjson", "LIBFASTJSON", "fastjson", "libfastjson"),
            ("zlib", "ZLIB", "z", ""),
        ]
        for dep_name, var, lib, inc_sub in pkg_overrides:
            info = self.dependencies[dep_name].cpp_info.aggregated_components()
            incdir = os.path.join(info.includedirs[0], inc_sub) if inc_sub \
                else info.includedirs[0]
            env.define(f"{var}_CFLAGS", f"-I{incdir}")
            env.define(f"{var}_LIBS", f"-L{info.libdirs[0]} -l{lib}")

        tc.generate(env)

    def build(self):
        # HMDFS：默认 umask 可能生成 640 文件，后续步骤不可读
        if self.settings.os in ("Linux", "OHOS"):
            os.umask(0o022)

        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()
        # 仅构建目标模块；LIBS= 清掉 configure 注入的全局 -lz（见 docstring 第 3 条）
        for mod_dir, _mod_name in MODULES:
            autotools.make(args=["-C", mod_dir, "-j1", "LIBS="])

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Autotools 助手以 out-of-source 方式构建：self.build_folder 即
        # build-<build_type>/ 目录，模块产物落于其中的 <模块目录>/.libs
        # （libtool 的可加载模块输出目录），源码树内不产生构建产物。
        dst_dir = os.path.join(self.package_folder, "lib", "rsyslog")
        for mod_dir, mod_name in MODULES:
            src_dir = os.path.join(self.build_folder, mod_dir, ".libs")
            if not os.path.isfile(os.path.join(src_dir, f"{mod_name}.so")):
                raise ConanException(f"{mod_name}.so not found in {src_dir}")
            copy(self, f"{mod_name}.so", src=src_dir, dst=dst_dir)

    def package_info(self):
        # 模块由 rsyslogd 运行时 loadmodule 加载，不作为链接库（R38：非 CLI 包）
        self.cpp_info.libdirs = ["lib/rsyslog"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("rsyslog_modules_dir", "lib/rsyslog")
        # rsyslogd 经 RSYSLOG_MODDIR 定位可加载模块（运行时/modules.c 读取该变量）
        self.runenv_info.define("RSYSLOG_MODDIR",
                                os.path.join(self.package_folder, "lib", "rsyslog"))
