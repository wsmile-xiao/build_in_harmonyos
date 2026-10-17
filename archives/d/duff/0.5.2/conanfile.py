#!/usr/bin/env python3
"""Conan recipe for duff 0.5.2 — duplicate file finder (Autotools CLI tool).

包版本 = 上游版本 0.5.2（R37：首次适配不加修订后缀）。源码 URL/sha256 与上游 tag 一致；
适配要点：启用 NLS（而非 --disable-nls）、不使用 --build/--host 三元组（改补 config.guess/sub）。

duff 是命令行重复文件查找工具：递归扫描给定路径，先按文件大小分桶，再抽样
比较，最后用 sha1/sha256/sha384/sha512 摘要（或逐字节比较）确认，按簇输出
重复文件及其摘要。

源码形态
--------
官方发布 tarball 由 SourceForge 托管（http://duff.sourceforge.net/，本环境
不可达），这里使用上游作者仓库的 tag 快照。该快照**不含** configure /
Makefile.in / build-aux/* / po/Makefile.in.in，也没有 m4 宏（m4/ 下只有
ChangeLog），因此 build() 按上游 README「3. Building Duff」的说明自行引导。

OHOS 适配（build() 内 4 处修改 + patches/0001）
-----------------------------------------------
1. **autotools 引导**：tool_requires 的 automake/gettext 提供
   aclocal / automake / xgettext / msgfmt，以及 AM_GNU_GETTEXT 需要的 m4 宏与
   po/ 基础设施（autoconf/autoreconf/autoheader 用镜像自带版本，理由见
   build_requirements）。gettext 包内的 autopoint/gettextize 以 prefix="/"
   构建（gettext_datadir 解析为 "//share/gettext"），configure.ac 也没有
   AM_GNU_GETTEXT_VERSION，两者都不可用；故沿用仓内 authselect / libzbar /
   centerim5 的做法：ACLOCAL_PATH 指向 <gettext>/share/aclocal +
   AUTOPOINT=true 跳过坏工具，并把 autopoint 本应安装的 po/ 文件、
   build-aux/config.rpath、ABOUT-NLS 从 gettext 包复制进源码树。
2. **E007 config.guess/config.sub**：GNU config.guess(2024-07-27) 没有
   HarmonyOS 分支（uname -s = "HarmonyOS"），configure 第一阶段即失败：
   "cannot guess build type; you must specify one"。在 autoreconf 之后补
   `*:HarmonyOS:*:*)` case 分支与 __OHOS__ libc 探测（R1：不用
   --build/--host 伪造三元组绕过）。
3. **E114 configure 临时目录**：`(umask 077 && mktemp -d "./confXXXXXX")` 在
   HMDFS 上生成 drwx--S--- 目录，config.status 写 subs1.awk 报
   "Permission denied → could not setup config files machinery"。在
   autoreconf 之后去掉该 umask 077（mktemp 与 mkdir 两条路径同属一类缺陷）。
4. **NLS**：OHOS（musl）libc 不提供 libintl——sysroot 的 libintl.h 无任何函数
   声明、libc.so 无 gettext/textdomain 符号、无 libintl.a/.so——configure 会把
   USE_NLS 静默判为 no，译文全部丢失（功能退化）。gettext/0.22.5.1 作为 host
   依赖提供 libintl.h + libintl.so，经 AutotoolsDeps 注入后 configure 判定
   "GNU gettext in libintl... yes / whether to use NLS... yes"，en / en@quot /
   en@boldquot / sv 四个语言目录随包安装到 share/locale。
5. **patches/0001-po-Makevars.patch**：po/LINGUAS 声明了 en@quot 与
   en@boldquot，其 .gmo 由 gettext 的 quot 规则（po/Rules-quot）生成，必须在
   po/Makevars 中 `include $(srcdir)/Rules-quot`；上游树缺这一行，po/ 里
   `make` 会报 "File en@boldquot.po does not exist"。

上游测试
--------
上游**没有**自动化测试套件：无 tests/ 目录，Makefile.am 中无 TESTS /
check_PROGRAMS 注册，`make check` 无事可做。唯一可执行的上游测试入口是
README.SHA:126-133 声明的编译期自测宏 `-DSHA{1,256,384,512}_TEST`
（4 算法 × 3 条 NIST 样例向量）。test_package/test_duff.sh 另做消费者端到端
验证（真实执行包内安装的 duff 二进制）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, load,
                               replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DuffConan(ConanFile):
    name = "duff"
    version = "0.5.2"
    description = "duff - a command-line utility for finding duplicate files"
    license = "Zlib"
    homepage = "http://duff.sourceforge.net/"
    url = "https://github.com/elmindreda/duff"

    # CLI 工具（R38：软件级 commands.json 已声明 duff/0.5.2）
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # ------------------------------------------------------------------ 源码
    def export_sources(self):
        export_conandata_patches(self)

    # -------------------------------------------------------------- 依赖声明
    def requirements(self):
        # OHOS musl libc 不提供 libintl：gettext 提供 libintl.h + libintl.so，
        # 使 configure 的 AM_GNU_GETTEXT([external]) 判定 USE_NLS=yes。
        self.requires("gettext/0.22.5.1")

    def build_requirements(self):
        # Git 快照无 configure：需要 automake(aclocal/automake) + gettext
        # （m4 宏 / po 基础设施 / xgettext / msgfmt / msginit）+ m4。
        # 不声明 autoconf/2.72：其传递依赖 perl/5.42.2 会注入 PERL5LIB，
        # 而 autoreconf 是系统 perl 脚本（/data/service/hnp/bin/autoreconf），
        # 加载 conan perl 的 Cwd.so 会因 ABI 不匹配而中止
        # （"Perl_my_cxt_init: symbol not found"，rc=255）。
        # OHOS 镜像自带 autoconf/autoreconf/autoheader（check-env 已核验 2.72）。
        self.tool_requires("automake/1.18")
        self.tool_requires("gettext/0.22.5.1")
        self.tool_requires("m4/1.4.19")

    # ------------------------------------------------------------------ 布局
    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        # gettext 包的 cpp_info.libs 声明了 intl/gettextpo/asprintf/textstyle，
        # 但包内**没有** libasprintf（lib/ 下无 libasprintf.a/.so），于是 configure
        # 的 conftest 链接行出现 `-lasprintf` 直接失败：
        #   ld.lld: error: unable to find library -lasprintf
        #   configure: error: C compiler cannot create executables
        # duff 只需要 libintl（src/Makefile.am: duff_LDADD = @LIBINTL@），
        # 因此把 LIBS 收敛为 -lintl。
        deps.environment.define("LIBS", ["-lintl"])
        deps.generate()
        AutotoolsToolchain(self).generate()

    # ------------------------------------------------------------------ 构建
    def build(self):
        apply_conandata_patches(self)
        self._seed_gettext_infrastructure()
        self._run_autoreconf()
        self._fix_config_guess()
        self._fix_config_sub()
        self._fix_configure_umask()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

    # ---------------------------------------------------------------- helpers
    def _gettext_folder(self):
        """tool_requires 的 gettext 包目录（m4 宏 / po 基础设施 / 构建工具）。"""
        folder = self.dependencies.build["gettext"].package_folder
        if not folder:
            raise ConanException("gettext tool package folder not available")
        return folder

    def _seed_gettext_infrastructure(self):
        """复制 autopoint 本应安装的文件。

        gettext 包内的 autopoint/gettextize 以 prefix="/" 构建，gettext_datadir
        解析成 "//share/gettext" 不可用，且 configure.ac 没有
        AM_GNU_GETTEXT_VERSION（autopoint 拒绝执行）。这里直接把 gettext 包
        share/gettext 下的基础设施文件放进源码树，效果与 autopoint 一致。
        """
        gettext = self._gettext_folder()
        gettext_share = os.path.join(gettext, "share", "gettext")
        po_share = os.path.join(gettext_share, "po")

        # po/：AM_GNU_GETTEXT 需要的 Makefile.in.in 与 en@quot/en@boldquot 规则
        po_files = ("Makefile.in.in", "Rules-quot", "quot.sed", "boldquot.sed",
                    "en@quot.header", "en@boldquot.header", "insert-header.sin",
                    "remove-potcdate.sin")
        for name in po_files:
            if not os.path.isfile(os.path.join(po_share, name)):
                raise ConanException(f"gettext po infrastructure missing: {name}")
            copy(self, name, src=po_share,
                 dst=os.path.join(self.source_folder, "po"))

        # build-aux/config.rpath 与 ABOUT-NLS 由 autopoint 安装
        for name in ("config.rpath", "ABOUT-NLS"):
            if not os.path.isfile(os.path.join(gettext_share, name)):
                raise ConanException(f"gettext infrastructure missing: {name}")
        copy(self, "config.rpath", src=gettext_share,
             dst=os.path.join(self.source_folder, "build-aux"))
        copy(self, "ABOUT-NLS", src=gettext_share, dst=self.source_folder)

    def _run_autoreconf(self):
        """引导 Git 快照的构建系统（上游 README「3. Building Duff」）。"""
        aclocal_path = os.path.join(self._gettext_folder(), "share", "aclocal")
        existing = os.environ.get("ACLOCAL_PATH", "")
        env_vars = [aclocal_path] + ([existing] if existing else [])
        self.run(
            'ACLOCAL_PATH="{}" AUTOPOINT=true autoreconf -fi'.format(
                os.pathsep.join(env_vars)),
            cwd=self.source_folder,
        )

    def _fix_config_guess(self):
        """E007：让 config.guess 认识 HarmonyOS（uname -s = "HarmonyOS"）。

        缺这一分支时 configure 第一阶段即中断：
        "cannot guess build type; you must specify one"（R1：不用 --build/--host
        伪造三元组绕过）。config.guess 的 case 分支非互斥且按顺序匹配，因此新
        分支必须插在 case 的第一条。
        """
        path = os.path.join(self.source_folder, "build-aux", "config.guess")
        if "HarmonyOS" in load(self, path):
            return

        # 1) libc 探测：OHOS 使用 musl（紧跟 __ANDROID__ 分支）
        libc_android = "\t#if defined(__ANDROID__)\n\tLIBC=android"
        replace_in_file(self, path, libc_android,
                        libc_android + "\n#elif defined(__OHOS__)\n    LIBC=ohos")

        # 2) HarmonyOS 系统识别分支
        case_head = ("case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:"
                     "$UNAME_VERSION in\n")
        replace_in_file(self, path, case_head, case_head + (
            "    *:HarmonyOS:*:*)\n"
            "\tcase \"$UNAME_MACHINE\" in\n"
            "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
            "\t    armv7*|armv8*) MACHINE=arm ;;\n"
            "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
            "\t    i?86)         MACHINE=i686 ;;\n"
            "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
            "\tesac\n"
            "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
            "\t;;\n\n"))

    def _fix_config_sub(self):
        """E007：让 config.sub 接受 ohos-linux 三元组。"""
        path = os.path.join(self.source_folder, "build-aux", "config.sub")
        if "ohos-linux" in load(self, path):
            return
        android_case = ("\t\t\t\tbasic_machine=$field1-unknown\n"
                        "\t\t\t\tbasic_os=linux-android\n"
                        "\t\t\t\t;;\n")
        replace_in_file(self, path, android_case, android_case + (
            "\tohos-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tbasic_os=linux-ohos\n"
            "\t\t\t\t;;\n"))

    def _fix_configure_umask(self):
        """E114：config.status 的临时目录在 HMDFS 上必须可写。

        `(umask 077 && mktemp -d "./confXXXXXX")` 会建出 drwx--S--- 目录，
        config.status 随后写 subs1.awk 报 "Permission denied"，configure 以
        "could not setup config files machinery" 中断。mktemp 与 mkdir 回退
        两条路径同属一类缺陷，一并去掉 umask 077。
        """
        path = os.path.join(self.source_folder, "configure")
        if "umask 077" not in load(self, path):
            return
        replace_in_file(self, path, "umask 077 && mktemp", "mktemp")
        replace_in_file(self, path, "umask 077 && mkdir", "mkdir")
