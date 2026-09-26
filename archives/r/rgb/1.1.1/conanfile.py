#!/usr/bin/env python3
"""Conan recipe — rgb 1.1.1 (X11 颜色名数据库工具集)

Build system: autotools (configure + make)
License: MIT
Homepage: https://gitlab.freedesktop.org/xorg/app/rgb

依赖说明: configure.ac 只有一处 PKG_CHECK_MODULES(RGB, xproto)，而 xproto.pc
与 <X11/Xos.h>/<X11/Xfuncs.h> 均由已发布的 xorgproto/2025.1 提供（仓库
actiona/clipnotify/comptty 同款依赖）。text 模式下 showrgb 只做文本库解析
（fopen/sscanf/printf），**不链接任何 X 客户端库**，因此本配方没有
libX11/libXext 依赖，也不需要 rpath/LD_PRELOAD。

构建模式选择（重要，见 notes.md「rgb 与 xorgrgb」一节）：
上游 Makefile.am 是 `bin_PROGRAMS = showrgb`，`rgb` 这个二进制只在
`if RGB_DB`（即 --with-rgb-db-type=dbm|ndbm）时才追加到 bin_PROGRAMS。
而 configure.ac 的 dbm/ndbm 两个分支都**无条件**执行
`PKG_CHECK_MODULES(XORG, [xorg-server])`，并且需要 dbm.h/ndbm.h +
dbminit()/dbm_open() 的实现库。实测 ohpcd 制品仓 `xorg-server` 与 `ndbm`
均为 "Found 0 pkg/version recipes"，OHOS sysroot 内也找不到 dbm.h/ndbm.h。
按 W0（精确依赖必须先确认已发布，禁止假头文件/ dummy 包）只能取上游默认
text 模式：产出 showrgb + 安装 rgb.txt，`rgb` DB 编译器不在本包内。

上游无测试套件：man/../Makefile.am grep 'check|TESTS' 为空，无 TESTS、
无 check_PROGRAMS、源码树无 tests/ 目录 ⇒ 静态测试数 N_static=0。
test_package 因此真实运行被测二进制并断言其行为（版本串、帮助退出码、
默认颜色库解析、显式库路径解析、缺库错误路径），共 5 条断言。

OHOS 适配点（复用仓库 xeyes/libX11 已过门禁的同款手法）：
  - config.guess 不认 uname -s=HarmonyOS：由 patches/0001-config.guess.patch 补
    `*:HarmonyOS:*:*)` 分支 ⇒ 三元组由 config.guess 探测，配方不写 --build/--host（SKILL §4.1）。
  - HMDFS getcwd: conan 缓存父目录对 getcwd() 不可达，configure 顶部 `pwd`
    判定会报 "working directory cannot be determined"；固定 cwd 到
    build_folder + 预置 PWD，并把 configure 的 pwd 判定改写为回退 $PWD。
  - E011/E114: configure 创建 config.status 临时目录用 `umask 077`，HMDFS
    上导致后续读取失败，统一改 022。
  - CI worker PATH 缺工具链目录：从 compiler_executables 推导并前置。
  - OHOS 内核拒绝未签名 ELF：package() 对 bin/ 下二进制自签。
"""
import glob as _glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _walk_find(root, name=None):
    """列出 root 子树下的文件（name=None 时全部；否则仅文件名等于 name 的）。

    为什么不用 glob：`glob.glob(root + "/**/x", recursive=True)` **不会进入以点开头的目录**
    （Python 的 `**` 遵循 shell 的 dotfile 惯例），而本包 DESTDIR 与烧死的绝对 --datadir
    叠加出的壳路径里恰好含 `/.cache/` ⇒ 旧写法恒返回空列表：既漏掉 rgb.txt 的归位，
    又让下面"壳内无真实文件才删"的护栏一起失明，最终把唯一的 rgb.txt 连壳删掉（CI 实测红）。
    os.walk 无此限制，且这里要的是"看得见"，不需要 glob 的通配能力。
    """
    out = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if name is None or fn == name:
                out.append(os.path.join(dirpath, fn))
    return out


