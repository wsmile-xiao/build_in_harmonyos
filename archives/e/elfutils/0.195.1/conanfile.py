#!/usr/bin/env python3
"""Conan recipe — elfutils 0.195.1 (autotools)

0.195.1 = 0.195 + 「把 libdebuginfod 从 dummy 空壳改成真实客户端库」。

背景（上游两个互相独立的开关，configure.ac:898-973）：
  --enable-libdebuginfod[=yes|dummy|no]  libdebuginfod 客户端库
  --enable-debuginfod[=yes|no]           debuginfod 服务端

0.195 用的是 `--enable-libdebuginfod=dummy`：包里虽然也外发
libdebuginfod.so.1，但那是空壳 —— debuginfod_begin() 直接
`errno = ENOSYS; return NULL;`（debuginfod/debuginfod-client.c:64），
实测该 .so 的 DT_NEEDED 只有 libc.so、体积 18880 字节。
`bin/debuginfod-find` 因此只是个必然失败的客户端。

0.195.1 改成 `--enable-libdebuginfod=yes`，产出真实客户端库：
  - configure 用 PKG_CHECK_MODULES 探测 libcurl >= 7.29.0 与 json-c >= 0.11
    （configure.ac:907-908），故 requirements 增 curl/json-c，并在 generate()
    里把这两个包内自带的 .pc 目录（lib/pkgconfig）注入 PKG_CONFIG_PATH
    —— 实测 AutotoolsDeps 在本依赖图里产出的脚本**不含 PKG_CONFIG_PATH**，
    不注入就报 `configure: error: unable to build libdebuginfod, missing
    libjson-c or libcurl`。
  - 真实 libdebuginfod.so 链接 libcurl + libelf（build-id 解析）+ json-c
    + fts + crypto（debuginfod/Makefile.am 的 libdebuginfod_so_LDLIBS），
    故其 DT_NEEDED 比 dummy 多了 libcurl/libelf/json-c。
  - 服务端仍保持 `--disable-debuginfod`：它需要 libmicrohttpd + sqlite3
    + libarchive（configure.ac:922-949），OHOS PC 无 debuginfod 服务端
    运行时场景，而「只建客户端」是上游支持的组合。

本版本附带修掉 0.195 配方在当前环境下暴露的两个构建缺陷（读源码即知、无需改上游）：
  1. `configure` 不能直接 exec：`autotools.configure()` 报
     `Error 126 Permission denied`。本机实测成因是**构建子进程落在受限的
     SELinux 域**（`u:r:adhoc_bin:s0`）——该域**拒绝 exec 缓存目录里的文件**
     （`/system/bin/sh: ./configure: Permission denied`），但普通文件/目录的
     创建与读写都正常。改为 OHOS 上经显式 shell 执行：`sh <configure>` 只
     **读取**脚本、不 exec 它，因此不受该限制。这也是仓库既有写法
     （`CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh /system/bin/sh
     <configure>`，全仓 28 个包在用，如 abx 0.1）。
  2. 探测程序运行期库路径：`configure` 会**编译并运行**探测程序，运行期要
     找得到所有依赖的 .so（原本只列 musl-fts/musl-obstack 也会出问题，新增
     curl/json-c 后漏一个就是 `configure: error: cannot run C compiled
     programs`）。这里改为覆盖**全部**依赖（含传递依赖）的 libdir。
"""
import glob
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout


