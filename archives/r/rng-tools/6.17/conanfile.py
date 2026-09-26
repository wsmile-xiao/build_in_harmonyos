#!/usr/bin/env python3
"""Conan recipe — rng-tools 6.17 (rngd daemon + rngtest FIPS-140-2 tool).

rng-tools 是 Linux 硬件随机数工具集：rngd 守护进程（多熵源：hwrng/rdrand/
jitter/NIST beacon/qrypt/pkcs11/rtlsdr/RNDR）和 rngtest（FIPS-140-2 随机性
检测工具）。产物为两个可执行文件，无库（R38: application → commands.json）。

构建系统: autotools。上游 GitHub tag 归档不含预生成 configure，需 autoreconf
自举（CI worker 无 automake/libtoolize → tool_requires automake/libtool）。

OHOS 适配要点:
  - musl 对 pthread_setaffinity_np / pthread_attr_setaffinity_np 声明层与符号层
    双缺，而 configure.ac:117-121 把"双探测皆失败"写成 AC_MSG_ERROR ⇒ 包在
    configure 期就硬中止（一行代码都没编译）。解法是非侵入两层垫片，缺一即失败：
    ①build() 生成 rngtools_np_affinity.h 经 CPPFLAGS 前置 -include 注入，让
      AC_CHECK_DECL 的编译探测转绿；②生成 rngtools_np_affinity.c 转发
      sched_setaffinity(2)，llvm-ar 打成 librngnpcompat.a，经 LDFLAGS=-L +
      LIBS=-lrngnpcompat 进最终链接。垫片故意只声明 plain 变体、不声明 attr
      变体 ⇒ configure 落 else 分支只 AC_DEFINE(HAVE_PTHREAD_SETAFFINITY)。
    上游源码零改动、零补丁（细节见 notes.md 与 knowledge/drafts 同名 DRAFT）
  - musl libc 无 argp，而 rngtest.c 直接使用 argp：configure.ac 在探测到
    libc 缺 argp 时走外部 libargp（AC_CHECK_LIB[argp]），--without-libargp
    会触发 AC_MSG_FAILURE（"libargp disabled and libc does not have argp"）
    ⇒ 必须 requires argp-standalone 并注入 -I/-L（E169 同族机制）
  - openssl/libcap 为 configure.ac 无条件 PKG_CHECK_MODULES ⇒ PkgConfigDeps
    注入 .pc；jitterentropy 为 AC_SEARCH_LIBS ⇒ LDFLAGS 注入（自动开关）
  - 可选熵源 nistbeacon(libxml2+libcurl+jansson)/qrypt(libcurl)/
    pkcs11(libp11)/rtlsdr(librtlsdr) 依赖重且不可用 ⇒ 显式 --without-*
  - aarch64 + sys/auxv.h 时 configure 自动启用 RNDR 源（rngd_rndr.c），
    musl 提供 getauxval/sys/auxv.h，无需干预
  - E011: autoreconf 生成的脚本含 umask 077，HMDFS 权限受限 ⇒ 改 022
  - 设备级 SHELL 路由（KB §12.49）：profile [buildenv] 的 SHELL/CONFIG_SHELL 指向
    harmonybrew bash 5.3，该 bash 在 HMDFS 上 getcwd 必挂，configure 经 $CONFIG_SHELL
    重 exec 自身即报 "working directory cannot be determined" ⇒ 配方内显式用
    /bin/sh 执行 configure 并把两个变量钉到 /bin/sh（不改框架 profile 文件）
  - 上游测试: tests/ 下 3 个 shell 脚本（TESTS）通过 make check 真实执行
"""
import os
import shlex

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class RngToolsConan(ConanFile):
    name = "rng-tools"
    version = "6.17"
    description = "rng-tools: random number generator daemon (rngd) and FIPS-140-2 RNG test tool (rngtest)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/nhorman/rng-tools"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac 无条件 PKG_CHECK_MODULES(openssl/libcap)
        self.requires("openssl/3.5.8.1")
        self.requires("libcap/2.73")
        # musl 无 argp：configure 自动探测并外链 -largp（E169）
        self.requires("argp-standalone/1.5.0")
        # jitter 熵源（AC_SEARCH_LIBS 探测，找到即启用，找不到自动关闭）
        self.requires("jitterentropy-library/3.6.3")

    def build_requirements(self):
        # tag 归档无预生成 configure，需自举；CI worker 无 host automake/libtool
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 为全部依赖按 cpp_info 生成 .pc（libcap 包不自带 .pc，而 configure
        # 对 openssl/libcap 用 PKG_CHECK_MODULES ⇒ 必须有 libcap.pc 可查）
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # E007: config.guess 不识别 OHOS 且 HMDFS 禁执行测试程序
        # （dummy.c Permission denied → "cannot guess build type"）⇒ 显式三元组
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        # 关闭依赖沉重的可选熵源（保留 jitter 与 RNDR，均零额外负担）
        tc.configure_args += [
            "--without-nistbeacon",  # 需 libxml2 + libcurl + jansson
            "--without-qrypt",       # 需 libcurl
            "--without-pkcs11",      # 需 libp11
            "--without-rtlsdr",      # 需 librtlsdr（USB 硬件）
        ]
        # 注意: 不能加 --without-libargp —— musl 缺 argp 时 configure 会
        # AC_MSG_FAILURE；正确路径是外链 argp-standalone（见 requirements）

        # 依赖路径注入（yara 同款模式，generate 与 build 同进程，os.environ
        # 直接生效）：openssl/libcap 需 PKG_CONFIG_PATH（configure 用
        # PKG_CHECK_MODULES），argp-standalone/jitterentropy 需 -I/-L
        # （configure 用 AC_LINK_IFELSE/AC_CHECK_LIB/AC_SEARCH_LIBS）
        cppflags, ldflags, pkg_dirs = [], [], []
        for _, dep in self.dependencies.items():
            for inc in dep.cpp_info.includedirs:
                cppflags.append("-I{}".format(inc))
            for libdir in dep.cpp_info.libdirs:
                ldflags.append("-L{}".format(libdir))
                pc = os.path.join(libdir, "pkgconfig")
                if os.path.isdir(pc):
                    pkg_dirs.append(pc)

        # musl（OHOS）对 pthread_setaffinity_np / pthread_attr_setaffinity_np 是
        # **声明层与符号层双缺**（glibc 专有 _np 扩展），把 _GNU_SOURCE 打开并不会
        # 让声明出现——设备实测：上游 configure 在"全裸"与"仅 -D_GNU_SOURCE"两种注入下
        # 产出的 configure 日志逐字节相同（sha256 一致），都在同一处
        # AC_MSG_ERROR([Neither pthread_setaffinity_np nor pthread_attr_setaffinity_np found])
        # 硬中止 ⇒ 真正的修复是 build() 里的两层垫片（-include 声明 + -lrngnpcompat 符号），
        # 不是这个宏。此处注入 -D_GNU_SOURCE 只为其它 GNU 扩展兜底（未验证其必要性，
        # 故不删除）；代价是与上游 10 个 TU 自带的 #define _GNU_SOURCE 冲突，产生
        # -Wmacro-redefined 告警（告警，非错误）。
        if cppflags:
            os.environ["CPPFLAGS"] = "-D_GNU_SOURCE " + " ".join(cppflags) + " " + os.environ.get("CPPFLAGS", "")
        else:
            os.environ["CPPFLAGS"] = "-D_GNU_SOURCE " + os.environ.get("CPPFLAGS", "")
        if ldflags:
            os.environ["LDFLAGS"] = " ".join(ldflags) + " " + os.environ.get("LDFLAGS", "")
        if pkg_dirs:
            os.environ["PKG_CONFIG_PATH"] = ":".join(pkg_dirs) + ":" + os.environ.get("PKG_CONFIG_PATH", "")
        # PkgConfigDeps 生成的 .pc（含 libcap.pc）所在目录放最前
        os.environ["PKG_CONFIG_PATH"] = (
            self.generators_folder + ":" + os.environ.get("PKG_CONFIG_PATH", ""))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # OHOS musl 既不声明也不导出 pthread_setaffinity_np（glibc GNU 扩展），
        # configure 的 AC_CHECK_DECL 双查均失败 → AC_MSG_ERROR 硬错
        # （KB E094/E147/E211 家族；此处用非侵入变体：声明垫片 + sched_setaffinity
        # 转发实现库，conanfile 级注入，不改上游源码，attr 变体不声明使
        # configure 落到 plain 变体 = HAVE_PTHREAD_SETAFFINITY）
        compat_dir = os.path.join(self.build_folder, "np-affinity-compat")
        os.makedirs(compat_dir, exist_ok=True)
        shim_h = os.path.join(compat_dir, "rngtools_np_affinity.h")
        with open(shim_h, "w") as f:
            f.write(
                "#ifndef RNGTOOLS_NP_AFFINITY_H\n"
                "#define RNGTOOLS_NP_AFFINITY_H\n"
                "#define _GNU_SOURCE 1\n"
                "#include <pthread.h>\n"
                "#include <sched.h>\n"
                "/* OHOS musl pthread.h 未声明 pthread_setaffinity_np（glibc GNU\n"
                " * 扩展）且 libc 未导出该符号；此声明供 configure 的\n"
                " * AC_CHECK_DECL 与上游 #include 路径使用，实现转发\n"
                " * sched_setaffinity(2)（见 librngnpcompat.a）。 */\n"
                "int pthread_setaffinity_np(pthread_t, size_t, const cpu_set_t *);\n"
                "#endif\n")
        compat_c = os.path.join(compat_dir, "rngtools_np_affinity.c")
        with open(compat_c, "w") as f:
            f.write(
                "#define _GNU_SOURCE 1\n"
                '#include "rngtools_np_affinity.h"\n'
                "#include <sched.h>\n"
                "int pthread_setaffinity_np(pthread_t thread, size_t cpusetsize,\n"
                "                           const cpu_set_t *mask)\n"
                "{\n"
                "    /* 丢弃 thread 形参、只给调用线程设亲和：rngd_jitter.c:290 传的是\n"
                "     * pthread_self()（本就是自身），但 :86 在 rngd_notime_start 里传的\n"
                "     * 是 notime_thread_id（另一个线程）——那一处会退化为给调用线程设\n"
                "     * 亲和。掩码是 CPU_SET 全核，故只影响性能不影响正确性（见 PR 已知限制）*/\n"
                "    (void)thread;\n"
                "    return sched_setaffinity(0, cpusetsize, mask);\n"
                "}\n")
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict) or {}
        cc = compilers.get("c", "clang")
        self.run('{} -c "{}" -o "{}"'.format(
            cc, compat_c, os.path.join(compat_dir, "rngtools_np_affinity.o")),
            cwd=compat_dir, env="conanbuild")
        self.run('llvm-ar rcs librngnpcompat.a rngtools_np_affinity.o',
                 cwd=compat_dir, env="conanbuild")

        # 注意：路径不加引号——configure 会自行加引号导致 ""path"" 空文件名
        os.environ["CPPFLAGS"] = (
            "-include {} ".format(shim_h) + os.environ.get("CPPFLAGS", ""))
        os.environ["LDFLAGS"] = (
            "-L{} ".format(compat_dir) + os.environ.get("LDFLAGS", ""))
        # LIBS 在链接序末尾（configure 追加的 -largp 之前亦可被 conftest 解析），
        # 保证 rngd/rngtest 最终链接解析到垫片符号
        os.environ["LIBS"] = "-lrngnpcompat " + os.environ.get("LIBS", "")

        autotools = Autotools(self)
        # tag 归档只有 configure.ac，先自举生成 configure
        autotools.autoreconf()

        # E490: HMDFS 适配路径可能丢失 helper 脚本可执行位 → 恢复
        for helper in ["configure", "config.guess", "config.sub", "install-sh",
                       "missing", "compile", "depcomp", "test-driver"]:
            fpath = os.path.join(self.source_folder, helper)
            if os.path.isfile(fpath):
                os.chmod(fpath, 0o755)

        # E011: 自举产物含 umask 077，HMDFS 权限受限目录会安装失败 → 改 022
        for fname in ["configure", "Makefile.in", "tests/Makefile.in"]:
            fpath = os.path.join(self.source_folder, fname)
            if os.path.isfile(fpath):
                with open(fpath, "r") as f:
                    content = f.read()
                if "umask 077" in content:
                    replace_in_file(self, fpath, "umask 077", "umask 022")

        # 防止 make 试图重新生成 autotools 文件（时间戳抖动触发重生成）
        for tool in ["ACLOCAL", "AUTOMAKE", "AUTOCONF", "AUTOHEADER", "AUTOM4TE"]:
            os.environ[tool] = ":"

        # OHOS 设备级坑（KB §12.49/§12.38①，E386 家族）：profile
        # ci/conan/profiles/ohos-aarch64 的 [buildenv] 把 SHELL/CONFIG_SHELL 指向
        # /data/service/hnp/bin/bash（harmonybrew bash 5.3），而该 bash 在 HMDFS 上
        # getcwd 必挂——设备实测 `cd <构建目录> && /data/service/hnp/bin/bash -c pwd`
        # rc=1（errno 乱值 Not supported / Not a socket / Bad address），同目录
        # /bin/sh（mksh）rc=0 且 python3 os.getcwd() 正常。autoconf 生成的 configure
        # 会经 $CONFIG_SHELL 重 exec 自身 ⇒ 报
        # "configure: error: working directory cannot be determined"（一行代码都没编，
        # 与配方、内存、负载无关）。profile 是框架文件（改动须单独 PR），故在配方内
        # 显式用 /bin/sh 执行 configure，并用命令行赋值把 SHELL/CONFIG_SHELL 钉到
        # /bin/sh（命令行赋值优先于 conanbuild.sh 里已 export 的值），使 config.status
        # 记录的 @SHELL@ 同为 /bin/sh，make/make check 不再拉起 hnp bash。
        # 同款绕法先例: archives/a/abx/0.1/conanfile.py
        configure_script = os.path.join(self.source_folder, "configure")
        self.run("CONFIG_SHELL=/bin/sh SHELL=/bin/sh "
                 + shlex.join(["/bin/sh", configure_script])
                 + " " + autotools._configure_args,
                 cwd=self.build_folder)
        autotools.make(args=["-j2"])

        # 上游测试（R51/W0b 五维账本）：tests/ 下 3 个 shell 用例
        #   rngtesturandom.sh  /dev/urandom 100 块过 FIPS 检测（可跳过:77）
        #   rngtestzero.sh     /dev/zero 必须被 FIPS 检测拒绝（反向断言）
        #   rngtestjitter.sh   jitter 熵源 30 秒产出过 rngtest（后台 killall 兜底）
        # 顶层 make check 递归 SUBDIRS(contrib tests) 真实执行；
        # 失败时 make check 非零退出，日志尾部随异常抛出（不吞错误）
        # RNGD_JITTER_TIMEOUT：上游 rngd -O jitter:timeout 的环境旋钮。默认 5s
        # 内 jitter 线程需产出首个 AES key，但构建机多窗口并发高负载（PSI>60%）
        # 时 jitter 线程调度延迟会超 5s ⇒ 放宽到 120s（上游脚本原生支持）
        os.environ["RNGD_JITTER_TIMEOUT"] = "120"
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 纯可执行文件包：rngd、rngtest 安装到 bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
