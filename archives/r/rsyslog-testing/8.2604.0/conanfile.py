#!/usr/bin/env python3
"""rsyslog-testing 8.2604.0 — rsyslog omtesting 输出模块（omtesting.so）Conan 配方。

打包口径（同族先例：archives/k/kamailio-outbound/6.0.6、kamailio-debugger/6.0.6
的「官方全量源码包 + 仅编译打包目标 .so」口径）：
  - 取官方 rsyslog 8.2604.0 源码包全量构建，仅编译打包 omtesting 模块；
  - 不依赖 rsyslog 本体包：模块 .so 由 rsyslogd 运行时 loadmodule 加载；
  - package_type=shared-library，cpp_info.libs=[]（模块不作为链接库供消费者使用），
    产物无命令行可执行文件 → 不建 commands.json（R38）。

构建体系：autotools（configure + automake 递归 make）
  ./configure <args>                    → 顶层与 plugins/omtesting/Makefile
  make -C plugins/omtesting -j1 LIBS=   → plugins/omtesting/.libs/omtesting.so

HarmonyOS / OHOS 适配要点：
1. config.guess/config.sub 补丁（0002/0003）：源码包自带脚本无法识别
   uname -s = "HarmonyOS"，configure 直接以 "cannot guess build type" 退出（E007）；
   补丁后 config.guess 输出 aarch64-unknown-linux-ohos。
2. configure 补丁（0001，E011）：临时目录块 "umask 077 && mktemp -d" 在 HMDFS 上
   创建的目录对构建进程不可写，umask 放宽为 000（先例：libestr / libfastjson /
   rsyslog 8.2404.0 配方）。
3. 模块链接显式清空 $(LIBS)：configure.ac 使 zlib 成为必需依赖并把 "-lz" 注入
   全局 LIBS，automake 默认给所有链接目标带上 $(LIBS)，会使模块产生
   DT_NEEDED libz.so；而 omtesting.c 不引用任何 zlib 符号（llvm-nm -u 实测无
   inflate/deflate/crc32/adler），且目标机 /usr/lib 只有 libz.so.1（无 libz.so），
   该 NEEDED 会让 rsyslogd loadmodule / dlopen 直接失败。故仅对模块目标传
   LIBS=（先例 rsyslog 8.2404.0 以静态 PIC zlib/1.3.1.1 规避同类问题）。
4. 依赖发现：libestr/libfastjson 的 .pc 记录 prefix="/"（DESTDIR 风格）会产出
   -I//include / -L//lib 这类不可用路径，且 cpp_info.libs 名与真实链接名不同
   （estr / fastjson）；沿用 rsyslog 8.2404.0 先例，用 pkg.m4 的 LIBESTR_*/
   LIBFASTJSON_* 覆盖变量直指 conan 包内真实路径。
5. 可选依赖全部关闭：--disable-impstats / --disable-impstats-push（impstats-push
   默认自动启用，需要 protoc-c，CI 无该工具链）、--disable-liblogging-stdlog
   （liblogging 未发布到制品仓）、--disable-fmhttp（libcurl 不在依赖集）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RsyslogTestingConan(ConanFile):
    name = "rsyslog-testing"
    version = "8.2604.0"
    description = ("rsyslog omtesting output module: test/simulation action "
                   "(sleep, fail and random-fail sequencing) for rsyslog rulesets")
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
        # 与本地已验证的 configure 调用逐字一致（config.status 记录的
        # ac_cs_config）。显式关闭全部可选特性而非依赖自动探测：
        #   1) 探测结果随构建机环境漂移（同一条配方在不同 worker 上可能开启不同
        #      特性），显式关闭使 CI 与本地可复现；
        #   2) 探测命中的系统第三方库会把 -lxxx/-D 注入全局 LIBS/CPPFLAGS，进而
        #      出现在本模块的链接命令行上，给 omtesting.so 带上目标机不存在的
        #      动态依赖串（同 docstring 第 3 条的 zlib 问题）；
        #   3) --disable-impstats-push 必需：该特性默认自动启用并需要 protoc-c，
        #      CI 无该工具链（本地 configure 实测卡点）；
        #   4) --disable-fmhttp / --disable-liblogging-stdlog：libcurl / liblogging
        #      未在依赖集内。
        for arg in ("--disable-testbench", "--disable-uuid", "--disable-libgcrypt",
                    "--disable-openssl", "--disable-gnutls", "--disable-mbedtls",
                    "--disable-libsystemd", "--disable-jemalloc", "--disable-valgrind",
                    "--disable-diagtools", "--disable-usertools", "--disable-mysql",
                    "--disable-pgsql", "--disable-libdbi", "--disable-snmp",
                    "--disable-elasticsearch", "--disable-clickhouse",
                    "--disable-omhttp", "--disable-wolfssl", "--disable-libzstd",
                    "--disable-relp", "--disable-ksi-ls12", "--disable-rfc3195",
                    "--disable-fmhttp", "--disable-impstats-push",
                    "--disable-impstats", "--disable-mmdblookup",
                    "--disable-omfile-hardened"):
            tc.configure_args.append(arg)

        env = tc.environment()

        # pkg-config 检查：用真实 conan 包路径覆盖（见模块 docstring 第 4 条）
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
        autotools.make(args=["-C", "plugins/omtesting", "-j1", "LIBS="])

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Autotools 助手以 out-of-source 方式构建：self.build_folder 即
        # build-<build_type>/ 目录，模块产物落于其中的 plugins/omtesting/.libs
        # （libtool 的可加载模块输出目录），源码树内不产生构建产物。
        module_dir = os.path.join(self.build_folder, "plugins", "omtesting", ".libs")
        if not os.path.isfile(os.path.join(module_dir, "omtesting.so")):
            raise ConanException(f"omtesting.so not found in {module_dir}")
        copy(self, "omtesting.so", src=module_dir,
             dst=os.path.join(self.package_folder, "lib", "rsyslog"))

    def package_info(self):
        # 模块由 rsyslogd 运行时 loadmodule 加载，不作为链接库（R38：非 CLI 包）
        self.cpp_info.libdirs = ["lib/rsyslog"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("rsyslog_modules_dir", "lib/rsyslog")
        # rsyslogd 经 RSYSLOG_MODDIR 定位可加载模块（运行时/modules.c 读取该变量）
        self.runenv_info.define("RSYSLOG_MODDIR",
                                os.path.join(self.package_folder, "lib", "rsyslog"))
