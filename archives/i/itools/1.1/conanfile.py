#!/usr/bin/env python3
"""Conan recipe for itools 1.1 (ical / idate / ipraytime / ireminder).

autotools 包，官方 tarball 不带 configure（README 口径是 autoreconf -f -i），但本配方
**不在构建期 bootstrap**：configure 及辅助件预生成后随包放在 generated/ 导出（见下）。
上游零测试入口（N_static=0，双法复核见 notes.md），package_type=application。
依赖 libitl/0.8.0：官方制品仓已发布二进制包，实物头布局为
<pkg>/include/itl/{hijri,prayer,astro}.h，与本品 `#include <itl/...>` 前缀一致。

真机实测决定的三处非显然写法（详见 notes.md §3/§4）：
  * configure.ac:12 注释掉了 AC_PROG_INSTALL，但 aclocal.m4:439 证明
    AM_INIT_AUTOMAKE 自身 AC_REQUIRE([AC_PROG_INSTALL]) ⇒ 占位符照常替换，
    **不需要任何补丁**（sct 的疑点已证伪）。
  * 生成 configure 时，设备 aclocal 的搜索目录里没有 pkg.m4，而 configure.ac 用了
    PKG_CHECK_MODULES ⇒ 原始宏文本会残留在生成的 configure 里（实测 configure:4658），
    执行即 `syntax error near unexpected token 'ITL,'`。所以随包这份必须由
    ACLOCAL_PATH 指向含 pkg.m4 的目录生成（本机已按此生成并核过 `sh -n` 通过）。
  * Makefile.am 的 LDADD 硬编码 "-litl -lm"，且不引用 @ITL_CFLAGS@/@ITL_LIBS@
    ⇒ PKG_CHECK_MODULES 探到的两个变量对本品毫无作用，头文件与库搜索路径只能
    由 -I/-L 通道提供；但不能因此用 AutotoolsDeps（它注入 LIBS 会打断 configure
    最早那个 run 探针，E467 实测），改走 extra_cflags/extra_ldflags。

CI 崩溃与修法（PR #12629 build 60809 首错逐字，方案 A）：
  worker 上有 hnp 的 autoconf 2.72（因此 autoreconf 本身能起），但**没有 aclocal**，
  于是构建期 autoreconf 必崩：`Can't exec "aclocal": No such file or directory at
  /data/service/hnp/autoconf.org/autoconf_2.72/share/autoconf/Autom4te/FileUtils.pm:299`
  ⇒ `autoreconf: error: aclocal failed with exit status: 2`。
  修法：configure 由本机（autoconf 2.72 + automake 1.17 + ACLOCAL_PATH 指向含 pkg.m4
  的目录）预生成，随配方放在 `generated/` 下并由 source() 还原进源码树，构建期不再跑
  任何 autotools bootstrap。这与已合入的 libxmi/1.2(compat/)、afflib/3.7.22(generated/)
  同一形态，理由同源（CI worker 缺 host automake/libtool）。
  ⚠ 一个已被复测推翻的旧判别：曾以为"configure 里 ac_fn_c_try_link 的定义必须排在调用
  之前"。复测（notes.md §6）显示只要 PKG_CHECK_MODULES 被 pkg.m4 正常展开，本机 1.17
  配对产出的也是 调用@1724 早于 定义@4828，而这份 configure 在设备上能跑通 W3
  ⇒ 顺序先后不是判据；未展开时 `sh -n configure` 直接在 4658 行报
  `syntax error: unexpected 'ITL,'`，那才是"宏没展开"的硬判据。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# 随配方导出的预生成 autotools  bootstrap 文件所在子目录（与 libxmi/1.2 compat/ 同法）
_PREGEN_DIR = "generated"
_PREGEN_FILES = ("configure", "config.h.in", "Makefile.in", "aclocal.m4",
                 "config.guess", "config.sub", "install-sh", "missing",
                 "compile", "depcomp", "INSTALL")

# E077：OHOS 本机未签名 ELF 不可执行，签名工具位置固定
_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"
_SIGNER = "/data/service/hnp/bin/binary-sign-tool"
# 本仓 profile [buildenv] 用的就是这个 bash（函数语义完整），配 PWD 预置才能跑 autoconf
_NATIVE_BASH = "/data/service/hnp/bin/bash"


def _prepare_autotools_env():
    """automake/aclocal/libtoolize 内部把 autoconf/autom4te/sed 的路径烧死成绝对
    路径，在 CI 沙箱里那些路径不存在 ⇒ 按 PATH 实测值回填（照抄已合入的
    abiword-plugin-* 配方写法）。"""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


class ItoolsConan(ConanFile):
    name = "itools"
    version = "1.1"
    description = (
        "Islamic tools built on the ITL library: ical (Hijri calendar grid), "
        "idate (Hijri/Gregorian converter), ipraytime (prayer times and Qibla) "
        "and the ireminder perl wrapper."
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/arabeyes-org/itools"
    url = "https://github.com/arabeyes-org/itools"
    topics = ("hijri", "prayer-times", "qibla", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    # 预生成的 autotools bootstrap 文件随配方导出（见模块 docstring 与 notes.md §6）
    exports = "%s/*" % _PREGEN_DIR

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "%s/*" % _PREGEN_DIR, self.recipe_folder,
             os.path.join(self.export_folder, _PREGEN_DIR))

    def requirements(self):
        self.requires("libitl/0.8.0")

    def build_requirements(self):
        # 故意**不**声明 tool_requires("autoconf/...") 或 tool_requires("automake/...")：
        # 本配方构建期不跑任何 autotools bootstrap（configure 由 source() 从随包导出的
        # generated/ 还原），所以既不需要 host aclocal，也不给 conan 版 automake 生成
        # configure 的机会。
        # 历史背景（#12629）：CI worker 有 hnp autoconf 2.72 但没有 aclocal，构建期
        # autoreconf 直接崩 `Can't exec "aclocal" ... aclocal failed with exit status: 2`；
        # 而曾试的 conan automake/1.18 配对另会在 configure 运行期崩
        # `ac_fn_c_try_link: command not found` → `cannot guess build type`。
        # 另注：把 conan 的 perl 模块混进 hnp perl（VirtualBuildEnv 的 PERL5LIB）会让
        # autoreconf 直接编译失败（`Cwd.so: Perl_my_cxt_init: symbol not found`）。
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("itools is packaged for Linux/OHOS")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("itools supports OHOS armv8 only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._restore_pregen()

    def _restore_pregen(self):
        """把随包导出的预生成 bootstrap 文件放回源码树（tarball 本身不含 configure）。

        与已合入的 libxmi/1.2 同一写法：`exports` 让文件落在缓存的 recipe_folder，
        而 export_sources 的落点在不同 conan 版本里位置不定，故按候选目录实测定位。
        """
        src = None
        for cand in (os.path.join(self.recipe_folder, _PREGEN_DIR),
                     os.path.join(self.export_sources_folder, _PREGEN_DIR),
                     os.path.join(os.path.dirname(self.recipe_folder), _PREGEN_DIR),
                     os.path.join(self.source_folder, _PREGEN_DIR)):
            if os.path.isdir(cand):
                src = cand
                break
        if src is None:
            raise ConanException(
                "pregen directory '%s' not found (looked in recipe_folder/"
                "export_sources_folder/source_folder): the shipped configure is "
                "required because this recipe deliberately runs no autotools "
                "bootstrap at build time." % _PREGEN_DIR)
        for name in _PREGEN_FILES:
            frm = os.path.join(src, name)
            if not os.path.isfile(frm):
                continue
            to = os.path.join(self.source_folder, name)
            shutil.copy2(frm, to)
        # E490/E543：HMDFS 上导出件没有执行位（默认 660），直接跑即 Permission denied
        self._restore_script_modes()
        missing = [n for n in ("configure", "Makefile.in", "config.h.in")
                   if not os.path.isfile(os.path.join(self.source_folder, n))]
        if missing:
            raise ConanException("pregen restore left %s missing in %s"
                                 % (missing, self.source_folder))

    def generate(self):
        _prepare_autotools_env()
        # libitl.pc 由 PkgConfigDeps 生成（libitl 配方设了 pkg_config_name），
        # 让 PKG_CHECK_MODULES 这一步真的能认出依赖；.pc 落在 generators_folder
        # 内（R49：私有目录，不污染共享 /usr/local）。
        PkgConfigDeps(self).generate()
        # **故意不用 AutotoolsDeps**（E467 实测）：它会把依赖的 -litl -lm 写进 LIBS，
        # 于是 autoconf 最早那个 run 探针（"whether we are cross compiling"）就无条件
        # 链接整条依赖闭包，而 libitl.so 的 LD_LIBRARY_PATH 属于 conanrun 不在构境内
        # ⇒ config.log 实锤：`./conftest` → `Error loading shared library libitl.so`
        # → `$? = 127` → `configure: error: cannot run C compiled programs`。
        # Makefile.am 的 LDADD 自带 -litl -lm，所以只需要 -I/-L 通道：走 extra_cflags/
        # extra_ldflags，不注入 LIBS。不改静态链接、不预设 cross_compiling、不加 --host
        # （三条都是 E467 明文禁止项）。
        tc = AutotoolsToolchain(self)
        dep = self.dependencies["libitl"]
        pkgdir = dep.package_folder
        for inc in dep.cpp_info.includedirs:
            if inc:
                tc.extra_cflags.append("-I{}".format(
                    inc if os.path.isabs(inc) else os.path.join(pkgdir, inc)))
        for lib in dep.cpp_info.libdirs:
            if lib:
                tc.extra_ldflags.append("-L{}".format(
                    lib if os.path.isabs(lib) else os.path.join(pkgdir, lib)))
        tc.configure_args.append("PKG_CONFIG_PATH={}".format(self.generators_folder))
        tc.generate()

    def _restore_script_modes(self):
        """E490：HMDFS 上 automake --copy 出来的 autotools 辅助脚本没有执行位
        （默认文件模式 660），直接执行即 Permission denied。按该条目 rec 恢复
        configure/config.guess/config.sub/install-sh/missing/compile/depcomp 的 755。"""
        for name in ("configure", "config.guess", "config.sub", "install-sh",
                     "missing", "compile", "depcomp"):
            path = os.path.join(self.source_folder, name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

    def _configure(self, autotools):
        """§12.38 / E386 家族（本次真机逐条实测定档，三种 shell 形态的差异已实证）：
          * 不路由（profile 原样把 SHELL/CONFIG_SHELL 指向 hnp bash）⇒ configure 的
            ac_pwd 计算失败，首错 `configure: error: working directory cannot be determined`；
          * 改 /bin/sh ⇒ 它能定义简单函数，但撑不住 autoconf 的复杂函数，
            表现为 `configure[N]: ac_fn_c_try_link: inaccessible or not found`，
            随后崩成 `cannot guess build type`；
          * 用 hnp bash（函数语义完整）+ **显式预置 PWD** ⇒ 实测
            `checking whether we are cross compiling... no`，conftest 真跑，通过。
        即 §12.38 记的"第二道：PWD 预置"在这里才是有效解。
        参数一律复用 Conan 生成的 _configure_args，不得只重拼 --prefix（E232 forbid_2）；
        分支判据用 settings_build.os 而非 settings.os（E232 forbid_1）。
        """
        settings_build = getattr(self, "settings_build", self.settings)
        if str(settings_build.os) == "OHOS":
            # 与 conan 同形：configure 用 source_folder 下的绝对路径，在 build_folder 里执行
            script = os.path.join(self.source_folder, "configure")
            # _configure_args 是 Autotools 从 <namespace>_conanbuild.conf 读出的**字符串**
            # （非列表），直接拼接；再 join 会把字符逐个插空格。
            args = autotools._configure_args
            self.run('env PWD="{cwd}" CONFIG_SHELL={sh} SHELL={sh} {sh} "{script}" {args}'
                     .format(cwd=self.build_folder, sh=_NATIVE_BASH, script=script, args=args),
                     cwd=self.build_folder, env="conanbuild")
        else:
            autotools.configure()

    def build(self):
        apply_conandata_patches(self)
        _prepare_autotools_env()
        # configure 已由 source() 从随包导出的 generated/ 还原到位（官方 tarball 本身
        # 不带 configure，README 口径是 autoreconf -f -i）。构建期**不跑**任何 autotools
        # bootstrap：CI worker 上有 hnp autoconf 2.72 但没有 aclocal，现场生成必崩
        # （#12629 build 60809 首错 Can't exec "aclocal" → aclocal failed exit 2）。
        # 缺件一律硬失败，绝不静默回退到现场 autoreconf——那正是 CI 的死法。
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            raise ConanException(
                "no %s: the recipe ships its bootstrap files under %s/ and does not "
                "run autoreconf at build time (CI workers have no aclocal)"
                % (configure_path, _PREGEN_DIR))
        self._restore_script_modes()
        autotools = Autotools(self)
        self._configure(autotools)
        # E074：HMDFS 上 jobserver fifo 会 EPERM，并行 make 直接挂 ⇒ -j1
        autotools.make(args=["-j1"])

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        # 只跑 install，绝不 install-strip：strip 会剥掉 clang 链接期嵌入的
        # ad-hoc .codesign 段，被剥副本在设备上 "Operation not permitted"（E077）
        autotools.install()
        self._sign_executables()

    def _sign_executables(self):
        """E077 四步：先 --remove-section .codesign 再 selfSign。
        调用签名器必须 env -u LD_LIBRARY_PATH（§12.14：conan-verify 经 ELF wrapper
        启动时注入的 SDK libc++ 会劫持 binary-sign-tool 的 std::__h 符号，
        报 symbol not found / exit 127，直接打断 package()）。
        保护分支按经验汇总要求：非 OHOS / 工具不存在 / 单文件失败都不硬中断。"""
        if str(self.settings.os) != "OHOS":
            return
        if not (os.path.isfile(_OBJCOPY) and os.path.isfile(_SIGNER)):
            self.output.warning("OHOS signing tools not found; skipping ELF self-sign")
            return
        for binary in sorted(glob.glob(os.path.join(self.package_folder, "bin", "*"))):
            if os.path.islink(binary) or not os.path.isfile(binary):
                continue
            # self.run 默认在返回码非 0 时直接抛 ConanException；这里要的是
            # "单文件失败只降级告警"，所以必须显式 ignore_errors 才拿得到返回码。
            if self.run('{} --remove-section .codesign "{}"'.format(_OBJCOPY, binary),
                        ignore_errors=True) != 0:
                self.output.warning("objcopy failed for %s; left unsigned" % binary)
                continue
            if self.run('env -u LD_LIBRARY_PATH {} sign -inFile "{}" -outFile "{}" '
                        '-selfSign 1'.format(_SIGNER, binary, binary),
                        ignore_errors=True) != 0:
                self.output.warning("sign failed for %s; left unsigned" % binary)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