# 上游用例集中依赖 glibc 专有接口、在 OHOS musl 上**无法构建**的 6 条用例。
# automake 的 `check-am` 依赖**全部** check_PROGRAMS，任何一个测试程序编不出来，
# 整批用例都不会被执行 —— 所以必须同时从 TESTS 与 check_PROGRAMS 里剔除，
# 否则得到的是「0 条用例执行」而不是「253 条用例执行」。
#
#   <error.h>        glibc 扩展头，OHOS musl 不提供
#                    → dwfl-report-offline-memory、eu_search_macros（编译期 fatal）
#   pthread_cancel   OHOS musl 的 pthread.h 与 libc.so 都没有该符号
#                    （上游 musl 本身有实现，OHOS 变体裁掉了）
#                    → dwfl-proc-attach、eu_search_cfi/die/lines/macros（链接期 undefined）
#
# 这 6 条在上游 TESTS(259) / check_PROGRAMS(128) 中各占一项。
_UPSTREAM_TESTS_SKIPPED = (
    "run-dwfl-report-offline-memory.sh",
    "dwfl-proc-attach",
    "run-eu-search-cfi.sh",
    "run-eu-search-die.sh",
    "run-eu-search-lines.sh",
    "run-eu-search-macros.sh",
)
_UPSTREAM_PROGRAMS_SKIPPED = (
    "dwfl-report-offline-memory",
    "dwfl-proc-attach",
    "eu_search_cfi",
    "eu_search_die",
    "eu_search_lines",
    "eu_search_macros",
)
# 构建树里会产生共享库、且运行期按 SONAME 被加载的目录
_BUILD_LIBDIRS = ("libelf", "libdw", "libasm", "debuginfod")


