"""Conan recipe — GNU combine 0.4.0 (autotools command line tool) for HarmonyOS PC.

上游: https://www.gnu.org/software/combine/  (集合运算 CLI: union / intersection /
difference / complement / join / unique / enumerate，逐行作用于文本文件)

适配路径 A（autotools + `conan create`）；全部 OHOS 适配点见同目录 notes.md。

补丁 (conandata.yml -> patches/, `-p1`):
  0001-config.guess.patch
        本快照 config.guess 是 2004-03-12 版（E160/E007 一族，仓内 B 先例 M4），
        不识别 `uname -s` = HarmonyOS ⇒ configure 报 "cannot guess build type"。
        本版分支体是 per-branch `echo <triplet>; exit 0 ;;` 风格
        （`grep -c 'GUESS=' config.guess` = 0），与仓内
        scripts/patch-autotools-ohos.pl 产出的 GUESS= 形态不同 ⇒ 按本快照自己的
        风格生成成对补丁，⛔ 直接复用别包锚点（实证会 Hunk FAILED）。
  0002-config.sub.patch
        同快照 config.sub (2004-03-12) 不认 aarch64，也不认 linux-ohos
        （落到 `-linux*)` 分支会被改写成 -linux-gnu-ohos）⇒ 补 4 处白名单。
  0003-configure-umask.patch
        autoconf 的临时目录用 `umask 077` 建 `./confXXXXXX`，HMDFS 上该目录落成
        drwx--S--- 且随后写入被拒（E011/E114 族）。构建目录内 A/B 实测：
        umask 077 → `can't create ./confXXXXXX/subs1.awk: Permission denied`
        ⇒ `config.status: error: could not setup config files machinery`；
        umask 002 → drwxrws--x 且写入正常 ⇒ 把两处 077 改成 002（保持"仅组内可读"
        语义、又不依赖环境 umask，比直接删掉 umask 更可复现）。
  0004-test-combine-shebang.patch
        上游 tests/test_combine 首行 `#!/bin/bash`，HarmonyOS 上没有 /bin/bash
        （实测 `ls /bin/bash` → No such file，/bin/sh → /system/bin/sh）
        ⇒ `make check` 起手就 ENOENT。只改 shebang：脚本里的 `[[ ]]`/`==`
        实测被目标 /bin/sh 接受（见 notes.md 实测记录），不动脚本体。

构建路由（E386 同族，本机一手复现）：profile `ci/conan/profiles/ohos-aarch64` 的
[buildenv] 导出 `CONFIG_SHELL=/data/service/hnp/bin/bash`，autoconf 会用
$CONFIG_SHELL 重新 exec 自己，而 hnp bash 在 HMDFS 支撑的构建目录里 getcwd()
必挂 ⇒ 实测报 `configure: error: working directory cannot be determined`。
仓内 gnu-pw-mgr/2.7.4、gtypist/2.10.1（units/2.22、bc/1.07.1 同源）已合入的解法
是给每条构建命令加 `env -u CONFIG_SHELL SHELL=/bin/sh` 前缀，本配方沿用。
⛔ 不拿 --build/--host 绕（会被判交叉编译，AC_RUN_IFELSE 一律静默跳过）。

可选依赖 guile（configure.ac:26 `AC_CHECK_LIB([guile],[gh_scm2bool])`）没有
required/AC_MSG_ERROR 判定，全部 guile 调用点都在 HAVE_LIBGUILE/HAVE_LIBGUILE_H
条件编译内（src/df_common.h:31,34,36,37,202 与 src/main.c:21，唯一 guile TU 是
src/iguile.c）⇒ 本配方不 requires guile（也不造 dummy 包/假头）。

doc/combine.info 完整性（独立 W4 判决 W68R-COMB-01）：压时间戳**不足以**让 automake 的
`.texinfo.info` 规则不触发 —— `make` 阶段 doc/ 会再生 version.texi，`make check` 于是仍
执行该规则；目标上没有 makeinfo ⇒ tarball 自带的原件被 `-o` 截成 0 字节并装进包里。
配方改为「每次 make 之前把原件字节快照到 build_folder，全部 make 跑完按快照原样写回，
再用解包后一手算出的 size + sha256 逐字节断言」，并对包内 share/info/combine.info 复核。
⛔ 把 MAKEINFO 占位成 `:`/`true`（那条规则会先备份 `$@` 再让假 makeinfo "成功"、最后
`rm -rf` 备份目录 ⇒ 真件被吃掉）；⛔ 从 package() 里少装 info 文件（改变上游安装面）。
判决行机器可读：
COMBINE_INFO_INTEGRITY=pre=<size> post=<size> sha=<sha256 前 12 位> restored=<bool>
"""
import hashlib
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

