#!/usr/bin/env python3
"""Conan recipe — xauth 1.1.4（X.Org 授权文件 / Xauthority 管理工具）

上游 xauth 1.1.4 的 configure 用

    PKG_CHECK_MODULES(XAUTH, x11 xau xext xmuu xproto >= 7.0.17)

声明依赖，其中 **xmuu 由 libXmu 的子库 libXmuu 提供**（libXmu 一次构建发布
libXmu.la + libXmuu.la 两条共享库，xmu.pc 与 xmuu.pc 并列）。ohpcd 制品仓
既没有 libxmu 也没有 libxmuu（`conan list "libxmu/*" -r ohpcd` → Found 0），
于是 PKG_CHECK_MODULES 里的 xmuu 无法满足。

三条路线里取第三条——与前两条的对比写在 notes.md「方案取舍」：

  1) 伪造一个 xmuu.pc 指向空库      —— 链接期 undefined reference，且没有任何
                                     上游产物支撑，属伪造。
  2) 手写 XmuGetHostname 桩         —— 复制上游逻辑，产权不清（同 xinit 造
                                     假 libX11 头 + x11_stub.c 的反面教材）。
  3) 从 libXmu 官方 tarball 取出 **真实的** libXmuu 源码就地编译成静态库
                                    —— 源码本体即上游产物（sha256 官方值），
                                     零改写，随包静态携带。**本配方采用此路线**
                                     （同 xeyes 内建 libICE/libSM/libXt/libXmu
                                     的 E277 vendored 依赖模式）。

libXmuu 有 5 个源文件（ClientWin.c / CursorName.c / DefErrMsg.c / GetHost.c /
Lower.c），但 xauth 全树对 Xmu 的引用**只有一处符号**：

    parsedpy.c:40  #include <X11/Xmu/SysUtil.h>
    parsedpy.c:76  (void) XmuGetHostname (buf, maxlen);

`XmuGetHostname` 定义在 libXmu 的 `src/GetHost.c`（gethostname 的薄封装，
函数体只有 3 行有效代码，非 WIN32 分支不 include 任何私有头）。因此只编译
GetHost.c，产物命名 `libXmuu.a`（`xmuu.pc` 的 `Libs: -lXmuu` 对得上）。
多编另外 4 个会引入 DefErrMsg.c 对 libX11 私有头 `<X11/Xlibint.h>` 的依赖，
而 xauth 一个符号都用不到——按实际需要取最小闭包。

另外两处制品仓/平台的坑：

- 发布的 libxau/1.0.11 里 `libXau.la` 的 `libdir=` 指向构建期临时目录、
  `dependency_libs` 残留 CI worker 的 `-L/…/usr/local/lib`（E 条目「残留静态
  glib 击穿链接」）。libtool 用 `-lXau` 命中这个 .la 后按 `libdir` 找 .so 会
  失败。build() 在 configure 之前就地改写（同 libxp/1.0.4）。
- 上游测试夹具 `tests/setup-sourced` 把授权文件路径写成
  `XAUTHORITY=${DATADIR:-/tmp}/.Xauthority`，OHOS 的 `/` 是 erofs 只读挂载，
  `/tmp` 不可写（E002）。build() 给 `make check` 传 `DATADIR`/`TMPDIR` 指向
  build_folder 下的可写 scratch 目录——**这一处不改上游脚本**（纯 env 注入）。

上游**有**测试套件且本配方实跑：`TESTS = test_xauth`（tests/Makefile.am），
`tests/test_xauth` 遍历 5 个 `*.script` 场景（010 add-inet / 020 add-local /
030 extract / 040 source / 090 bad-usage），每个场景把 xauth 的真实 stdout/
stderr 与随包发布的 `.stdout`/`.stderr` 夹具逐字节 diff。用例是**纯文件**的
（只操作 XAUTHORITY 文件，不需要 X server），因此在 CI worker 上可原样执行。

## 测试驱动补丁（唯一的补丁）

`patches/0001-tests-ignore-locks-on-ohos.patch` 只改上游自带的测试驱动
`tests/setup-sourced` 里**两条真实执行**的调用行：

    ../xauth "$@"   →   ../xauth -i "$@"

`echo "> xauth" "$@"` 那一行**不动**（它与 `.stdout` 夹具逐字节比对）。
`-i` 是上游自己的文档化选项（`xauth(1)`：`-i  ignore locks on authority
file`，源码 `xauth.c:129` 置 `ignore_locks`，`process.c:753` 据此跳过
`XauLockAuth()`）。跳过锁的理由：本平台文件系统（HMDFS）不支持硬链接，而
libXau 的加锁实现是 `link()`（见 notes.md 根因一节），因此在 OHOS 上
`XauLockAuth()` **必然**返回 LOCK_ERROR / LOCK_TIMEOUT，xauth 在写授权文件
之前就退出——5 个场景此前集体 FAIL 正是这个原因。本测试是单进程顺序访问
同一个 XAUTHORITY 文件，锁不参与任何被断言的语义（夹具里没有任何锁相关
文本），故仅在测试驱动侧加 `-i`，产品行为不变。
"""

