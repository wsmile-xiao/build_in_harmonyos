#!/usr/bin/env python3
"""Conan recipe for syslog-ng 4.8.1 — 增强型日志守护进程（Autotools，application）。

构建体系：tarball 自带预生成 configure/configure.ac（无需 autogen）；
捆绑 lib/ivykis（AC_CONFIG_SUBDIRS，默认 --with-ivykis=internal）在其内部
再跑一次 configure，故 config.guess/config.sub 与 E011 umask 补丁各需两份。

平台适配要点（均经源码核实）：
- config.guess/config.sub 不识别 uname -s=HarmonyOS 与 linux-ohos 组合：
  顶层、lib/ivykis 与 lib/ivykis/test.mt 三份独立副本全修 → 0001–0004、
  0007/0008；configure 的 "umask 077 && mktemp -d" 临时目录在 HMDFS 上
  Permission denied（mktemp -d 固定 0700）→ 0005/0006/0009
  （libestr/libfastjson/rsyslog 同款修法）。OHOS libc 无 pthread_cancel/
  pthread_testcancel 符号（链接期 undefined）→ 0010 在 test.mt 子工程
  增加 AC_CHECK_FUNCS(pthread_cancel) 能力探测，取消语义用例以
  HAVE_PTHREAD_CANCEL 守卫（test.mt 为该符号唯一实际链接使用点，其余
  用例照跑）；lib/thread-utils.h 的 thread_cancel() 内联助手全树零调用
  者，但其函数体含 pthread_cancel——C 编译仅警告、C++ TU（examples
  模块）升级为硬错误 → 0012 将 pthread_cancel 加入既有 AC_CHECK_FUNCS
  列表，SYSLOG_NG_HAVE_PTHREAD_CANCEL 未定义时置 no-op；afuser
  （usertty 目的地，modules/afuser）同理：OHOS 的 utmpx.h 为仅含
  struct utmpx 的桩头，getutxent/endutxent 既不声明也不提供，且平台无
  utmp 数据库 → 0011 复用既有 getutxent 探测（configure.ac 的
  AC_CHECK_FUNCS 列表本就含 getutxent），查询实现以
  SYSLOG_NG_HAVE_GETUTXENT 守卫，未检测到时桩空查询（usertty 在 OHOS
  上退化为 "无用户登录"，如实记录于 notes）。
- HMDFS（E046）chmod +x 不生效 → configure 经 sh(1) 调用（autofs 5.1.9
  同款实证修法）；make 与 make install 同为 in-source 就地执行（必须
  cd source 根：Autotools.make/install 默认 cwd=build_folder，即
  basic_layout 的 build-release 子目录 → "No targets specified and no
  makefile found"）；install 显式 DESTDIR=$package_folder
  （--prefix="/" 的配套约定，Autotools.install() 同款默认；缺省时按
  prefix=/ 直写系统根 "//lib"，OHOS 根分区 EROFS 必炸）；E490 权限位
  恢复循环降级为一般平台 best-effort。
- 致命 PKG_CHECK_MODULES 共 5 组（GLIB/PCRE2/OPENSSL/JSON/CRITERION）：
  全部经 pkg.m4 的 <VAR>_CFLAGS/<VAR>_LIBS 环境变量短路（_PKG_CONFIG 宏
  先看变量、变量非空即不再调 pkg-config）——制品仓 .pc 被 relocatable
  打包改写成 DESTDIR 前缀 "/"，直接用会产出 -I//include 之类废路径
  （rsyslog 配方对 libestr/libfastjson 记录过同款问题），故 generate()
  直接把真实包路径写进这 5 组变量。仅 JSON 稍特殊：configure 先
  PKG_CHECK_EXISTS(json-c) 选模块名（该宏不吃变量短路，会真调 pkg-config），
  但 --exists 只查 .pc 可解析与 Version、不校验前缀，PKG_CONFIG_PATH
  （依赖自带 lib/pkgconfig + PkgConfigDeps 生成目录兜底）保证可发现。
- 其余模块级 PKG_CHECK_MODULES（maxminddb/mongodb/libesmtp/hiredis/
  rabbitmq/rdkafka/riemann/systemd/python/java/libcap/libbpf...）均为
  可选探测：找不到即自动关模块，正是默认集。
- 链接模式默认 dynamic（configure.ac 701-704）：模块是 dlopen 的 .so
  （lib/syslog-ng/*.so），静态链接才要求的 static-glib/static-openssl
  检查不适用。
- criterion >= 2.2.1 被探测到即自动 enable_tests=yes（无 --enable-tests
  开关；找不到时静默关测试）→ criterion 走 test_requires + 变量覆盖，
  configure 摘要 "Unit tests ... yes" 是门禁；make check（libtest +
  modules/*/tests）不在 build() 内跑（仓库惯例 upstream_test_in_build=
  false，保持 create 确定性），由设备在缓存构建树内全量实跑。
- 模块目录运行期定位：编译期默认 ${exec_prefix}/lib/syslog-ng 即
  "/lib/syslog-ng"（conan 惯例 DESTDIR 前缀 "/"）；lib/reloc.c
  lookup_sysprefix()（166 行）认 SYSLOGNG_PREFIX 环境变量做前缀重定位
  → package_info 导出 SYSLOGNG_PREFIX=package_folder（RSYSLOG_MODDIR 同款）。
- $ORIGIN rpath：sbin/syslog-ng 与 sbin/syslog-ng-ctl 找 ../lib 的
  libsyslog-ng.so，lib/syslog-ng 模块找 .. 的框架库；依赖库目录用
  绝对 rpath（zile 模式，兼顾链接期 needed-by 传递库查找）。
- glib 必须 shared 单实例：40+ 个 dlopen 模块与框架库共享同一份
  gobject 类型系统；制品仓 glib/2.84.0.1 即 shared 二进制修订
  （全仓 140+ 配方在用）。
- json 头以 <json.h> 风格包含（modules/json/json-parser.c:33）→
  JSON_CFLAGS 额外加 <pkg>/include/json-c 子目录（存在时）。
- 测试二进制写临时文件，OHOS 系统 /tmp 只读 → TMPDIR 钉在 build 目录内。
"""
import os
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class SyslogNgConan(ConanFile):
    name = "syslog-ng"
    version = "4.8.1"
    description = "syslog-ng is an enhanced log daemon with flexible filtering and parsing capabilities"
    license = "GPL-2.0-or-later"
    homepage = "https://www.syslog-ng.com/"
    url = "https://github.com/syslog-ng/syslog-ng"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 裸格式引用（ohpcd 制品仓无 user/channel）；全部 shared 二进制
        # （dlopen 模块与框架库共链同一份实现，类型系统/全局态单实例）。
        self.requires("glib/2.84.0.1")
        self.requires("pcre2/10.45")
        self.requires("openssl/3.5.6")
        self.requires("json-c/0.18")
        self.requires("libcurl/8.5.0")
        # libhttp 的 compression.c 直接调用 zlib（deflateInit2_/deflateEnd，
        # gzip content-encoding），必须显式直连声明：libcurl 虽传递依赖
        # zlib/1.3.1.1，但 conan 的 tools.graph:skip_binaries 优化在 libcurl
        # 二进制已就绪（缓存/仓库）时会把这条传递边的二进制标记 skip，而
        # self.dependencies.host 的过滤器含 "skip": False → 节点被整体滤除，
        # _find_dep("zlib") 会找不到（run#10 实证：generate() 直接报
        # dependency 'zlib' not found）。显式直连后 zlib 二进制必然解析
        # （含 CI 干净缓存场景）。制品仓 zlib 只发布静态 libz.a：链入
        # libhttp.so 后 deflate 符号自包含（同 libcurl.so 静态内嵌形态），
        # 运行时无需外部 libz（OHOS 系统 /system/lib64 无 libz）。
        self.requires("zlib/1.3.1.1")

    def build_requirements(self):
        # 上游单元测试框架：configure 探测到 criterion>=2.2.1 即自动开启
        # 单元测试（静默关闭无提示），故走 test_requires 并做变量覆盖。
        self.test_requires("criterion/2.4.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _iter_deps(self):
        """host/build/test 三个上下文的全部依赖（含传递闭包）。"""
        for group_name in ("host", "build", "test"):
            group = getattr(self.dependencies, group_name, None)
            if not group:
                continue
            for _, dep in group.items():
                yield dep

    def _all_dependencies(self):
        seen, deps = set(), []
        for dep in self._iter_deps():
            if dep.ref.name not in seen:
                seen.add(dep.ref.name)
                deps.append(dep)
        return deps

    def _find_dep(self, name):
        for dep in self._iter_deps():
            if dep.ref.name == name:
                return dep
        raise ConanException(f"dependency '{name}' not found in host/build/test context")

    @staticmethod
    def _dep_dirs(dep):
        """依赖的 include/lib 目录（模块化 cpp_info 合并），绝对化。

        本代制品仓常见把真实路径放在 components（glib: include/glib-2.0 与
        lib/glib-2.0/include），顶层 includedirs 只有 "include"，两层都收。
        """
        root = dep.package_folder
        incs, libs = [], []

        def _add(lst, value):
            if not value:
                return
            path = value if (os.path.isabs(value) or not root) else os.path.join(root, value)
            if path not in lst:
                lst.append(path)

        infos = [dep.cpp_info]
        try:
            infos.append(dep.cpp_info.aggregated_components())
        except Exception:
            pass
        for info in infos:
            for inc in info.includedirs:
                _add(incs, inc)
            for libdir in info.libdirs:
                _add(libs, libdir)
        return incs, libs

    def generate(self):
        # 先生成依赖 .pc（含 json-c.pc——configure 的 PKG_CHECK_EXISTS
        # 需要真调 pkg-config 选 json 模块名），再统一注入 PKG_CONFIG_PATH。
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        env = tc.environment()
        # 遍历全部依赖（含传递闭包）：头/库路径 + 绝对 rpath 注入链接行；
        # .pc/bin/lib 路径注入环境。LD_LIBRARY_PATH 同时是链接期
        # "shared lib needed by libX" 传递库的查找路径（critical）。
        for dep in self._all_dependencies():
            if not dep.package_folder:
                continue
            incs, libs = self._dep_dirs(dep)
            for inc in incs:
                tc.extra_cflags.append(f"-I{inc}")
            for libdir in libs:
                tc.extra_ldflags.append(f"-L{libdir}")
                tc.extra_ldflags.append(f"-Wl,-rpath,{libdir}")
            for pkg_dir in (os.path.join(dep.package_folder, "lib", "pkgconfig"),
                            os.path.join(dep.package_folder, "share", "pkgconfig")):
                if os.path.isdir(pkg_dir):
                    env.append_path("PKG_CONFIG_PATH", pkg_dir)
            bin_dir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bin_dir):
                env.append_path("PATH", bin_dir)
            for libdir in libs:
                env.append_path("LD_LIBRARY_PATH", libdir)
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)

        # 5 组致命 pkg 检查的变量短路（pkg.m4 _PKG_CONFIG：变量非空即不再
        # 调 pkg-config）——绕开 relocatable .pc 的坏前缀。
        def _pc_override(var, dep_name, libs, extra_incs=()):
            dep = self._find_dep(dep_name)
            incs, libdirs = self._dep_dirs(dep)
            env.define(f"{var}_CFLAGS",
                       " ".join(f"-I{i}" for i in list(incs) + list(extra_incs)))
            env.define(f"{var}_LIBS",
                       " ".join([f"-L{l}" for l in libdirs] +
                                [f"-l{lib}" for lib in libs]))

        # 变量名与模块清单对 configure.ac 逐行核实：
        # GLIB（1036 行：glib-2.0 $GLIB_ADDONS=gmodule-2.0 gthread-2.0）
        _pc_override("GLIB", "glib", ["glib-2.0", "gmodule-2.0", "gthread-2.0"])
        # PCRE2（1145 行：libpcre2-8）
        _pc_override("PCRE2", "pcre2", ["pcre2-8"])
        # OPENSSL（1159 行：openssl）
        _pc_override("OPENSSL", "openssl", ["ssl", "crypto"])
        # JSON（1377 行：json-c；头在 include/json-c/ 子目录，存在即补）
        _json_extra = [os.path.join(inc, "json-c")
                       for inc in self._dep_dirs(self._find_dep("json-c"))[0]
                       if os.path.isdir(os.path.join(inc, "json-c"))]
        _pc_override("JSON", "json-c", ["json-c"], _json_extra)
        # CRITERION（1302 行：criterion >= 2.2.1，命中即 enable_tests）
        _pc_override("CRITERION", "criterion", ["criterion"])

        # 关掉需要宿主语言工具链、设备/CI 不可用的运行时后端（保持默认
        # 模块集；auto 探测在这些环境也大概率落到 off，显式更稳）。
        for flag in ("--disable-python", "--disable-python-modules",
                     "--disable-java", "--disable-java-modules",
                     "--disable-systemd"):
            tc.configure_args.append(flag)
        # http 模块：--with-libcurl=<DIR> 直接吃包目录（探 DIR/include/curl）。
        _libcurl = self._find_dep("libcurl").package_folder
        if _libcurl:
            tc.configure_args.append(f"--with-libcurl={_libcurl}")

        # http 模块 compression.c 直接调用 zlib（deflateInit2_/deflateEnd 等，
        # gzip content-encoding）。上游只在非 dynamic 链接模式才把 -lz 塞进
        # 全局 LIBS（configure.ac:1164 条件块）；dynamic 模式全靠 glibc 懒
        # 绑定在进程全局域碰巧解析——musl 在 dlopen 时全量重定位，直接报
        # "Error relocating ... libhttp.so: deflateInit2_: symbol not found"
        # （实测 run#9 test_package 断言 9 失败）。ZLIB_LIBS 是 configure.ac
        # :2339 AC_SUBST 的正规变量（modules/afsocket 的 LIBADD 本就消费它，
        # 补丁 0013 让 http 模块也消费）；dynamic 模式下 configure 不覆盖
        # 外部注入值。
        _zlib = self._find_dep("zlib")
        _zlib_libdirs = self._dep_dirs(_zlib)[1]
        env.define("ZLIB_LIBS",
                   " ".join([f"-L{l}" for l in _zlib_libdirs] + ["-lz"]))

        # 自有产物的 $ORIGIN rpath（'$$' 在 Makefile 里坍缩为 '$'）：
        #   sbin/syslog-ng、sbin/syslog-ng-ctl → ../lib（libsyslog-ng.so）
        #   lib/syslog-ng/*.so                 → ..  （libsyslog-ng.so）
        tc.extra_ldflags.append("-Wl,-rpath,'$$ORIGIN/../lib'")
        tc.extra_ldflags.append("-Wl,-rpath,'$$ORIGIN/..'")

        # 测试/configure 需要可写 TMPDIR（OHOS /tmp 只读）。
        _tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(_tmp, exist_ok=True)
        env.define("TMPDIR", _tmp)

        # MKDIR_P：autoconf 2.72 的 "race-free mkdir -p" 检测靠
        # `mkdir --version` 字符串嗅探（只认 coreutils/BusyBox/fileutils
        # 签名），设备 OHOS mkdir 均不匹配 → 退化 "$ac_install_sh -d"
        # 即 ./install-sh -c -d；随后 config.status 的 depfiles 引导
        # （sed ... | make -f - am--depfiles，规则 @$(MKDIR_P) $(@D)）
        # 直接 execve HMDFS 上的 install-sh → E046 Error 126，configure
        # 尾部报 "Something went wrong bootstrapping makefile fragments"。
        # 预设 MKDIR_P 使 configure 跳过整个检测（configure 原文：
        # `if test -z "$MKDIR_P"`）并原样写入 Makefile；设备 mkdir -p
        # 实测可用（E046 下这是唯一可 execve 的形式）。
        env.define("MKDIR_P", "mkdir -p")

        # E046：HMDFS 上 chmod +x 不生效（execve 直接 EACCES/126），configure
        # 必须经 sh(1) 调用。把工具链生成的完整 configure 参数逐行落盘传给
        # build()（Autotools.configure() 内部是直接 execve，用不了）；
        # 逐行 + shlex.quote 传递，避免 ${prefix} 被 sh 展开成空值。
        self._cfg_args_file = os.path.join(self.generators_folder,
                                           "sng-configure-args.txt")
        with open(self._cfg_args_file, "w") as _f:
            _f.write("\n".join(tc.configure_args))

        tc.generate(env=env)

    def build(self):
        # HMDFS 下 umask 可能造出 640 文件使后续步骤读不了（rsyslog 同款）。
        if self.settings.os in ("Linux", "OHOS"):
            os.umask(0o022)
        apply_conandata_patches(self)
        # 非递归 automake（subdir-objects）：全树唯一生效顶层 Makefile.in，
        # 其再生规则把全部 202 个 Makefile.am 列为依赖——任一 Makefile.am
        # 比它新（同秒毫秒差即触发，实测 4ms）就调 missing→automake-1.16；
        # 设备无 automake（missing 退 127）→ 构建首步即死。0013 触及
        # modules/http/Makefile.am，纯净重建（官方 conan-verify）必踩；
        # 曾幸存的开发构建树仅因两次 patch 恰落同一纳秒。
        # 对策（2026-10-12 扩展）：全树再生文件按依赖序两趟归一（只动时间
        # 戳、不动内容）——先 aclocal.m4，再以它为前置的 configure/config.h.in/
        # Makefile.in（同刻会让后三者判旧，故 +2s）。0010/0012 触及
        # configure.ac/config.h.in 后，aclocal.m4（←configure.ac/acinclude.m4/
        # m4/*.m4）同样判旧、经 missing→aclocal-1.16（设备无 automake，
        # 真机 run6 实证顶层 Makefile:13732 Error 127），configure（←autoconf）
        # 与 config.h.in（←autoheader）是下两级连锁；test.mt 子工程同构。
        _mt = time.time()
        _regen = {"configure", "config.h.in", "Makefile.in"}
        for _dp, _dn, _fns in os.walk(self.source_folder):
            for _fn in _fns:
                if _fn == "aclocal.m4":
                    os.utime(os.path.join(_dp, _fn), (_mt, _mt))
                elif _fn in _regen:
                    os.utime(os.path.join(_dp, _fn), (_mt + 2, _mt + 2))
        # E490（best-effort）：HMDFS 上 chmod 对执行位实际不生效（E046，
        # other 位被吞、execve 不看属主位），根治手段是 sh 调用（见下方
        # configure）。此循环保留为一般平台兜底；缓存 create 流程中
        # source_folder 即源码树根（补丁落该处），configure/make 均在
        # source 根以 in-source 方式执行（见下方）。
        _aux_scripts = ("configure", "config.guess", "config.sub", "install-sh",
                        "missing", "compile", "depcomp", "ltmain.sh",
                        "test-driver",
                        "lib/ivykis/configure", "lib/ivykis/config.guess",
                        "lib/ivykis/config.sub", "lib/ivykis/install-sh",
                        "lib/ivykis/missing", "lib/ivykis/compile",
                        "lib/ivykis/depcomp", "lib/ivykis/ltmain.sh")
        for _root in (self.build_folder, self.source_folder):
            for _aux in _aux_scripts:
                _p = os.path.join(_root, _aux)
                if os.path.exists(_p):
                    os.chmod(_p, os.stat(_p).st_mode | 0o755)
        # CI 从 ohpcd 下载的依赖包自带 .la 文件中被 relocatable 打包改坏的
        # 绝对路径会让 libtool 报 "//lib/xxx.la is not a valid libtool
        # archive"（zile/libgee 同款清理）。
        for dep in self._all_dependencies():
            if not dep.package_folder:
                continue
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                for _la in os.listdir(lib_dir):
                    if _la.endswith(".la"):
                        os.remove(os.path.join(lib_dir, _la))
                        self.output.info(f"removed broken libtool archive: {dep.ref}/{_la}")
        # E046：HMDFS 不认 chmod +x（chmod 的 other 位被吞、execve EACCES，
        # 实测直接跑 configure → 126 Permission denied）。basic_layout 的
        # build_folder 是 source 下的 build-release 子目录，configure 在
        # source 根（autofs 5.1.9 同款实证修法：cd 到 source 根、经 sh(1)
        # 调用，in-source 构建）。参数取 generate() 落盘的 tc.configure_args
        # 全集（与 Autotools.configure() 直接调用时一致，只是绕开 execve）；
        # SHELL=/bin/sh 供 configure 内 config.status 以 $SHELL 执行
        # lib/ivykis 子 configure（autoconf 对子 configure 自带该回退）。
        import shlex
        with open(self._cfg_args_file, "r") as _f:
            _cfg_args = [ln for ln in _f.read().splitlines() if ln]
        self.run('cd "{}" && SHELL=/bin/sh /bin/sh configure {}'.format(
            self.source_folder,
            " ".join(shlex.quote(a) for a in _cfg_args)),
            env="conanbuild")
        # E046 续：in-source 构建的 Makefile 落在 source_folder（缓存 create
        # 中即 p/b/<id>/b 根，实测该目录含完整源码树+Makefile），而
        # Autotools.make() 默认 cwd=build_folder（basic_layout 的
        # build-release 子目录，只有 conan 生成物）→ "No targets specified
        # and no makefile found"。make 是真 ELF 可直接 execve（E046 只杀
        # HMDFS 上的 shell 脚本），仅需 conanbuild 环境变量。
        self.run('cd "{}" && make -j1'.format(self.source_folder),
                 env="conanbuild")
        # 上游单元测试（libtest + modules/*/tests，criterion 驱动）不在
        # build() 内执行：保持 conan create 确定性（单条平台性用例失败不
        # 拖垮整包），与仓库惯例一致（upstream_test_in_build=false）。
        # enable_tests 仍经 CRITERION 探测自动开启；make check 在设备上
        # 于缓存构建树内全量实跑（见 notes.md「重跑步骤」第 3 步）。

    def package(self):
        # 同 build()：install 必须与 configure 同树（in-source）执行，
        # Autotools.install() 默认 cwd=build_folder 会再次找不到 Makefile。
        # DESTDIR=package_folder 必须显式带上（AutotoolsToolchain 的
        # --prefix="/" 配套约定，Autotools.install() 同款默认，conan
        # autotools.py:111）：缺省会按 prefix=/ 直写系统根（实测
        # "mkdir -p '//lib'" → OHOS 根分区 EROFS，"install: //lib/...
        # Read-only file system"，失败#8）。
        self.run('cd "{}" && make install DESTDIR="{}"'.format(
            self.source_folder, self.package_folder),
            env="conanbuild")
        # HMDFS：install 产物统一放开读权限（rsyslog 同款）。
        if self.settings.os in ("Linux", "OHOS"):
            self.run(f'chmod -R a+r "{self.package_folder}"')
            self.run(f'find "{self.package_folder}" -type d -exec chmod a+rx {{}} \\;')

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = ["lib", "lib/syslog-ng"]
        # 模块目录经 SYSLOGNG_PREFIX 环境变量重定位（lib/reloc.c
        # lookup_sysprefix；编译期默认 /lib/syslog-ng）——消费者必须拿到
        # 真实包前缀才能 dlopen 到模块（RSYSLOG_MODDIR 同款）。
        self.runenv_info.define("SYSLOGNG_PREFIX", self.package_folder)
        # 兜底：依赖库目录进运行期 LD_LIBRARY_PATH（防消费者侧重定位失效）。
        for dep in self._all_dependencies():
            if not dep.package_folder:
                continue
            for libdir in self._dep_dirs(dep)[1]:
                self.runenv_info.append_path("LD_LIBRARY_PATH", libdir)