# E386 同族解法（见模块 docstring）：剥掉 profile 注入的 CONFIG_SHELL，
# 并把 SHELL 钉到目标上真实存在的 /bin/sh
SH = "env -u CONFIG_SHELL SHELL=/bin/sh"

# W68R-COMB-01：tarball 自带 doc/combine.info 原件的字节快照落在 **build_folder**
# （⛔ 留在源码树里 —— 它会被 make/dist 看见，也会污染归档面）
INFO_SNAPSHOT = "combine.info.pristine"

# 与 conan AutotoolsToolchain 默认注入的参数保持一致（--prefix=/ + DESTDIR 打包），
# 手工调用 configure 时必须自带，否则产物会落到 /bin 而不是 <package_folder>/bin。
# ⛔ 不加 --build/--host（见模块 docstring）。
CONFIGURE_ARGS = (
    "--prefix=/"
    " '--bindir=${prefix}/bin'"
    " '--sbindir=${prefix}/bin'"
    " '--libdir=${prefix}/lib'"
    " '--includedir=${prefix}/include'"
    " '--oldincludedir=${prefix}/include'"
    # po/ 与 intl/ 走 gettext（AC_CHECK_HEADERS 含 libintl.h、AM_GNU_GETTEXT）。
    # 目标上没有 libintl 运行时，消息目录也不是交付物 ⇒ --disable-nls：
    # configure 置 USE_NLS=no，po/Makefile 随之只跑 Makefile.in.in 里的
    # `all-no:` / `install-data-no: all` 空目标，因此 worker 上没有
    # msgfmt/autopoint（实测二者只在 ~/.harmonybrew/bin 里存在）也能构建。
    " --disable-nls"
    # guile 是可选依赖（见模块 docstring）。把两条探测显式钉成 no，而不是听任
    # worker 上是否残留 /usr/local/include/libguile.h：
    #   * ac_cv_header_libguile_h=yes 会打开 HAVE_LIBGUILE 分支并触发 GUILE_FLAGS
    #     宏（configure:12152 跑 `$GUILE_CONFIG info pkgdatadir`，
    #     guile-config 不存在时 configure 直接失败）；
    #   * 它同时决定 GUILE_SITE ⇒ src/combine_scm 的安装目录（见 package()）。
    # 钉死之后构建结果与机器残留无关、可复现。代价：上游 Test 7（guile 扩展用例）
    # 必然失败，已在 notes.md 与测试统计里如实申报，⛔ 不删用例、⛔ 不缩分母。
    " ac_cv_lib_guile_gh_scm2bool=no"
    " ac_cv_header_libguile_h=no"
)