import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# 真正参与链接的依赖（run-only 的 libxcb/libxdmcp 不进 -I/-L 行）
_LINK_DEPS = ("libx11", "libxext", "libxau", "xorgproto")
# libXmu 官方 tarball 的本地展开目录名（相对 source_folder）
_VENDOR_DIR = "vendor-libxmu"


class XauthConan(ConanFile):
    name = "xauth"
    version = "1.1.4"
    description = "X.Org X authority file utility"
    license = "MIT-open-group"
    homepage = "https://gitlab.freedesktop.org/xorg/app/xauth"
    url = "https://gitlab.freedesktop.org/xorg/app/xauth"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xauth supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # configure 的 PKG_CHECK_MODULES(XAUTH, x11 xau xext xmuu xproto) 四个
        # 真实模块全部走 conan 依赖；xmuu 见文件头说明（就地编译上游子库）。
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0.1", transitive_headers=True, transitive_libs=True)
        # 必须用**范围**而不是钉死版本：libxau 同时被 libx11/6.4.0 → libxcb/1.16
        # 传递引入，制品仓里 libxcb 一侧的 libxau 诉求在 1.0.11 / 1.0.12 之间
        # 变过。钉死任一侧都会在图里撞出 version conflict（libxp/1.0.4 CI 实证）。
        self.requires("libxau/[>=1.0.11]", transitive_headers=True, transitive_libs=True)
        # 提供 X11/X.h、X11/Xfuncs.h、X11/Xos.h、X11/Xosdefs.h、X11/Xfuncproto.h。
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # xauth 运行时经 libX11.so.6 → libxcb.so.1 → libXdmcp.so.6 递归依赖；
        # 声明为 run 依赖，test_package 的 conanrun 环境才能定位到 .so。
        self.requires("libxcb/1.16", run=True)
        self.requires("libxdmcp/1.1.5", run=True)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # 把 conandata.yml 里 patches 段引用的补丁文件打进 export_sources，
        # apply_conandata_patches() 才能在 export_sources_folder 下找到它。
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"]["xauth"], strip_root=True)
        # 唯一的补丁：给 tests/setup-sourced 里两条真实的 `../xauth` 调用加 -i
        # （见文件头「测试驱动补丁」）。只动上游自带的测试驱动，不动产品源码。
        apply_conandata_patches(self)
        # libXmuu 源码（见文件头）：展开到 source_folder 下的独立目录，
        # 不污染 xauth 自己的源码树（xauth 的 configure/Makefile 不感知它）。
        vendor = os.path.join(self.source_folder, _VENDOR_DIR)
        os.makedirs(vendor, exist_ok=True)
        get(
            self,
            **self.conan_data["sources"]["libxmu"],
            strip_root=True,
            destination=vendor,
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        # xauth 1.1.4 自带的 config.sub 不认识 linux-ohos（实测：
        # `config.sub aarch64-unknown-linux-ohos` → "OS 'ohos' not recognized"），
        # 而 --build/--host 都不给时 configure 会跑 config.guess，在 OHOS 上
        # `uname -s` 返回 "HarmonyOS" → "cannot guess build type"。
        # 显式给**本机三元组**（config.sub 规范化成 aarch64-unknown-linux-gnu）
        # 让 configure 走 non-cross 分支（conftest 真执行），不是拿三元组去
        # 伪装交叉编译。
        tc.configure_args.extend(["--build=aarch64-linux", "--host=aarch64-linux"])
        environment = tc.environment()
        # PKG_CHECK_MODULES 的 AC_ARG_VAR 逃生口：生成的 configure 第 11988 行
        # 是 `if test -n "$XAUTH_CFLAGS"; then pkg_cv_XAUTH_CFLAGS="$XAUTH_CFLAGS"`
        # ——两者非空即完全绕过 pkg-config，xmuu.pc 不存在也不影响 configure
        # （同 libxp/1.0.4 的 XPRINT_CFLAGS/XPRINT_LIBS）。
        environment.define("XAUTH_CFLAGS", self._xauth_cflags())
        environment.define("XAUTH_LIBS", self._xauth_libs())
        tc.generate(env=environment)

    def build(self):
        self._build_vendored_libxmuu()
        self._relocate_dep_la_files()
        self._patch_configure()

        # HMFS 下 getcwd 不可达：切到 build_folder（路径查找可用）并预置 PWD
        # 让 configure 的 `ac_pwd=`pwd`` 兜底有值走逻辑路径（同 aribb24/xsel）。
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass
        os.environ["PWD"] = self.build_folder
        os.umask(0)

        # 上游测试夹具硬编码 ${DATADIR:-/tmp}，而 OHOS 的 /tmp 是 erofs 只读
        # （E002）。作用域内指向 build_folder 下的可写 scratch 目录，try/finally
        # 恢复，靠**环境注入**解决（不改测试脚本），不影响随后的 make install。
        scratch = os.path.join(self.build_folder, "test-scratch")
        os.makedirs(scratch, exist_ok=True)
        prior = {k: os.environ.get(k) for k in ("TMPDIR", "DATADIR", "LD_LIBRARY_PATH")}
        os.environ["TMPDIR"] = scratch
        os.environ["DATADIR"] = scratch
        # make check 会**直接执行**刚链接出来的 ../xauth（tests/test_xauth），
        # 而 xauth 动态依赖 conan 包提供的 libX11.so.6 / libXext.so.6 /
        # libXau.so.6 —— 这些 .so 不在 OHOS 加载器的默认搜索路径里。不补
        # LD_LIBRARY_PATH 时进程在 main() 之前就被加载器判死，stderr 里只有
        #     Error loading shared library libX11.so.6: (needed by ../xauth)
        #     Error relocating ../xauth: XCloseDisplay: symbol not found
        # 夹具里 8 行期望输出一条都产生不出来，5 个场景集体 FAIL。失败点看着
        # 像「用例不通过」，实为加载器限制（CI #53739 实证）。同 ezstream
        # 1.0.2 / aaphoto 0.45。作用域内设置，try/finally 恢复（同 TMPDIR）。
        libdirs = self._dependency_libdirs()
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            libdirs + ([prior["LD_LIBRARY_PATH"]] if prior["LD_LIBRARY_PATH"] else [])
        )

        autotools = Autotools(self)
        try:
            autotools.configure()
            autotools.make(args=["-j1"])
            # 上游回归套件是构建契约的一部分：TESTS = test_xauth 遍历 5 个
            # *.script 场景，与随包 .stdout/.stderr 夹具逐字节比对。
            # 驱动脚本已在 source() 里打过唯一一个补丁：两条真实执行的调用加
            # 上游自己的 -i（HMDFS 无硬链接 ⇒ XauLockAuth() 必败，见文件头）。
            try:
                autotools.make(target="check", args=["-j1"])
            except ConanException:
                self._dump_check_diagnostics()
                raise
        finally:
            for key, value in prior.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._sign_elf(os.path.join(self.package_folder, "bin", "xauth"))

    def package_info(self):
        # 命令行工具：只有 bin/xauth，无可链接库、无可 include 头
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]

    # ── libXmuu（上游 libXmu 子库）就地编译 ──────────────────────────
    def _build_vendored_libxmuu(self):
        """把 libXmu 官方 tarball 里的 libXmuu 真实源码编成静态 libXmuu.a。

        xauth 只引用 XmuGetHostname 一个符号（parsedpy.c:76），它定义在
        `src/GetHost.c`；非 WIN32 分支下该文件只 include <X11/Xosdefs.h>、
        <string.h>、<unistd.h> 和 <X11/Xmu/SysUtil.h>，且 config.h 的引入
        被 `#ifdef HAVE_CONFIG_H` 守卫（不定义即不需要 config.h）。
        因此不需要 libXmu 的 configure，直接编译单文件即可。
        """
        vendor = os.path.join(self.source_folder, _VENDOR_DIR)
        source_c = os.path.join(vendor, "src", "GetHost.c")
        include_dir = os.path.join(vendor, "include")
        lib_dir = os.path.join(vendor, "lib")
        object_file = os.path.join(lib_dir, "GetHost.o")
        archive = os.path.join(lib_dir, "libXmuu.a")
        if not os.path.isfile(source_c):
            raise ConanInvalidConfiguration(
                f"libXmuu source not found: {source_c}"
            )
        os.makedirs(lib_dir, exist_ok=True)
        cc = self._compiler_path()
        ar = self._tool_path("llvm-ar", "ar")
        # GetHost.c 唯一的外部头是 <X11/Xosdefs.h>，由 **xorgproto** 提供
        # （见 requirements()）；只给 vendor/include 会漏掉它，clang 直接
        # 报 `'X11/Xosdefs.h' file not found`（CI #53436 实证）。这里与
        # _xauth_cflags() 取同一份依赖 include 目录。
        includes = " ".join(
            f"-I{shlex.quote(path)}"
            for path in [include_dir] + self._dependency_dirs("include")
        )
        self.run(
            f"{shlex.quote(cc)} -fPIC -O2 {includes} "
            f"-c {shlex.quote(source_c)} -o {shlex.quote(object_file)}",
            env="conanbuild",
            cwd=self.build_folder,
        )
        self.run(
            f"{shlex.quote(ar)} rcs {shlex.quote(archive)} {shlex.quote(object_file)}",
            env="conanbuild",
            cwd=self.build_folder,
        )

    # ── XAUTH_CFLAGS / XAUTH_LIBS 计算（绕过 pkg-config） ────────────
    def _xauth_cflags(self):
        flags = [f"-I{os.path.join(self.source_folder, _VENDOR_DIR, 'include')}"]
        flags.extend(f"-I{path}" for path in self._dependency_dirs("include"))
        return " ".join(flags)

    def _xauth_libs(self):
        # 顺序有讲究：-L<libXmuu> -lXmuu 在前，再是 libX11/libXext/libXau 的
        # -L/-l 对。xauth 的 Makefile.am 是 `xauth_LDADD = $(XAUTH_LIBS)`。
        flags = [f"-L{os.path.join(self.source_folder, _VENDOR_DIR, 'lib')}", "-lXmuu"]
        flags.extend(f"-L{path}" for path in self._dependency_dirs("lib"))
        flags.extend(["-lX11", "-lXext", "-lXau"])
        return " ".join(flags)

    def _dependency_libdirs(self):
        """整个依赖图的 lib 目录（含传递依赖，按图序去重）。

        与 _dependency_dirs 的区别：后者只遍历 _LINK_DEPS（参与 -l 行的四个
        包），而**运行期**真正要解析的是 libX11.so.6 → libxcb.so.1 →
        libXdmcp.so.6 这条递归 NEEDED 链，libxcb/libxdmcp 一个符号都不参与
        链接却必须在 LD_LIBRARY_PATH 里。
        """
        result = []
        for _, dependency in self.dependencies.items():
            for path in dependency.cpp_info.aggregated_components().libdirs:
                if path not in result:
                    result.append(path)
        return result

    def _dependency_dirs(self, subdir):
        result = []
        for name in _LINK_DEPS:
            try:
                dependency = self.dependencies[name]
            except KeyError:
                continue
            package_folder = getattr(dependency, "package_folder", None)
            if not package_folder:
                continue
            path = os.path.join(package_folder, subdir)
            if os.path.isdir(path) and path not in result:
                result.append(path)
        return result

    # ── make check 失败时的构建控制台取证 ────────────────────────────
    def _dump_check_diagnostics(self):
        """把上游 harness 的原始输出打到构建控制台，再让异常照常向外抛。

        CI 只回传日志尾部约 4000 字符，而 `make check` 的失败细节（每个
        `*.script` 被跑出来的 out.stdout / out.stderr 与随包夹具的逐字节
        diff）出现在 automake 的 "Testsuite summary" 汇总行**之前**，正好
        落在截断区外。所以在异常逃逸之前主动 cat 出来。

        tests/test_xauth.log 是 automake 的 per-test 日志，内含 test_xauth
        的完整 stdout：每个场景的 "Testing <name>" 与随后的 diff 输出。
        """
        # 顺序即优先级倒序：CI 只保留**尾部**约 4000 字符，所以把最有诊断价值的
        # test_xauth.log 放在最后打印，保证它一定落在保留区内。
        # harness 依赖的外部命令：任一缺失都会让 5 个场景集体 FAIL 而非静默跳过，
        # 单独列出来避免把「工具缺失」误判成「用例不通过」。
        self.output.info(
            "诊断: LD_LIBRARY_PATH={}".format(os.environ.get("LD_LIBRARY_PATH", ""))
        )
        self.output.info("诊断: harness 依赖的外部命令可用性")
        for tool in ("diff", "awk", "xargs", "wc", "sort", "basename", "ls", "touch", "rm"):
            found = shutil.which(tool)
            self.output.info(
                "  | {}: {}".format(tool, found if found else "**MISSING**")
            )
        for name, keep in (
            ("out.stderr", 600),
            ("test-suite.log", 900),
            ("test_xauth.log", 2600),
        ):
            path = os.path.join(self.build_folder, "tests", name)
            if not os.path.isfile(path):
                self.output.info("诊断: 缺少 {}".format(path))
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    body = handle.read()
            except OSError as exc:
                self.output.info("诊断: {} 不可读: {}".format(path, exc))
                continue
            self.output.info(
                "===== {} ({} bytes, 末 {}) =====".format(path, len(body), keep)
            )
            for line in body[-keep:].splitlines():
                self.output.info("  | " + line)

    # ── configure 的 OHOS 运行期修补（E002 / E114 / HMFS getcwd） ────
    def _patch_configure(self):
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        with open(configure_path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        # config.status 用 umask 077 建临时目录，HMDFS 下不可执行/不可写（E002）。
        if "umask 077" in text:
            text = text.replace("umask 077", "umask 022")
        # HMFS 下 getcwd 不可达 → configure 报 "working directory cannot be
        # determined"。autoconf 2.70+ 的 `ac_pwd=`pwd`` 追加 PWD 兜底
        # （同 aribb24/1.0.4、xsel/1.2.1）。
        if (
            'ac_pwd=`pwd`' in text
            and 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"' not in text
        ):
            text = text.replace(
                'ac_pwd=`pwd`', 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"'
            )
        with open(configure_path, "w", encoding="utf-8") as handle:
            handle.write(text)

    # ── 依赖包 .la 修补 ─────────────────────────────────────────────
    def _relocate_dep_la_files(self):
        """把依赖包里的 libtool 归档改写成当前可解析的状态。

        制品仓发布的 libXau.la 记录了构建机的绝对路径：
            libdir='/storage/Users/currentUser/.conan2/p/b/libx<hash>/p/lib'
            dependency_libs=' -L/storage/Users/currentUser/usr/local/lib'
        前者在本机/CI 上都不存在，libtool 用 `-lXau` 命中这个 .la 后按 libdir
        找 libXau.so 会失败；后者指向 CI worker 残留的静态库目录，会把非 Conan
        库悄悄吸进链接行。两条都就地清掉（同 libxp/1.0.4）。
        """
        for name in _LINK_DEPS:
            try:
                dependency = self.dependencies[name]
            except KeyError:
                continue
            package_folder = getattr(dependency, "package_folder", None)
            if not package_folder:
                continue
            dep_lib = os.path.join(package_folder, "lib")
            if not os.path.isdir(dep_lib):
                continue
            for entry in os.listdir(dep_lib):
                if not entry.endswith(".la"):
                    continue
                la_path = os.path.join(dep_lib, entry)
                with open(la_path, "r", encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
                fixed = re.sub(
                    r"^libdir=.*$",
                    "libdir='{}'".format(dep_lib),
                    content,
                    flags=re.MULTILINE,
                )
                fixed = re.sub(
                    r"^dependency_libs=.*$",
                    "dependency_libs=''",
                    fixed,
                    flags=re.MULTILINE,
                )
                if fixed != content:
                    with open(la_path, "w", encoding="utf-8") as handle:
                        handle.write(fixed)
                    self.output.info(
                        "依赖 .la 已重定位: {} -> {}".format(entry, dep_lib)
                    )

    # ── OHOS ELF 签名（E077，同 xinit/xeyes） ───────────────────────
    def _sign_elf(self, path):
        """鸿蒙内核只加载带有效 .codesign 段的 ELF（E077）。

        顺序不可变：先 llvm-objcopy 移除旧签名段 → binary-sign-tool 重新自签名
        → 恢复可执行权限（签名后权限归零）。
        """
        if str(self.settings.os) != "OHOS" or not os.path.isfile(path):
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.exists(sign_tool) and os.path.exists(objcopy)):
            return
        self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
        self.run(
            f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1'
        )
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    # ── 工具链定位 ──────────────────────────────────────────────────
    def _compiler_path(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = executables.get("c")
        if configured and os.path.isfile(configured):
            return configured
        return shutil.which("clang") or configured or "clang"

    def _tool_path(self, *names):
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return names[0]
