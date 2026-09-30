#!/usr/bin/env python3
"""Conan recipe for linuxinfo 4.2.3 — 读 /proc + uname(2) 的鸿蒙 PC 系统信息命令行工具。

上游 Peter Deakin 创建、Alex Buell 首发，2014 年起由 Helge Kreutzmann
(debian@helgefjell.de) 维护；官方发布物挂在 helgefjell.de 自己的 data/ 目录下
（见 conandata.yml 的采样证据），既不在 GitHub 也没有 git 仓库镜像。

依赖结论（W0，逐条实测，详见 notes.md）
--------------------------------------
**无 requires。** Debian 的 Build-Depends 里那两项都不是必需项：

* ``libpcre2-dev`` —— 上游 ``m4/pcre.m4`` 的 ``AC_ARG_WITH(pcre, ...)`` 缺省分支
  就是 ``with_pcre=no``；实测 ``./configure`` 输出 ``checking for --with-pcre... no``
  且生成的 ``Makefile`` 里 ``PCRE_LINK = `` 为空。它只在 x86 的 ``regstrcmp()``
  分支被用到，aarch64 走 ``linuxinfo_arm.c`` 的 ``CPU implementer`` 静态查表。
  Debian 自己也把 ``libpcre2-dev`` 限死成 ``[i386] [amd64] [x32]``（arm64 不拉）。
  仓内虽已发布 pcre2/10.40~10.48，本包用不上，**不引入**。
* ``po4a`` —— 只用来把 ``po4a/linuxinfo.1`` 翻成多语言 man。官方件里
  ``po4a/linuxinfo.1`` **已随包发好**，``LINUXINFO_PROG_PO4A`` 找不到 po4a 时
  把 ``USE_PO4A`` 置 ``no``，实测生成的 ``po4a/Makefile`` 里退化成空目标
  ``all-local-no:``。man 页安装走 ``man_MANS`` 不受影响。配方再加
  ``--disable-nls`` 把 ``USE_NLS``/``LIBINTL`` 一并钉成 ``no``/空，
  ``po/`` 子目录不再需要 msgfmt —— 不给它"伪装成 required"的机会。

OHOS 适配点（patches/ 与 conandata.yml 1:1）
-------------------------------------------
1. ``0001-configure-umask.patch`` — E011/E114/E118 家族：``config.status`` 用
   ``(umask 077 && mktemp -d ./confXXXXXX)`` 建私有临时目录，HMDFS 的 UID 映射
   + 继承来的 setgid 位把它落成 ``drwx--S---``，**属主自己都不能在里面建文件**，
   于是 ``echo 'BEGIN {' >"$ac_tmp/subs1.awk"`` 直接 ``Permission denied``，
   configure 死于 ``could not setup config files machinery``。
2. ``0002-linuxinfo_common-libc-version-probe.patch`` — ``GetSystemLibcInfo()``
   探测 ``gnu_get_libc_version``/``__libc_version``/``__linux_C_lib_version`` 三个
   glibc 专有符号。**接力棒实测加强过**：起草棒版只补了末支空指针守卫，但上游用
   ``asm (".weak sym")`` 声明弱符号，clang 15（OHOS SDK）不认为这是 weak ⇒ 把
   ``if (gnu_get_libc_version != 0)`` 折叠成恒真，反汇编实证 ``main`` 的**第一条指令**
   就是 ``bl gnu_get_libc_version@plt``（无任何 compare）；OHOS 是 musl，实测
   ``nm -D /lib/ld-musl-aarch64.so.1`` 的 1954 个动态符号里这三个 **0 命中**，
   PLT 槽解析为 0 ⇒ 起手即 SIGSEGV(139)（首轮 test_package 实测 TC-03/TC-05 全 139）。
   ⇒ 改成真正的 ``__attribute__((weak))`` 声明，clang 会保留运行期空指针判定，
   走该函数本来就写好的 ``"Unknown"`` 默认值；glibc 上三符号全解析，行为不变。
   守卫本身保留（末支读地址 0 依然是真 bug）。
3. ``0003-linuxinfo-nls-identity-fallback.patch``（接力棒首轮 ``conan create`` 实测新增）
   — ``--disable-nls`` 让 ``m4/gettext.m4`` 不再 ``AC_DEFINE([ENABLE_NLS])``（本包无
   ``config.h``，AC_DEFINE 全走 ``DEFS``，实测生成的 ``DEFS`` 里确实没有 ``-DENABLE_NLS``），
   而 ``linuxinfo.c`` / ``linuxinfo_common.c`` **无条件** ``#include <libintl.h>`` 并直调
   ``gettext()``/``ngettext()``/``bindtextdomain()``/``textdomain()``。OHOS sysroot 的
   ``libintl.h``（353 B）只留 ``__USE_GNU_GETTEXT``/``__GNU_GETTEXT_SUPPORTED_REVISION``
   两个宏、**零函数声明** ⇒ 六个调用全成隐式 ``int`` 声明，OHOS clang 把
   ``-Wint-conversion`` 当 **error**（首轮实测 13 warnings + 10 errors，
   ``Makefile:540: linuxinfo.o`` Error 1）；另 ``setlocale``/``LC_ALL``/``LC_NUMERIC``
   在上游只靠 glibc 的传递包含拿到，musl 下必须显式 ``#include <locale.h>``。
   ⇒ 按 ``ENABLE_NLS`` 加分支：定义了就走原路 ``<libintl.h>``（glibc+NLS 行为逐字节不变），
   没定义就用 GNU gettext 文档里 ``--disable-nls`` 的恒等翻译回退。**不含任何平台宏**。
   在案件：``knowledge/drafts/DRAFT-latino-1.4.4-musl-empty-libintl-bison-dgettext``
   （musl 空壳 ``libintl.h`` 同机制），邻近图条目 E015/E027/E508。
4. ``0004-linuxinfo_common-splitstring-return-value.patch``（接力棒第二轮实测新增）
   — ``splitstring()`` 声明返回 ``int``、每个调用方都拿它当"这行有 ``key:value``"的
   布尔用，但函数体末尾**没有 return**（上游 UB，``-Wreturn-type`` 有告警）。glibc 上
   靠尾调用 ``strcpy`` 把非空指针留在 w0 里侥幸为真；``build_type=Release`` 的 clang
   -O3 利用这条 UB 后调用方恒见 0 ⇒ ``GetHardwareInfo()`` 与 ``getphysicalmemory()``
   **静默不解析任何东西**，而进程仍 rc=0。同一批 DEFS 只差 -O 级的 A/B 实测：
   ``-O3`` 未打本枚 → ``Unknown Unknown processors, ? total bogomips, 0M RAM``；
   ``-O0`` → ``Three ARM v7 instruction set 528MHz processors, 2001.00 total bogomips,
   31914M RAM``；``-O3`` + 本枚 → 与 -O0 逐字相同。⇒ 补显式 ``return 1;``。
   ⚠ 这条在仓内知识图/drafts 里查不到先例，是本包唯一可能升路径 B 的新机制
   （判定与 Issue/标题前缀归主窗，见 notes.md §8）。

平台三元组：上游 ``config.guess``（快照 2024-07-27）不认 ``uname -s`` 返回的
``HarmonyOS``，裸跑 ``./configure`` 会 ``cannot guess build type; you must
specify one``；而 ``config.sub``（2024-05-27）**已经**认 ``ohos`` 后缀
（实测 ``aarch64-linux-ohos`` → ``aarch64-unknown-linux-ohos``，rc=0）。
⇒ 显式喂 ``--build/--host`` 就够，不动 config.guess/config.sub（R21）。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
# ⚠ 必须走子模块全路径：conan 2.29.1 的 conan/tools/gnu/__init__.py **不**再导出
#   get_gnu_triplet，`from conan.tools.gnu import get_gnu_triplet` 拿到的是同名**子模块**
#   对象，调用时炸 `TypeError: 'module' object is not callable`（本包首轮 conan create
#   真实死于此处，generate() line 99）。仓内先例同法：archives/b/binutils/2.46.0、
#   archives/a/avr-libc/2.2.1 都是 `from conan.tools.gnu.get_gnu_triplet import _get_gnu_triplet`。
from conan.tools.gnu.get_gnu_triplet import _get_gnu_triplet
from conan.tools.layout import basic_layout


class LinuxinfoConan(ConanFile):
    name = "linuxinfo"
    version = "4.2.3"
    description = ("Print a one-line summary of the running system by parsing "
                   "/proc/cpuinfo, /proc/meminfo and uname(2)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.helgefjell.de/linuxinfo.php"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 只产出 bin/linuxinfo，不产出 .a/.so（Makefile.am: bin_PROGRAMS = linuxinfo）
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0：pcre2 / po4a 均经实测确认非必需（见模块 docstring），故本包零依赖。
        # 若将来要开 --with-pcre，必须先按 R36 确认 pcre2 已发布再在此处 requires。
        pass

    def validate(self):
        # R32: os 判定必须 in ("Linux", "OHOS")，不能 == "Linux"
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"linuxinfo parses Linux-style /proc; unsupported on "
                f"{self.settings.os}")
        # 本配方只在 AArch64 上实测过（linuxinfo_arm.c 分支）。
        # 上游另有 intel/sparc/mips... 共 15 个 arch 分支，但 x86 那条会额外
        # 牵出 pcre2（--with-pcre），不在本版本验证范围内。
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                f"linuxinfo/{self.version} is validated on AArch64 (armv8) only, "
                f"got {self.settings.arch}")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        # 官方货源 + sha256 只认 conandata.yml 这一处（单一真相源）
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)

        # config.guess 认不出 HarmonyOS，但 config.sub 认 ohos 后缀 ⇒ 显式喂三元组，
        # 不替换也不补丁 config.guess/config.sub。
        # OHOS → "linux-ohos"、armv8 → "aarch64" ⇒ triplet = aarch64-linux-ohos
        # （与 config.sub 实测 `aarch64-linux-ohos` → `aarch64-unknown-linux-ohos` 同一条链）
        triplet = _get_gnu_triplet(str(self.settings.os), str(self.settings.arch))["triplet"]
        tc.configure_args.append(f"--build={triplet}")
        tc.configure_args.append(f"--host={triplet}")

        # 把文档/翻译链钉成确定性形态：
        # USE_NLS=no -> USE_PO4A=no、LIBINTL/LTLIBINTL 空、po/ 不再要 msgfmt。
        # 实测生成 Makefile: USE_NLS = no / USE_PO4A = no / LIBINTL = / PCRE_LINK =
        tc.configure_args.append("--disable-nls")

        # R1 参数最少化：不额外加 --sysconfdir/--libdir/--with-pcre；
        # prefix 由 AutotoolsToolchain 指到 package_folder，make install 落 bin/linuxinfo。
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # R9：并发 make 会踩 HMDFS jobserver fifo EPERM（E074）；
        # 本包只有 17 个 .c，串行开销可忽略。
        # 上游无 check 目标（test_package/MANIFEST.yml 附逐条清点命中数）。
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 独立可执行文件，无 C/C++ 消费面（R34 的实质验证在 test_package/test.sh）
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