class ElfutilsConan(ConanFile):
    name = "elfutils"
    version = "0.195.1"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"


    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("zstd/1.5.7")
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.6.2")
        self.requires("argp-standalone/1.5.0")
        self.requires("musl-fts/1.2.7")
        self.requires("musl-obstack/1.2.3")
        # libdebuginfod 真实客户端库的外部依赖（configure 用
        # PKG_CHECK_MODULES 探测 libcurl >= 7.29.0 / json-c >= 0.11）
        self.requires("curl/8.15.0")
        self.requires("json-c/0.18")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        # libdebuginfod 的两个外部依赖由 configure 的 PKG_CHECK_MODULES 探测
        # （libcurl >= 7.29.0、json-c >= 0.11，configure.ac:907-908）。
        # 用 PkgConfigDeps 为**全部**依赖生成 .pc：只把依赖包里自带的 .pc 目录
        # 塞进 PKG_CONFIG_PATH 不够 —— curl 包内那份 libcurl.pc 带
        # `Requires.private: openssl,zlib`，而 openssl 包里根本没有
        # pkgconfig 目录，pkg-config 会因解析不了该依赖判定 libcurl「不存在」
        # （实测 `Package 'openssl', required by 'libcurl', not found` →
        # `checking for libcurl >= 7.29.0... no`）。PkgConfigDeps 生成的
        # .pc 覆盖整条依赖链，是仓库既有做法（acsccid 1.1.13 /
        # air-quality-sensor 0.1.5 先例）。
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-werror")
        # 真实 libdebuginfod 客户端库（=dummy 只产出 debuginfod_begin()
        # 恒返回 NULL + ENOSYS 的空壳）
        tc.configure_args.append("--enable-libdebuginfod=yes")
        # 服务端需 libmicrohttpd + sqlite3 + libarchive，本仓不提供，OHOS PC
        # 也无该运行时场景；「只建客户端」是上游支持的组合
        tc.configure_args.append("--disable-debuginfod")
        tc.configure_args.append("--with-zstd")
        tc.configure_args.append("--program-prefix=eu-")
        # musl 需要的三项（与 Alpine 的 elfutils APKBUILD 一致）：
        #   _GNU_SOURCE      —— musl 在此宏下才暴露 program_invocation_short_name
        #                       （lib/color.c、src/{elflint,readelf,elfcmp}.c 都用它）
        #   FNM_EXTMATCH=0   —— musl 的 fnmatch.h 没这个宏（探针实测）
        #   -Wno-error       —— musl 与 glibc 的细节差异会触发若干告警，
        #                       上游 --disable-werror 只管它自己的 -Werror
        tc.extra_cflags.append("-D_GNU_SOURCE")
        tc.extra_cflags.append("-DFNM_EXTMATCH=0")
        tc.extra_cflags.append("-Wno-error")
        tc.extra_cxxflags.append("-D_GNU_SOURCE")
        tc.extra_cxxflags.append("-Wno-error")

        # ── 依赖的 -I / -L / -l 必须经环境变量喂给 configure ──
        # elfutils 的 configure 用 AC_CHECK_LIB 类探测（如 --with-zstd 会试链 -lzstd），
        # 不给路径就报 `configure: error: missing -lzstd for --with-zstd`。
        # 走 os.environ 而非 AutotoolsToolchain.extra_* —— 后者实测不一定落到 configure
        # 的编译/链接探测里（本仓 autotools-dep-header-missing 规则的既有结论）。
        import os
        _inc, _lib, _l = [], [], []
        for _ref, _dep in self.dependencies.items():
            ci = _dep.cpp_info
            for _p in ci.includedirs or []:
                _inc.append("-I" + _p)
            for _p in ci.libdirs or []:
                _lib.append("-L" + _p)
            for _n in ci.libs or []:
                _l.append("-l" + _n)
        os.environ["CPPFLAGS"] = " ".join(_inc) + " " + os.environ.get("CPPFLAGS", "")
        os.environ["LDFLAGS"] = " ".join(_lib) + " " + os.environ.get("LDFLAGS", "")
        # 三个 musl 垫片（argp / fts / obstack）提供的是 glibc 才有的符号，
        # elfutils 的源码直接调它们，故必须显式进 LIBS，否则链接期 undefined。
        os.environ["LIBS"] = " ".join(_l) + " " + os.environ.get("LIBS", "")
        # libdebuginfod 的两个外部依赖由 configure 的 PKG_CHECK_MODULES 探测
        # （libcurl >= 7.29.0、json-c >= 0.11，configure.ac:907-908），必须让
        # pkg-config 找到它们的 .pc —— 否则报
        # `configure: error: unable to build libdebuginfod, missing libjson-c or libcurl`。
        #
        # 第一顺位是 PkgConfigDeps 的输出目录（见 generate() 开头），它含
        # 整条依赖链的 .pc；依赖包内自带的 pkgconfig 目录作为第二顺位。
        # 与上面 CPPFLAGS/LDFLAGS/LIBS 同一理由走 os.environ：conan 生成的
        # 环境脚本在这一路径上不一定落到 configure 进程里。
        _pc = [self.generators_folder]
        for _dep in (d for _r, d in self.dependencies.items()):
            for _p in _dep.cpp_info.libdirs or []:
                _pc_dir = os.path.join(_p, "pkgconfig")
                if os.path.isdir(_pc_dir):
                    _pc.append(_pc_dir)
        os.environ["PKG_CONFIG_PATH"] = ":".join(_pc) + ":" + os.environ.get("PKG_CONFIG_PATH", "")
        self.output.info("PKG_CONFIG_PATH=%s" % os.environ["PKG_CONFIG_PATH"][:240])
        self.output.info("CPPFLAGS=%s" % os.environ["CPPFLAGS"][:200])
        self.output.info("LDFLAGS=%s" % os.environ["LDFLAGS"][:200])
        self.output.info("LIBS=%s" % os.environ["LIBS"][:200])
        # configure 会**编译并运行**探测程序（"checking whether we are cross compiling"）。
        # 我们把 musl-fts / musl-obstack 这两个**共享库**放进了 LIBS，0.195.1
        # 起又加了 -lcurl/-ljson-c（连带 openssl/brotli/nghttp2/libssh2/zlib…），
        # 探测程序链上它们后运行时找不到 .so →
        # `configure: error: cannot run C compiled programs.`（config.log 里紧邻
        # `./conftest` 的那行 `Error loading shared library libcurl.so: (needed by
        # ./conftest)` 就是它）。
        #
        # 关键：**不能用 -Wl,-rpath 解决** —— 那会把 conan cache 绝对路径烤进
        # 产物的 RPATH，正是本仓一直在修的「安装产物里烤死构建期路径」那个病。
        # 用 LD_LIBRARY_PATH：只影响构建期的进程执行，不进任何产物。
        #
        # ⚠️ 必须走 `Environment` + `save_script()`（而不是直接改 os.environ）：
        # 上面 CPPFLAGS/LDFLAGS/LIBS 用 os.environ 实测能落到 configure，但
        # LD_LIBRARY_PATH 会与 conan 自己生成的 `conanbuildenv-*.sh`（它也要
        # export LD_LIBRARY_PATH）撞车，传递不稳定 —— 同一配方会出现"这次过、
        # 下次 `cannot run C compiled programs`"。save_script 是 conan 明确支持
        # 的注入通道，确定性生效。仓库既有写法（`aaphoto` 0.45 / `dirb` 2.22
        # 同款；知识条目 DRAFT-conan-dep-shared-libs-break-configure-conftest）。
        #
        # 覆盖**全部**依赖（含传递依赖）的 libdir 与 bindir —— 漏一个 curl 的
        # 传递依赖，探测程序就起不来。
        env = Environment()
        for _dep in self.dependencies.values():
            for _p in _dep.cpp_info.libdirs or []:
                env.prepend_path("LD_LIBRARY_PATH", _p)
            for _p in _dep.cpp_info.bindirs or []:
                env.prepend_path("PATH", _p)
        env.vars(self, scope="build").save_script("conanbuild_elfutils_probe")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 发布 tarball（ftp.gnu.org 那类）里带现成的 configure，直接用；
        # 但 **GitHub 的 archive tarball 从不含 configure**（它只是 git tree 的快照，
        # configure 是 autoreconf 的产物、不进版本库），此时必须先自举。
        # 判在运行期而非生成期：同一份配方两种源都能用。
        import os as _os
        if not _os.path.isfile(_os.path.join(self.source_folder, "", "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            autotools.autoreconf()
        # ⚠️ umask / uname 这类对 configure 脚本本身的修补**必须在 autoreconf 之后**：
        # 自举会重新生成 configure，放在前面等于白改（改的是不存在的文件，
        # 或改完又被覆盖）。
        import glob, os
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        self._configure(autotools)
        autotools.make(args=["-j1"])
        # 真实执行上游 `make check` 用例集（结果落 upstream-tests-summary.txt，
        # 不改变构建成败；见方法注释）
        self._run_upstream_tests()

    def _configure(self, autotools):
        """调用 configure；OHOS 上经显式 shell，绕开「不能直接 exec」这一限制。

        `autotools.configure()` 在本环境直接报 `Error 126 Permission denied`。
        本机实测成因：构建子进程落在受限的 SELinux 域 `u:r:adhoc_bin:s0`，
        该域**拒绝 exec 缓存目录里的文件**（`/system/bin/sh: ./configure:
        Permission denied`），而普通文件/目录的创建与读写都正常。
        `sh <configure>` 只**读取**脚本、不 exec 它，故不受该限制；这也是
        仓库既有写法（`CONFIG_SHELL` + `SHELL` 同指向该 shell，全仓 28 个包
        在用，如 abx 0.1）。CONFIG_SHELL/SHELL 一并指向 `/system/bin/sh`，
        还能保证 config.status 与 config/install-sh 等子脚本走同一解释器。

        非 OHOS 平台仍走标准 autotools.configure()。
        """
        configure_script = os.path.join(self.source_folder, "configure")
        if (str(self.settings.os) not in ("OHOS", "HarmonyOS")
                or not os.path.isfile(configure_script)):
            autotools.configure()
            return
        command = ("CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh "
                   + shlex.join(["/system/bin/sh", configure_script]))
        if autotools._configure_args:
            command = "{} {}".format(command, autotools._configure_args)
        self.output.info("configure via explicit shell (OHOS: 绕开受限域不能 exec 缓存文件)")
        self.run(command, cwd=self.build_folder)

    # ──────────────────────── 上游用例执行（make check） ────────────────────────

    def _test_run_env(self):
        """把「执行上游用例」需要的运行期环境注入 conanbuild（build 作用域）。

        只影响测试进程，不进任何产物、不改上游源码：
          * LD_LIBRARY_PATH += **构建树自身**的库目录 —— `src/*` 工具与
            `tests/*` 程序都按 SONAME 加载它们（`AM_LDFLAGS` 只有
            `-rpath-link`，仅链接期有效）。缺了会报
            `Error loading shared library libdw.so.1: (needed by .../src/readelf)`
            并连带上百条用例批量失败
          * 清 `BASH_ENV`：宿主 shell 的包装脚本会被 bash 子进程继承并污染
            （实测表现为 `... safe-delete-bash-env.sh: ... rm: ...: bad interpreter`）

        ⚠️ **不要在这里改 PATH** —— 见 `_wc_shim_dir()` 的说明（会把 autotools 的
        `$(LN_S)` 带偏，构建直接死在 `ln -fs libelf.so libelf.so.1`）。
        """
        env = Environment()
        for _d in _BUILD_LIBDIRS:
            _p = os.path.join(self.build_folder, _d)
            if os.path.isdir(_p):
                env.prepend_path("LD_LIBRARY_PATH", _p)
        # check_PROGRAMS 的链接规则是
        #   $(CC) $(CHECK_DEF_FLAGS) -o $@ … $(libelf_so_LDLIBS)
        # **不含 $(LDFLAGS)**（上游假定依赖在系统默认路径），所以 conan 依赖的
        # `-L` 上不了链接行 → 报 `cannot find -lzstd`。用 `LIBRARY_PATH` 补：
        # 它是链接器的标准搜索路径变量，不改任何产物、也不污染上游规则。
        for _dep in self.dependencies.values():
            for _p in _dep.cpp_info.libdirs or []:
                env.prepend_path("LIBRARY_PATH", _p)
        env.define("LC_ALL", "C")
        env.define("LANG", "C")
        env.unset("BASH_ENV")
        env.vars(self, scope="build").save_script("conanbuild_elfutils_upstream_tests")

    def _wc_shim_dir(self):
        """在构建目录里放一个 `wc` 兼容脚本并返回其所在目录。

        上游 3 处用例（`run-strip-test.sh:56` 等）用 `wc --lines`（GNU 长选项），
        OHOS 的 toybox 与 hnp 的 busybox `wc` 都只认 `-l` → `wc: Unknown option
        'lines'`，13 条 `run-strip-*` 整批失败。这里用一个**脚本**把 GNU 长选项
        映射成短选项后转发系统 `wc`。

        ⚠️ 为什么不用 `tool_requires("coreutils/9.10")`（试过，把构建搞挂了）：
        **tool_requires 的 `cpp_info.bindirs` 会被 conan 自动注入构建期 PATH**
        （实测生成的 `conanbuild.sh` 里出现 `.conan2/p/coreu…/p/bin`，
        `command -v ln` 随即指向 coreutils 的 `ln`）。而 `.conan2/p/…` 下的
        可执行文件是**未签名 ELF**，执行它会切换到 SELinux 域
        `u:r:adhoc_bin:s0`，该域**拒绝 `symlink()`** —— autotools 的 `$(LN_S)`
        于是死在
        `ln: failed to create symbolic link 'libelf.so.1': Permission denied`
        （实测对照：系统 `/usr/bin/ln`（toybox）建链 rc=0，coreutils 的 `ln` rc=1）。
        同理，用 `Environment.prepend_path("PATH", …)` 全局注入也会带偏 `ln`/`rm`。

        脚本的 shebang 是系统解释器 `/system/bin/sh`（不触发域切换），
        且这个目录**只在测试命令里**前置，构建过程完全不受影响。

        另一个坑：本机 `chmod` 常为空操作（实测 `chmod 755` 只得到 770），
        而**没有可执行位的文件会被 PATH 查找直接跳过**（shim 静默失效、
        仍旧命中 `/bin/wc`）。故先 `copy2` 一个系统可执行文件占位再覆写内容，
        以保住 755（与 `ohos-worker-env-triage` 里那条同源手法）。
        """
        tools = os.path.join(self.build_folder, "eu-test-tools")
        shim = os.path.join(tools, "wc")
        if os.path.isfile(shim) and os.access(shim, os.X_OK):
            return tools
        os.makedirs(tools, exist_ok=True)
        body = (
            "#!/system/bin/sh\n"
            "# OHOS 测试期 `wc` 兼容层：GNU 长选项 → toybox 短选项，转发系统 wc。\n"
            "# 仅用于执行上游用例；不参与任何产物。\n"
            'out=""\n'
            'for a in "$@"; do\n'
            "  case \"$a\" in\n"
            "    --lines|--line)    a=-l ;;\n"
            "    --words|--word)    a=-w ;;\n"
            "    --bytes|--byte)    a=-c ;;\n"
            "    --chars|--char)    a=-m ;;\n"
            "    --max-line-length) a=-L ;;\n"
            "  esac\n"
            '  if [ -z "$out" ]; then out="$a"; else out="$out $a"; fi\n'
            "done\n"
            "exec /usr/bin/wc $out\n"
        )
        try:
            shutil.copy2("/usr/bin/wc", shim)   # 占位：继承系统文件的 755
        except OSError:
            pass
        with open(shim, "w", encoding="utf-8") as fh:
            fh.write(body)
        try:
            os.chmod(shim, 0o755)
        except OSError:
            pass
        if not os.access(shim, os.X_OK):
            self.output.warning("%s 不可执行；`wc --lines` 可能失败" % shim)
        return tools

    def _materialize_build_tree_sonames(self):
        """把构建树 lib/ 里的 SONAME 软链换成实体副本。

        elfutils 的 Makefile 用 `ln -fs libX.so libX.so.1` 建 SONAME 别名，
        而 OHOS 的加载器**不跟随符号链接**（命中软链即
        `Error loading shared library libX.so.1`），构建树里所有 `src/*` 工具
        与测试程序因此起不来。做法与 `package()` 的 `_materialize_soname_aliases()`
        一致，只是作用在构建树。
        """
        count = 0
        for _d in _BUILD_LIBDIRS:
            _dd = os.path.join(self.build_folder, _d)
            if not os.path.isdir(_dd):
                continue
            for _f in sorted(glob.glob(os.path.join(_dd, "*.so*"))):
                if not os.path.islink(_f):
                    continue
                _real = os.path.realpath(_f)
                if not os.path.isfile(_real):
                    continue
                _tmp = _f + ".conanmv"
                shutil.copy2(_real, _tmp)
                os.replace(_tmp, _f)
                count += 1
        self.output.info("构建树 SONAME 软链实体化 %d 个" % count)

    def _upstream_make_var(self, name):
        """用 make 自身的展开结果取变量（含 `$(am__append_N)` 分叉）。

        不解析 Makefile 文本：TESTS / check_PROGRAMS 里含 `$(am__append_N)`
        间接引用，文本解析会漏项（实测漏 12 条、多算 8 个未展开变量）。
        """
        _out = os.path.join(self.build_folder, "upstream-var-%s.txt" % name)
        self.run(
            "make --eval='eu-print-var:; @printf \"%%s\\n\" $(%s)' eu-print-var"
            " > '%s' 2>/dev/null || true" % (name, _out),
            cwd=os.path.join(self.build_folder, "tests"),
            env="conanbuild")
        try:
            with open(_out, encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
        except OSError:
            return []
        items, seen = [], set()
        for _t in raw.split():
            _t = _t.replace("$(EXEEXT)", "")
            if _t and _t not in seen:
                seen.add(_t)
                items.append(_t)
        return items

    def _trs_results(self):
        """读 automake 的 `*.trs`（一条用例一个文件），返回 {用例名: PASS/FAIL/SKIP}。"""
        tests_dir = os.path.join(self.build_folder, "tests")
        results = {}
        try:
            names = os.listdir(tests_dir)
        except OSError:
            return results
        for _n in names:
            if not _n.endswith(".trs"):
                continue
            try:
                with open(os.path.join(tests_dir, _n), encoding="utf-8",
                          errors="replace") as fh:
                    txt = fh.read()
            except OSError:
                continue
            _m = re.search(r":test-result:\s*(\w+)", txt)
            if _m:
                results[_n[:-4]] = _m.group(1)
        return results

    def _run_upstream_tests(self):
        """真实执行上游 `make check` 用例集，汇总写入 `upstream-tests-summary.txt`。

        口径（本机 OHOS PC aarch64 W3 环境实测）：
          上游 TESTS 259 条、check_PROGRAMS 128 个；其中 6 条用例（及对应测试
          程序）依赖 OHOS musl 未提供的 glibc 接口（`<error.h>` / `pthread_cancel`，
          见 `_UPSTREAM_TESTS_SKIPPED` 注释），剔除后 253 条全部执行。

        `-k` 保证单条失败不中断；失败清单与结果只作汇报，**不使 `conan create`
        失败**（与 binutils 2.46.0 对 `make check` 的处理一致）；但「一条都没跑
        起来」视为测试环境失效，直接抛错，避免把环境问题伪装成通过。
        """
        tests_dir = os.path.join(self.build_folder, "tests")
        if not os.path.isdir(tests_dir):
            self.output.warning("无 tests/ 目录，跳过上游用例执行")
            return
        self._test_run_env()

        all_tests = self._upstream_make_var("TESTS")
        progs = [p for p in self._upstream_make_var("check_PROGRAMS")
                 if p not in _UPSTREAM_PROGRAMS_SKIPPED]
        tests = [t for t in all_tests if t not in _UPSTREAM_TESTS_SKIPPED]
        if not tests:
            raise ConanException("取不到上游 TESTS 清单，测试环境失效")

        # 清掉历史结果，保证这一轮是完整记录
        for _n in os.listdir(tests_dir):
            if _n.endswith(".trs") or _n.endswith(".log"):
                try:
                    os.unlink(os.path.join(tests_dir, _n))
                except OSError:
                    pass

        # ── 第一步：只构建 check_PROGRAMS（`check TESTS=` = 建程序不跑用例）──
        # 必须与「实体化软链」分两步：构建过程可能重新链接 libX.so 并把
        # `libX.so.N` 的软链重建回去，那样用例运行期又会加载失败。
        build_log = os.path.join(self.build_folder, "upstream-check-build.log")
        _wc_dir = self._wc_shim_dir()
        _pfx = 'PATH="%s:$PATH" ' % _wc_dir if _wc_dir else ""
        try:
            self.run(
                "%smake -k -j1 check TESTS= check_PROGRAMS='%s' > '%s' 2>&1"
                % (_pfx, " ".join(progs), build_log),
                cwd=tests_dir, env="conanbuild")
        except ConanException as exc:
            self.output.warning("部分 check_PROGRAMS 未构建成功：%s" % str(exc)[:160])

        # ── 第二步：实体化构建树 lib/ 的 SONAME 软链 ──
        self._materialize_build_tree_sonames()

        # ── 第三步：只跑用例（check-TESTS 也依赖 check_PROGRAMS，故仍要传变量）──
        check_log = os.path.join(self.build_folder, "upstream-check.log")
        cmd = ("%smake -k -j1 check-TESTS TESTS='%s' check_PROGRAMS='%s'"
               % (_pfx, " ".join(tests), " ".join(progs)))
        try:
            self.run(cmd + " > '%s' 2>&1" % check_log, cwd=tests_dir, env="conanbuild")
        except ConanException as exc:
            self.output.warning("上游用例有失败（make 非 0 退出）：%s" % str(exc)[:160])

        results = self._trs_results()
        if not results:
            raise ConanException("上游用例一条都没执行，见 %s" % check_log)
        counts = {}
        for _v in results.values():
            counts[_v] = counts.get(_v, 0) + 1
        fails = sorted(n for n, v in results.items() if v == "FAIL")
        skips = sorted(n for n, v in results.items() if v == "SKIP")

        lines = [
            "elfutils %s 上游测试用例执行汇总（OHOS PC aarch64 / musl）" % self.version,
            "上游 TESTS 总数            : %d" % len(all_tests),
            "因 OHOS musl 缺接口而无法构建: %d（%s）"
            % (len(all_tests) - len(tests), ", ".join(_UPSTREAM_TESTS_SKIPPED)),
            "实际执行用例数             : %d" % len(results),
            "  PASS : %d" % counts.get("PASS", 0),
            "  FAIL : %d" % counts.get("FAIL", 0),
            "  SKIP : %d" % counts.get("SKIP", 0),
            "  XFAIL/XPASS/ERROR : %d / %d / %d"
            % (counts.get("XFAIL", 0), counts.get("XPASS", 0), counts.get("ERROR", 0)),
            "通过率（执行集）: %.1f%%" % (100.0 * counts.get("PASS", 0) / len(results)),
            "",
            "失败用例（%d）：" % len(fails),
        ]
        lines += ["  - " + _f for _f in fails]
        lines += ["", "跳过用例（%d）：" % len(skips)]
        lines += ["  - " + _f for _f in skips]
        lines += ["", "完整日志: %s" % check_log]

        summary = os.path.join(self.build_folder, "upstream-tests-summary.txt")
        with open(summary, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        for _l in lines:
            self.output.info(_l)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._sign_binaries()
        self._materialize_soname_aliases()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted（cmake/SDK-toolchain 产的自签无效，且 conan install 复制会破坏链接器自签）。
        # ① lib/ 的 .so  ② bin/ 的 ELF 可执行文件（llvm-config/xxx CLI 等）——产可执行文件的包必须签 bin。
        import glob, os
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        # ⚠️ 必须 `env -u LD_LIBRARY_PATH`：本配方 generate() 把全部依赖（含传递依赖）
        # 的 libdir 塞进了 LD_LIBRARY_PATH（configure 探测程序运行期需要），该变量会
        # 被 conan 的 buildenv 继承到 package() 阶段；而 binary-sign-tool 自身 NEEDED
        # 的是**系统** libc++（std::__h 内联命名空间），在 SDK 的 llvm/lib 抢先下会
        # 加载到 std::__1 的另一份 libc++ → 工具报 relocating/symbol not found 或
        # **静默产出 XPM 不认的签名**。实测症状极具迷惑性：日志显示
        # "add codesign section success"，但装出来的 .so 一被 dlopen 就
        # `Permission denied`；交互 shell 里手动签同样文件却正常（因为那里没这个变量）。
        # 仓库既有写法，全仓 22 个包同款（cliquer 1.21 / concalc 0.9.3 等）。
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('env -u LD_LIBRARY_PATH {oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def _materialize_soname_aliases(self):
        """把 lib/ 下的 SONAME / 开发名别名软链替换为实体副本（知识条目 E316 / E492）。

        上游 install 产出标准三段式命名，`.so` 与 `.so.1` 都是**符号链接**：
            libelf.so -> libelf.so.1 -> libelf-0.195.so

        这在 OHOS 上是加载致命项：ELF 的 `DT_NEEDED` 记的是 **SONAME**
        （`libelf.so.1`），加载器按该名字 open 路径时若命中的是符号链接，在
        不具备符号链接解析能力的域下会得到 **EACCES**；而 musl 加载器只在
        `ENOENT`/`ENOTDIR` 时才继续搜索下一个目录 —— 于是立即整体失败：

            Error loading shared library libelf.so.1: (needed by ./test_probe)
            Error relocating ./test_probe: elf_version: symbol not found   → rc=127

        实测（本机 dlopen 探针，`u:r:adhoc_bin:s0` 域，XPM 校签名最严的上下文）：
        同一批文件**用实体名加载全部 OK、用 SONAME 软链名加载一律 Permission
        denied**；把软链换成实体副本后立刻正常。

        旁证：本机 conan 缓存里已发布的 `elfutils/0.195` 及其他依赖包的 `lib/`
        **全部是实体文件、0 软链**，唯独本包（新构建）是软链 —— 这正是 0.195
        的 test_package 只有 1 条 dlopen 断言（且那条走的是实体名）而没暴露它的原因。

        做法与 `archives/l/libkysdk-base/3.0.1.3` 的 `_materialize_soname_aliases`
        一致（E316 / E492 的 rec）：`shutil.copy2` 跟随软链复制实体（保留权限位），
        先写临时名再 `os.replace` 原子替换，避免删除系统调用。
        放在 `_sign_binaries()` **之后**：签名对象是真实文件，副本随内容一起
        带走签名（复制不破坏签名，本仓 2026-08-04 真机对照实验结论）。
        """
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for name in sorted(os.listdir(lib_dir)):
            path = os.path.join(lib_dir, name)
            if not os.path.islink(path):
                continue
            entity = os.path.realpath(path)   # 跟随软链取实体
            if not os.path.isfile(entity):
                continue
            tmp = path + ".entity"
            shutil.copy2(entity, tmp)
            os.replace(tmp, path)             # 原子替换掉软链本身

    def package_info(self):
        # 0.195.1 起 libdebuginfod 是真实客户端库，纳入导出列表。
        # 存量 elfutils/0.195 消费者精确 pin 到 0.195，不会被动受影响；
        # 新消费者会额外链 -ldebuginfod（其运行期依赖 curl/json-c 由本包
        # 的 requires 传递，conanrun 自动带上）。
        explicit_libs = ['elf', 'dw', 'asm', 'debuginfod']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "elfutils")
        self.cpp_info.set_property("cmake_target_name", "elfutils::elfutils")
        pkg = "" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