class CombineConan(ConanFile):
    name = "combine"
    version = "0.4.0"
    description = ("GNU Combine: set-theory operations (union, intersection, "
                   "difference, complement, join, unique, enumerate) on the lines "
                   "of text files")
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/combine/"
    url = ""  # CI fills this

    package_type = "application"  # bin_PROGRAMS = combine；lib/ 的 libdf.a 是 noinst
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0/R36: 无必须依赖（guile 可选、NLS 关闭）⇒ 本包对制品仓零依赖。
        pass

    def validate(self):
        # R32: os 判断必须用 in ("Linux", "OHOS")，不能 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "combine/0.4.0 is only validated on Linux/OHOS, not %s"
                % self.settings.os)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 仍然生成 toolchain：CC/CFLAGS/LDFLAGS/PATH 由 conanbuild.sh 注入环境，
        # 手工 configure/make 直接吃这份环境（R33：⛔ 裸用 ${CC} 之类的 shell 变量）
        tc = AutotoolsToolchain(self)
        tc.generate()

    # ------------------------------------------------------------------
    # doc/combine.info 完整性保护（独立 W4 判决 W68R-COMB-01）
    #
    # 实测（2026-09-26 18:2x 那轮 create 日志 :3138 与 :3176-3199）：
    # `make` 阶段 doc/ 打印 `Updating ./version.texi` ⇒ 再生件比 combine.info 新，
    # `make check` 的 `Making check in doc` **照样**执行 `.texinfo.info` 规则；
    # `missing --run makeinfo -o combine.info combine.texinfo` 在目标上 127（无
    # makeinfo），而同一规则里的备份守卫 `missing --run makeinfo --version` 也失败
    # ⇒ `restore` 保持 `:`、原件没被移进 .am$$ 备份目录 ⇒ makeinfo 的 `-o` 已经把
    # 97620 B 的真件截成 0 字节，随后 `make install` 把这个空件装进 share/info/。
    # ⇒ 时间戳压制只是减少一次无谓触发，**不是**交付面正确性的依据。
    #
    # 处置（不改上游安装面、不碰 Makefile.am/Makefile.in、不把 MAKEINFO 占位成 `:`）：
    #   1. 解包后一手算出原件的 size + sha256 作参照（⛔ 拿 97620 这类常数当判据）；
    #   2. 每次 make 之前把原件字节快照到 build_folder（⛔ 留在源码树里）；
    #   3. 全部 make 跑完后若 size/sha 与快照不符（含被截成 0）就按快照**原样写回**；
    #   4. 写回后逐字节断言等于参照，不等就 ConanException（⛔ 只打 warning 放行）；
    #   5. 对包内 share/info/combine.info 再断一次，防 make install 阶段二次打破。
    # ------------------------------------------------------------------

    def _info_paths(self):
        return (os.path.join(self.source_folder, "doc", "combine.info"),
                os.path.join(self.build_folder, INFO_SNAPSHOT))

    def _info_sha256(self, path):
        digest = hashlib.sha256()
        with open(path, "rb") as fp:
            while True:
                chunk = fp.read(1 << 16)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def _info_measure(self, path):
        if not os.path.exists(path):
            return -1, ""
        return os.stat(path).st_size, self._info_sha256(path)

    def _info_snapshot(self, label):
        """每次 make 之前调用：确立/刷新原件快照（⛔ 把已被截断的件当参照）。"""
        info, snap = self._info_paths()
        size, sha = self._info_measure(info)
        if size < 0:
            raise ConanException(
                "combine/0.4.0: doc/combine.info is missing (%s) before %s; the tarball "
                "ships it, so nothing may remove it" % (info, label))
        ref = getattr(self, "_info_ref", None)
        if ref is None:
            # 参照只能在**任何 make 之前**确立；此时原件就还是 tarball 的字节
            if size == 0:
                raise ConanException(
                    "combine/0.4.0: doc/combine.info already arrived as a 0-byte file "
                    "before %s - cannot establish a pristine reference" % label)
            ref = self._info_ref = (size, sha)
        if (size, sha) == ref or not os.path.exists(snap):
            os.makedirs(self.build_folder, exist_ok=True)
            shutil.copyfile(info, snap)
        self.output.info("COMBINE_INFO_SNAPSHOT=phase=%s size=%s sha=%s ref=%s/%s"
                         % (label, size, sha[:12], ref[0], ref[1][:12]))

    def _info_verify(self):
        """全部 make 跑完之后调用：被截断就按快照原样写回，再逐字节断言。"""
        info, snap = self._info_paths()
        ref_size, ref_sha = self._info_ref
        pre_size, pre_sha = self._info_measure(info)
        restored = (pre_size, pre_sha) != (ref_size, ref_sha)
        if restored:
            if not os.path.exists(snap):
                raise ConanException(
                    "combine/0.4.0: doc/combine.info was damaged (size=%s) and the "
                    "pristine snapshot %s is gone - refusing to ship a truncated "
                    "document" % (pre_size, snap))
            shutil.copyfile(snap, info)
        post_size, post_sha = self._info_measure(info)
        self.output.info("COMBINE_INFO_INTEGRITY=pre=%s post=%s sha=%s restored=%s"
                         % (pre_size, post_size, post_sha[:12],
                            "true" if restored else "false"))
        if (post_size, post_sha) != (ref_size, ref_sha):
            raise ConanException(
                "combine/0.4.0: doc/combine.info is not byte-identical to the tarball "
                "original after restore: expected size=%s sha256=%s, got size=%s "
                "sha256=%s" % (ref_size, ref_sha, post_size, post_sha))

    def _info_check_packaged(self):
        """包内 share/info/combine.info 必须与 tarball 原件逐字节相同（⛔ 悄悄少装）。"""
        delivered = os.path.join(self.package_folder, "share", "info", "combine.info")
        ref_size, ref_sha = self._info_ref
        size, sha = self._info_measure(delivered)
        self.output.info("COMBINE_INFO_PACKAGED=size=%s sha=%s expected=%s/%s path=%s"
                         % (size, sha[:12], ref_size, ref_sha[:12], delivered))
        if (size, sha) != (ref_size, ref_sha):
            raise ConanException(
                "combine/0.4.0: packaged share/info/combine.info does not match the "
                "tarball original: expected size=%s sha256=%s, got size=%s sha256=%s "
                "at %s" % (ref_size, ref_sha, size, sha, delivered))

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # configure / Makefile.in / config.* 都是脚本，HMDFS 解包不保证可执行位（E490）
        for f in ("configure", "config.guess", "config.sub", "install-sh",
                  "missing", "depcomp", "mkinstalldirs", "config.rpath"):
            p = os.path.join(src, f)
            if os.path.exists(p):
                os.chmod(p, 0o755)
        # tests/Makefile.am 的注册入口是手写目标
        #   check: $(srcdir)/test_combine $(srcdir) $(top_builddir)/tests
        # 由 make **直接 exec** 该脚本 ⇒ 可执行位必须补回，否则 check 起手就失败
        tc_script = os.path.join(src, "tests", "test_combine")
        if os.path.exists(tc_script):
            os.chmod(tc_script, 0o755)

        # doc/Makefile.am 只有 `info_TEXINFOS = combine.texinfo`，而目标上没有
        # makeinfo（实测 command -v makeinfo = NONE）。tarball 已带生成好的
        # doc/combine.info：把**生成物**的时间戳压过 .texinfo，可以让 `make` 阶段
        # 少跑一次 `.texinfo.info` 规则（gnu-pw-mgr/2.7.4 同族做法）。
        # ⚠ 但压时间戳**不保证规则不触发**：`make` 阶段会重新生成 version.texi，
        # 到 `make check` 时该规则照样执行，makeinfo 缺失会把原件截成 0 字节
        # （实测见上方「doc/combine.info 完整性保护」注释）⇒ 真正的交付面保障是
        # 下面三处一手算出的快照/写回/断言，不是这条 utime。
        # 把 MAKEINFO 占位成 `:`/`true` 反而危险：那条规则会先把 $@ 备份进 .am$$
        # 再让假 makeinfo “成功”，最后 rm -rf 备份目录，真件会被吃掉。
        # ⛔ 这里不动 Makefile.am/Makefile.in（R6：只碰生成物时间戳）。
        doc = os.path.join(src, "doc")
        info = os.path.join(doc, "combine.info")
        texi = os.path.join(doc, "combine.texinfo")
        if os.path.exists(info) and os.path.exists(texi):
            newer = os.stat(texi).st_mtime + 3600.0
            os.utime(info, (newer, newer))

        # 参照只能在任何 make 之前确立（此刻 doc/combine.info 还是 tarball 的字节）
        self._info_snapshot("before-configure")

        # 树内构建（gnu-pw-mgr/2.7.4 同族）：tests 的手写 check 目标按
        # ${bld}/../src/combine 找二进制，树内跑最稳
        self.run('cd "%s" && %s sh configure %s' % (src, SH, CONFIGURE_ARGS))
        self._info_snapshot("before-make")
        self.run('cd "%s" && %s make -j1' % (src, SH))

        # ★ 上游测试真跑（R51 / 手册04 §10：0 执行一律不可交付）
        # tests/ 的 check 目标跑 test_combine：7 个用例，逐个把 combine 的输出与
        # 黄金件 stats*.txt / result*.txt 做 diff -q 比对（共 15 次比对）。
        # ⛔ 不用 try/except 吞非零退出：make 失败直接让 conan create 失败。
        # ⚠ 诚实口径：上游 test_combine 自身的退出码恒为 0（最后一条命令是 rm），
        #   用例失败只会打印 "Test N: ... FAILED" ⇒ 判决必须逐用例点收日志，
        #   不能只看 make 返回 0（见 notes.md 的五维台账）。
        self._info_snapshot("before-make-check")
        self.run('cd "%s" && %s make -j1 check' % (src, SH))

        # ★ W68R-COMB-01：`.texinfo.info` 规则在上面两次 make 里有权改写原件；
        #   跑完立刻按快照写回并逐字节断言（断言不过 = create 直接失败）
        self._info_verify()

    def package(self):
        # DESTDIR 打包（--prefix=/ ⇒ 产物落在 <package_folder>/bin）
        # src/combine_scm/Makefile.am 把两个 guile 模块装到
        #   guiledatedir = @GUILE_SITE@/combine_scm
        # 本构建不启 guile ⇒ GUILE_SITE 为空 ⇒ 该目录退化成 "/combine_scm"，
        # 产物会落在 <package_folder>/combine_scm（包根散目录）。命令行覆盖 make
        # 变量把它显式重定向到 share/combine_scm，既不留散目录也不丢上游 .scm 载荷
        # （⛔ 改生成的 Makefile.in，R6）。
        self.run('cd "%s" && %s make install DESTDIR="%s" guiledatedir=/share/combine_scm'
                 % (self.source_folder, SH, self.package_folder))
        # ⛔ 不是"少装 info"，而是断言装进去的那份与 tarball 原件逐字节相同：
        # make install 也会走 doc/ 的 info 依赖链，装完再核一次才算交付面证据
        if getattr(self, "_info_ref", None) is not None:
            self._info_check_packaged()

    def package_info(self):
        # 纯命令行工具：lib/ 的 libdf.a 是 noinst_LIBRARIES，包内无 .a/.so
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
