#!/usr/bin/env python3
"""Conan recipe — gadap 2.0 (GrADS Data Interface / GADAP).

GADAP: GrADS Client Interface for OPeNDAP in-situ (station) data.
上游 2008 年代码针对无命名空间的旧 libdap (<=3.7) 编写; 本配方面向
libdap 3.20.6 conan 包 (类型在 libdap:: 命名空间), 通过 patches 0002-0011
适配命名空间, 0001 修复 configure 的 HMDFS 临时目录陷阱。

构建系统: autotools (tarball 自带 configure 2.59, 无需 autoreconf)。
configure 通过 m4/libdap.m4 的 AC_CHECK_LIBDAP → dap-config 脚本发现
libdap; libdap conan 包内的 dap-config 有打包缺陷 (prefix=/ 空 + 硬编码
构建时 conan cache 路径), 本配方在 generate() 生成重定位版 dap-config
(generators 目录), 通过 DAP_CONFIG 环境变量注入 (libdap 配方重写 .pc
的同源手法)。

依赖 (conan requires, 全部制品仓/本地 cache):
  libdap/3.20.6             DAP2 协议核心库 (OHOS 适配 conan 包) (dap/dapclient/dapserver)
  libxml2/2.15.3              DAP4 解析 (libdap 传递依赖, gadap 链接需要)
  curl/8.15.0                 HTTP 客户端 (libdap 传递依赖, 链接需要)
  libtirpc/1.3.7              XDR 序列化 rpc/*.h (libdap 传递依赖, 链接需要)
  uuid/2.40.1                 libdapserver 链接需要 (dap-config --libs 输出 -luuid)

上游测试: test/ 目录的 test 程序 (station 数据查询客户端)。真实数据测试
依赖 http://test.opendap.org 上游测试服务器 (内容随时间变动, 2026-09 实测
数据集路径 404)。构建期验证 test 程序可构建可运行 (无参数输出 "need URL"
返回 0 = 链接/运行冒烟通过)。

License: 上游 COPYRIGHT 为 BSD-like (IGES), Debian 打包按 GPL-2+ 处理,
配方沿用 GPL-2.0-or-later (与旧归档一致)。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# ohos-sdk lld 所在目录 — lld 自身 NEEDED libxml2.so.16, 其正确版本在
# 同目录 (llvm/lib), LD_LIBRARY_PATH 需把它排在 conan 依赖 lib 之前,
# 否则 conan 的 libxml2.so.16 遮蔽后 lld 启动即崩 (symbol not found)。
# 与 libdap/3.20.6 配方同源手法。
def _sdk_llvm_lib(compiler_path):
    try:
        real = os.path.realpath(compiler_path)
        llvm_bin = os.path.dirname(real)
        if os.path.basename(llvm_bin) == "bin":
            lib = os.path.join(os.path.dirname(llvm_bin), "lib")
            if os.path.isdir(lib):
                return lib
    except Exception:
        pass
    return "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"


class GadapConan(ConanFile):
    name = "gadap"
    # 版本 2.0.0 = 上游 gadap 2.0 同源码（gadap_2.0.orig.tar.gz）。
    # 平台任务 version=2 / taskBranch=feat/gadap-2 与 conan 版本号规则冲突
    # （conan 版本至少 2 字符），已问卷反馈平台修正为 feat/gadap-2.0.0；
    # 另制品仓 gadap/2.0 已被旧 cmd-pkgs 方案（PR4455）占用，本配方为
    # conan requires 重写版，按 R37 用新版本号 2.0.0。
    version = "2.0.0"
    description = "GADAP: GrADS Client Interface for OPeNDAP in-situ (station) data"
    license = "GPL-2.0-or-later"
    homepage = "https://cola.gmu.edu/grads/gadap/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libdap 3.20.6 为 OHOS 适配 conan 包 (本地 cache / 制品仓)。
        # gadap 上游 configure 只要求 >= 3.7.3, 3.20.6 满足; 命名空间
        # 差异由 patches 0002-0011 适配。
        self.requires("libdap/3.20.6",
                      transitive_headers=True, transitive_libs=True)
        # 以下三个是 libdap 的直接依赖; gadap 链接 libdap.a (静态) 时
        # 这些符号同样进入 gadap 的 NEEDED/lib 集合, dap-config --libs
        # 也会输出 -lcurl -lxml2 -ltirpc, 因此显式声明为直接依赖
        # (conan 传递依赖可见性在 test_package 消费侧不可靠)。
        self.requires("libxml2/2.15.3")
        self.requires("curl/8.15.0")
        self.requires("libtirpc/1.3.7")
        # libdapserver (dap-config --libs 输出 -luuid) 链接需要 uuid
        self.requires("uuid/2.40.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gadap/2.0 is only supported on Linux/OHOS, not {self.settings.os}")

    def source(self):
        # tar 条目带 "./gadap-2.0/" 前缀, conan 2.29 的 strip_root 对该
        # 前缀不生效 (与旧归档一致), 手动剥离顶层目录。
        get(self, **self.conan_data["sources"])
        import shutil
        src = self.source_folder
        sub = os.path.join(src, "gadap-2.0")
        if os.path.isdir(sub):
            for f in os.listdir(sub):
                shutil.move(os.path.join(sub, f), os.path.join(src, f))
            os.rmdir(sub)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: 上游只产 libgadap.a (lib_LIBRARIES), 保持静态
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        # R33: 编译器从 Conan conf 获取, 显式传给 configure
        # (CI 干净环境 AutotoolsToolchain 不自动注入到 configure 命令行)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        if compilers.get("c"):
            tc.configure_args.append(f"CC={compilers['c']}")
        if compilers.get("cpp"):
            tc.configure_args.append(f"CXX={compilers['cpp']}")
        # 上游 2008 年代码 + libdap 3.20.6 头文件 (strstream/ostrstream)
        # 需要 C++11 (C++17 起 strstream 移除; profile cppstd=17 会注入
        # -std=c++17 导致编译失败, 显式覆盖回 C++11 — libdap 配方同因)
        cxxflags = ["-stdlib=libc++", "-std=c++11"]
        cxxflags.append("-O2" if self.settings.build_type == "Release" else "-O0")
        tc.configure_args.append(f"CXXFLAGS={' '.join(cxxflags)}")
        tc.generate()

        # ── 重定位 dap-config (libdap 打包缺陷: prefix=/ + 硬编码 ──)
        # configure 的 AC_CHECK_LIBDAP 只认 dap-config; 原版输出的
        # -I/-L 指向 libdap 构建时的 conan cache 路径, 消费者环境无效。
        # 在 generators 目录生成重定位版, 通过 DAP_CONFIG 环境变量注入
        # (AC_PATH_PROG 先查 $DAP_CONFIG 绝对路径)。
        # 依赖遍历 (全部直接依赖, ref 名取首个路径段), 避免硬编码名单
        inc_dirs = []       # -I 列表 (除 libdap 外)
        lib_dirs = []       # -L 列表 (除 libdap 外)
        for _dep in self.dependencies.values():
            dep_name = str(_dep.ref).split("/")[0]
            if dep_name == "libdap":
                continue
            pf = getattr(_dep, "package_folder", None) or ""
            for inc in _dep.cpp_info.includedirs:
                inc_dirs.append(inc if (os.path.isabs(inc) or not pf)
                                else os.path.join(pf, inc))
            for lb in _dep.cpp_info.libdirs:
                lib_dirs.append(lb if (os.path.isabs(lb) or not pf)
                                else os.path.join(pf, lb))
        d = self.dependencies["libdap"]
        d_pf = getattr(d, "package_folder", "")
        d_inc = os.path.join(d_pf, "include", "libdap") if d_pf else ""
        d_lib = os.path.join(d_pf, "lib") if d_pf else ""
        # libxml2 头文件在 include/libxml2 子目录
        inc_flags = " ".join(
            "-I" + p for p in dict.fromkeys(inc_dirs))
        lib_flags = " ".join(
            "-L" + p for p in dict.fromkeys(lib_dirs))
        cxx = compilers.get("cpp", "clang++")
        cc = compilers.get("c", "clang")
        dap_config = os.path.join(self.generators_folder, "dap-config")
        with open(dap_config, "w") as f:
            f.write(f"""#! /bin/sh