class RgbConan(ConanFile):
    name = "rgb"
    version = "1.1.1"
    description = (
        "X11 rgb color-name database: showrgb dumper "
        "(text-mode build; the rgb DB compiler needs xorg-server)"
    )
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/rgb"
    url = "https://gitlab.freedesktop.org/xorg/app/rgb"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def configure(self):
        # R32 平台限制：本包的 text 模式定性、config.guess 补丁与烤入的绝对库路径都只在
        # OHOS/Linux + armv8 上真机验证过；其它组合直接拒绝，而不是静默产出不可用包。
        supported_os = ("OHOS", "Linux")
        if str(self.settings.os) not in supported_os or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "rgb 1.1.1 仅在 os ∈ %s 且 arch=armv8 上验证（实测组合 OHOS/armv8），"
                "当前 os=%s arch=%s 未验证。"
                % (supported_os, self.settings.os, self.settings.arch)
            )

    def source(self):
        get(self, **self.conan_data["sources"]["rgb"], strip_root=True)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _xorgproto_paths(self):
        """xorgproto 依赖包的 include 目录与 pkgconfig 目录列表。"""
        dep = self.dependencies["xorgproto"]
        pkg = dep.package_folder
        pcs = []
        for sub in ("lib/pkgconfig", "share/pkgconfig", "lib64/pkgconfig"):
            cand = os.path.join(pkg, sub)
            if os.path.isdir(cand):
                pcs.append(cand)
        incs = [os.path.join(pkg, d) for d in getattr(dep.cpp_info, "includedirs", []) or []]
        if not incs:
            incs = [os.path.join(pkg, "include")]
        return incs, pcs

    def _prepend_toolchain_path(self):
        """CI worker PATH 缺工具链目录（xeyes/flint 同款实测）：clang 本体按
        绝对路径可用，但其内部调用的 ld.lld/as 走 PATH 解析，缺失时 configure
        报 "C compiler cannot create executables"。从编译器路径 dirname 推导
        工具链目录并前置，不硬编码机器路径；已在 PATH 中则跳过（幂等）。
        """
        cc = None
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            cc = compilers.get("c") or compilers.get("cpp")
        except Exception:  # noqa: BLE001 - conf 缺失时回落环境变量
            cc = None
        if not cc:
            cc = os.environ.get("CC")
        if not cc:
            return
        toolchain_dir = os.path.dirname(cc)
        if not toolchain_dir:
            return
        cur = os.environ.get("PATH", "")
        if toolchain_dir in (cur.split(os.pathsep) if cur else []):
            return
        os.environ["PATH"] = toolchain_dir + os.pathsep + cur

    def _fix_script_modes(self):
        """E490：HMDFS 的部分适配路径会丢掉 autotools helper 脚本的执行位，
        导致 configure/config.sub 不可执行而使 conan create（G2）失败。
        处方：对已知 helper 脚本统一 chmod +x（仓库口径 restore-known-autotools-
        script-modes，仅处理名字在白名单内的脚本，不改内容）。"""
        fixed = []
        for name in (
            "configure", "config.guess", "config.sub", "install-sh",
            "missing", "compile", "depcomp", "ltmain.sh", "ar-lib", "test-driver",
        ):
            for path in _glob.glob(
                os.path.join(self.source_folder, "**", name), recursive=True
            ):
                try:
                    os.chmod(path, 0o755)
                    fixed.append(os.path.basename(path))
                except OSError as exc:
                    self.output.warning("chmod +x %s failed: %s" % (path, exc))
        if fixed:
            self.output.info("E490 chmod +x applied to: %s" % ", ".join(sorted(set(fixed))))

    def _rewrite_configure(self):
        """HMDFS 兜底：umask 077 -> 022（E011/E114）+ pwd 失败回退 $PWD。

        conan 缓存父目录对 getcwd() 不可达（目录本身可寻址），autoconf 生成
        的 configure 顶部 `pwd` 判定会直接 abort "working directory cannot be
        determined"；config.status 的临时目录创建用 umask 077，HMDFS 上后续
        读取会失败。与仓库 nspr/aribb24/libgsf/xeyes 同款改写。
        """
        for cfg in _glob.glob(
            os.path.join(self.source_folder, "**", "configure"), recursive=True
        ):
            try:
                with open(cfg, "r", encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            orig = text
            text = text.replace("umask 077", "umask 022")
            if 'ac_pwd=`pwd` && test -n "$ac_pwd" &&' in text:
                text = text.replace(
                    'ac_pwd=`pwd` && test -n "$ac_pwd" &&',
                    'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"'
                    ' && test -n "$ac_pwd" &&',
                    1,
                )
            elif "if (pwd) >/dev/null 2>&1; then :; else" in text:
                text = text.replace(
                    "if (pwd) >/dev/null 2>&1; then :; else",
                    'if (pwd) >/dev/null 2>&1 || test -n "$PWD"; then :; else',
                )
            if text != orig:
                with open(cfg, "w", encoding="utf-8") as fh:
                    fh.write(text)

    def _sign_elf(self, path):
        """ELF 代码签名：OHOS 内核拒绝执行未签名 ELF（clinfo/xeyes 同款）。"""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(
                f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1'
            )
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass  # HMFS 可能不支持 chmod（HMBS_CAP_CHMOD=0）

    # ------------------------------------------------------------------ #
    # build pipeline
    # ------------------------------------------------------------------ #
    def generate(self):
        tc = AutotoolsToolchain(self)
        incs, pcs = self._xorgproto_paths()

        # PKG_CHECK_MODULES(RGB, xproto) 需要 pkg-config 命中 xproto.pc。
        # xorgproto 的 .pc 在 share/pkgconfig（非 lib/pkgconfig），必须显式
        # 给出；保留 conan 注入的既有值，避免覆盖其它依赖的搜索路径。
        existing = os.environ.get("PKG_CONFIG_PATH", "").strip()
        pc_all = pcs + ([existing] if existing else [])
        if pc_all:
            tc.configure_args.append("PKG_CONFIG_PATH=" + ":".join(pc_all))

        # include 路径：text 模式 showrgb.c 需要 <X11/Xos.h>/<X11/Xfuncs.h>
        for inc in incs:
            tc.extra_cflags.append(f"-I{inc}")

        # 平台三元组由 **config.guess 自己探测**（patches/0001-config.guess.patch 给它加了
        # HarmonyOS 分支，真机 uname -s=HarmonyOS ⇒ aarch64-unknown-linux-ohos）。
        # 不在此写死 --build/--host/--target：SKILL §4.1 禁用交叉三元组，且写死 arch
        # 会让 settings.arch 变化时静默产出错架构产物（libfontenc/1.1.7 同族同法）。

        # ★ text 模式是本平台唯一可构建分支（09-23 实测定性，详见 notes.md）：
        # dbm/ndbm 分支下 showrgb.c 有 `#ifndef USE_RGB_TXT / #include "rgb.h"`，
        # 上游注释自陈 "off in server/include/" —— rgb.h 属 **xorg-server**；
        # 官方 release tarball 完整清单**不含 rgb.h**（tar tzf 实测），且 ohpcd
        # 无 xorg-server recipe ⇒ 该分支无法编译。
        # 注意该结论与 ndbm 库符号无关：实测 gdbm/1.23 compat 层可让
        # `checking for dbm_open in -lgdbm_compat... yes` 通过，**头文件才是硬墙**。
        tc.configure_args.append("--with-rgb-db-type=text")

        # ★ 必须显式给 --with-rgb-db-dir，否则默认库路径不可用（实测 test 3 FAIL：
        # `showrgb` 无参运行 exit=1 / unable to open rgb database "/share/X11/rgb"）。
        # 机理：showrgb.c:57 `dbname = RGB_DB`，text 分支再补 ".txt"
        # （showrgb.c:141/148），而 RGB_DB 由 configure 烤成 "$(db_dir)/$(db_file)"。
        # build-driver 用 --prefix=/ ⇒ 烤出 /share/X11/rgb，与包内实际安装的
        # <pkg>/share/X11/rgb.txt 不一致。指到 package_folder 后 db_dir=<pkg>/share/X11、
        # db_file=rgb，安装位置与编译期默认值重新对齐。
        tc.configure_args.append(
            "--with-rgb-db-dir=" + os.path.join(self.package_folder, "share", "X11", "rgb")
        )

        # E017：harness 默认 --enable-werror 会把隐式声明告警升成硬错误（09-23 实测）
        tc.extra_cflags.append("-D_GNU_SOURCE")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._fix_script_modes()
        self._prepend_toolchain_path()
        # HMDFS getcwd 兜底：cwd 固定到 build_folder 并预置 PWD
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD fallback")
        os.environ["PWD"] = self.build_folder
        self._rewrite_configure()

        autotools = Autotools(self)
        autotools.configure()
        # -j1：诊断期取第一条真实错误（并发报错会淹没首错），包体量小无性能诉求
        autotools.make(args=["-j1"])

    def _relocate_rgb_db(self):
        """把颜色库归位到编译期 RGB_DB 指向的位置。

        Autotools.install() 以 --destdir=package_folder 安装，而本包为保证
        showrgb 的编译期默认库路径可用，把 --with-rgb-db-dir 指到了包内绝对路径
        （见 generate()）；两者叠加会使 `make install` 把 rgb.txt 装进
        <pkg>/<pkg>/share/X11/rgb.txt 这种重复嵌套的位置，导致包内按
        <pkg>/share/X11/rgb.txt 找不到默认库（09-23 实测 test 3 FAIL:
        packaged default database missing）。这里按实际落点归位并清理空壳目录。
        """
        pkg = self.package_folder
        want = os.path.join(pkg, "share", "X11")
        found = _walk_find(pkg, "rgb.txt")
        target = os.path.join(want, "rgb.txt")
        if target not in found:
            for src_path in found:
                try:
                    os.makedirs(want, exist_ok=True)
                    shutil.move(src_path, target)
                    found = [target]
                    break
                except OSError as exc:
                    self.output.warning("rgb.txt 归位失败 %s: %s" % (src_path, exc))
        if not found:
            self.output.error("package(): 未找到任何 rgb.txt，默认颜色库不可用")
        # 清掉 --destdir 与绝对 rgbdir 叠加产生的「包内绝对路径壳」目录：本包真实产物
        # 只在 bin/ 与 share/ 下，<pkg>/storage/... 里不可能是合法内容，故按壳根整体删。
        # 不用 ignore_errors——上一版它把失败静默吞掉，交付包里留下 9 个空目录（r2 审计 P2）。
        if not pkg.startswith(os.sep):
            return
        shell = os.path.join(pkg, pkg.lstrip(os.sep).split(os.sep, 1)[0])
        if not os.path.isdir(shell):
            return
        strays = _walk_find(shell)
        if strays:
            self.output.error(
                "包内绝对路径壳目录里发现真实文件，未删除（需人工定性）：%s" % strays[:5])
            return
        try:
            shutil.rmtree(shell)
            self.output.info("已清理包内绝对路径壳目录：%s" % shell)
        except OSError as exc:
            self.output.error(
                "清理包内绝对路径壳目录失败 %s: %s（交付包会残留空目录）" % (shell, exc))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._relocate_rgb_db()
        # 清理 conan 前缀下无价值的打包元数据（避免误入包内容审计）
        for junk in ("share/man/whatis",):
            for p in _glob.glob(os.path.join(self.package_folder, junk)):
                os.remove(p)
        # OHOS 内核拒绝未签名 ELF：bin/ 下全部二进制自签
        bin_dir = os.path.join(self.package_folder, "bin")
        for f in sorted(os.listdir(bin_dir)) if os.path.isdir(bin_dir) else []:
            path = os.path.join(bin_dir, f)
            if os.path.isfile(path):
                self._sign_elf(path)

    def package_info(self):
        # 命令行工具包：仅暴露 bin/（R38）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