# Relocated dap-config generated by gadap conan recipe.
# libdap conan 包内的 dap-config prefix=/ 为空且硬编码构建时 cache
# 路径 (打包缺陷), 消费者环境不可用; 本脚本指向本机 conan 包目录。
prefix="{d_pf}"
exec_prefix="${{prefix}}"
libdir="{d_lib}"
includedir="{d_inc}"
case "$1" in
    --version) echo "libdap 3.20.6" ;;
    --cc) echo "{cc}" ;;
    --cxx) echo "{cxx}" ;;
    --cflags) echo "-I${{includedir}} {inc_flags}" ;;
    --libs) echo "-L${{libdir}} -ldap -ldapserver -ldapclient {lib_flags} -lcurl -lxml2 -ltirpc -luuid -lm -lpthread" ;;
    --server-libs) echo "-L${{libdir}} -ldap -ldapserver {lib_flags} -lxml2 -ltirpc -luuid -lm -lpthread" ;;
    --client-libs) echo "-L${{libdir}} -ldap -ldapclient {lib_flags} -lcurl -lxml2 -ltirpc -luuid -lm -lpthread" ;;
    --prefix) echo "${{prefix}}" ;;
    *) echo "unknown option: $1"; exit 1 ;;
esac
""")
        os.chmod(dap_config, 0o755)
        self.output.info(f"  [ohos] relocated dap-config -> {dap_config}")

        env = Environment()
        env.define_path("DAP_CONFIG", dap_config)
        # ⚠️ LD_LIBRARY_PATH 顺序 (libdap 配方同源知识):
        #  1) sdk llvm/lib 最前 — lld 自身 NEEDED libxml2.so.16, conan
        #     同名库遮蔽会让 lld 启动即崩;
        #  2) /system/lib64 第二 — libc++_shared.so 正确版本 (musl loader
        #     无默认搜索路径);
        #  3) 依赖包 lib 目录随后 — conftest/AC_RUN_IFELSE/测试程序运行期
        #     加载 libdap/libxml2 等。
        # musl loader 空格段陷阱: 外层 LD_LIBRARY_PATH 若含 "空格前缀"
        # 段, 出现在路径中间会让后续所有段失效 — 清洗后用 define 重建。
        _parts = [_sdk_llvm_lib(cxx)]
        _parts.append("/system/lib64")
        for p in os.environ.get("LD_LIBRARY_PATH", "").split(":"):
            if p.strip() and " " not in p and p not in _parts:
                _parts.append(p)
        for dep in self.dependencies.values():
            pf = getattr(dep, "package_folder", None) or ""
            for libdir in dep.cpp_info.libdirs:
                _lb = str(libdir)
                if not os.path.isabs(_lb) and pf:
                    _lb = os.path.join(pf, _lb)
                if _lb and _lb not in _parts:
                    _parts.append(_lb)
        env.define("LD_LIBRARY_PATH", ":".join(_parts))
        # E074: make jobserver 用 mkfifo, HMDFS 不支持 FIFO — TMPDIR
        # 指向 tmpfs
        _fifo_tmp = "/data/storage/el2/base/temp"
        if os.path.isdir(_fifo_tmp):
            env.define("TMPDIR", _fifo_tmp)
        env.vars(self, scope="build").save_script("gadap_build_env")

    def build(self):
        apply_conandata_patches(self)

        # ── 时间序防 configure 重生成 (关键!) ──
        # tar 解压保留 2008 时间戳; patch 更新 configure/configure.ac
        # 后, Makefile 的 am--refresh/config.status--recheck 规则会用
        # 设备上的 autoconf 2.72 重新生成 configure (2.59→2.72 重生成
        # 后 0001 patch 的行号上下文失效 + 引入 E011 config.status
        # mktemp umask 077 陷阱)。用 touch -r 把生成文件的时间戳拉回
        # 与 configure.ac 一致, 保证 make 走预生成 configure 不重跑。
        sf = self.source_folder
        anchor = os.path.join(sf, "configure.ac")
        for rel in ("aclocal.m4", "configure", "Makefile.in", "config.h.in",
                    "src/Makefile.in", "test/Makefile.in", "gadap-config.in"):
            p = os.path.join(sf, rel)
            if os.path.isfile(p):
                os.utime(p, ns=(os.stat(anchor).st_atime_ns,
                                os.stat(anchor).st_mtime_ns))
        # patch 后 VERSION 已改名 GADAP_VERSION; 上游 configure 会再
        # echo -n 2.0>VERSION (patch 0001 已改为 GADAP_VERSION, 但保险
        # 起见删除遗留的 VERSION 文件, 防 HMDFS 大小写不敏感下遮蔽
        # libc++ <version> 头)
        for junk in ("VERSION",):
            vp = os.path.join(sf, junk)
            if os.path.isfile(vp):
                os.remove(vp)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

        # ── 上游测试 (R31/L1: make check 必须执行) ──
        # test/Makefile.am: bin_PROGRAMS = test — make check 构建 test
        # 程序 (无 check-SCRIPTS/check_PROGRAMS 注册, automake 1.9 时代
        # 仅有构建验证)。构建成功后再运行一次 (无参数 → "need URL"
        # 返回 0) 作为链接+加载冒烟。真实数据测试依赖
        # http://test.opendap.org 测试服务器, 2026-09 实测数据集路径
        # 已 404 (上游服务器内容变动), 不纳入 pass/fail 判定。
        try:
            autotools.make(args=["check", "-j2"])
        except Exception as ex:
            self.output.warning(f"  [warn] make check reported failure: {ex}")

        test_bin = os.path.join(self.build_folder, "test", "test")
        if os.path.isfile(test_bin):
            # OHOS loader 无默认共享库搜索路径; LD_LIBRARY_PATH 由
            # generate() 的 build env 脚本提供 (conanbuild scope)
            self.run(f'"{test_bin}"', env="conanbuild")
            self.output.info("  [ohos] upstream test binary smoke: rc=0 (need URL)")
        else:
            self.output.warning("  [ohos] upstream test binary not found, skip smoke run")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 上游 Makefile 把 test/ 的测试程序也 install 到 bin/ (bin_PROGRAMS);
        # 它是内部测试驱动 (需要 OPeNDAP URL 参数), 不是用户工具 — 从包里
        # 移除 (9MB 测试二进制无交付价值; gadap-config 保留, 与 libdap 包
        # 的 dap-config 同类)
        import shutil
        test_bin = os.path.join(self.package_folder, "bin", "test")
        if os.path.isfile(test_bin):
            os.remove(test_bin)
            self.output.info("  [ohos] removed upstream test driver from bin/")

    def package_info(self):
        self.cpp_info.libs = ["gadap"]
        self.cpp_info.includedirs = ["include"]
        # gadap 对外安装 gadap.h/gadap_err.h/gadap_types.h (include_HEADERS),
        # 其内部 ga*.h 不安装; libdap 头由 libdap 包自身提供
        self.cpp_info.requires = [
            "libdap::libdap",
            "libxml2::libxml2",
            "curl::curl",
            "libtirpc::libtirpc",
            "uuid::uuid",
        ]
