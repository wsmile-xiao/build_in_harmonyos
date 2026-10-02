#!/usr/bin/env python3
"""Conan recipe — trickle 1.08

User-space bandwidth shaper (trickle/trickled/tricklectl + LD_PRELOAD
overload modules). Upstream: https://github.com/mariusae/trickle
(monkey.org/~marius/trickle). License: BSD-3-Clause.

适配要点：
- 上游无 1.08 tag；使用 Debian 1.08+ds orig tarball（git snapshot
  2024-05-06，版本号来自 configure.in AC_INIT([trickle],[1.08])）；
- tarball 无预生成 configure，build() 中先 autoreconf 自举；
- 全量背靠 Debian 1.08+ds-1.1 补丁系列（10 个，见 conandata.yml）；
- 交叉编译（OHOS）：configure 的 AC_TRY_RUN libc 访问探测无法执行
  （E064 模式），补丁给出 dlopen("libc.so") 的 musl 默认；
- 依赖：libevent（trickled 事件循环，旧 API 经 libevent2 兼容头
  event.h）+ libtirpc（trickled/tricklectl 的 XDR 编解码）；
- trickle-overload.so / libtrickle.so 是 LD_PRELOAD 共享模块，不受
  --disable-shared 控制（否则 libtool 不生成模块，链接规则会失败），
  因此本配方不传 --enable-static/--disable-shared（R26 的静态策略针对
  链接型库；trickle 产物为应用 + 强制 shared 的 preload 模块）。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class TrickleConan(ConanFile):
    name = "trickle"
    version = "1.08"
    description = "Trickle is a user-space bandwidth shaper: a lightweight, portable traffic shaper that works in userland via LD_PRELOAD"
    license = "BSD-3-Clause"
    homepage = "https://github.com/mariusae/trickle"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # R32: settings.os must accept Linux and OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libevent/2.1.13")
        self.requires("libtirpc/1.3.7")

    def build_requirements(self):
        # tarball 无 configure，需 autoreconf 自举；libtirpc 经 pkg-config 探测
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 注意：不传 --enable-static/--disable-shared —— trickle 的两个
        # LD_PRELOAD 模块必须以 libtool -module shared 形式产出。
        # configure 由 build() 以 sh 显式调用（HMDFS 执行位，含
        # --with-libevent 与 --build 三元组），此处仅生成构建环境。
        AutotoolsToolchain(self).generate()
        AutotoolsDeps(self).generate()

    @staticmethod
    def _find_conan_pkg(prefix, probe_files):
        """build() 进程的 os.environ 不含 conanbuild 注入的工具 PATH（run()
        时才临时激活），改从 CONAN_HOME 缓存定位 automake/libtool 包。"""
        ch = os.environ.get("CONAN_HOME")
        if not ch:
            return None
        for d in sorted(glob.glob(os.path.join(ch, "p", prefix + "*", "p"))):
            if all(os.path.isfile(os.path.join(d, "bin", f)) for f in probe_files):
                return d
        return None

    def _bootstrap_autotools(self):
        """HMDFS 回退自举（E087/E054）：OHOS 真机上 conan automake/libtool
        包内的 sh/perl 脚本无有效执行位，autoreconf() exec aclocal 直接
        Permission denied。此路径用显式解释器等价重放 autoreconf：
        - aclocal/automake 由 hnp perl 直接运行（.aclocal-real/.automake-real
          是 conan automake 包 wrapper 背后的真身，只读不执行）
        - autoconf/autoheader 用 PATH 中系统工具（hnp 已在 runner PATH）
        - libtoolize 以复制 ltmain.sh + libtool m4 宏替代（libtoolize 自身
          的重定位推算在脱离 wrapper 后失效）
        生成物与标准 autoreconf -i 等价（已在 OHOS 真机验证）。"""
        am = self._find_conan_pkg("autom", (".aclocal-real",))
        lt = self._find_conan_pkg("libto", ("libtoolize", "libtool"))
        if not am or not lt:
            raise ConanInvalidConfiguration(
                "无法在 PATH 中定位 automake/libtool 工具包（HMDFS 自举需要）")
        perl = "/data/service/hnp/bin/perl"
        if not os.path.isfile(perl):
            perl = shutil.which("perl") or "perl"
        acdir = glob.glob(os.path.join(am, "share", "aclocal-1.*"))[0]
        amd = glob.glob(os.path.join(am, "share", "automake-1.*"))[0]
        ltaclocal = os.path.join(lt, "share", "aclocal")
        ltbuildaux = os.path.join(lt, "share", "libtool", "build-aux")
        am_bin = os.path.join(am, "bin")
        real_aclocal = os.path.join(am_bin, next(
            f for f in os.listdir(am_bin) if f.endswith("aclocal-real")))
        real_automake = os.path.join(am_bin, next(
            f for f in os.listdir(am_bin) if f.endswith("automake-real")))
        src = self.source_folder
        os.makedirs(os.path.join(src, "m4"), exist_ok=True)
        copy(self, "ltmain.sh", src=ltbuildaux, dst=src)
        for m in ("libtool.m4", "ltoptions.m4", "ltsugar.m4",
                  "ltversion.m4", "lt~obsolete.m4"):
            copy(self, m, src=ltaclocal, dst=os.path.join(src, "m4"))
        self.run(f'"{perl}" -I "{amd}" "{real_aclocal}" '
                 f'--automake-acdir="{acdir}" '
                 f'--system-acdir="{os.path.join(am, "share", "aclocal")}" -I m4',
                 cwd=self.source_folder)
        self.run("autoconf", cwd=self.source_folder)
        self.run("autoheader", cwd=self.source_folder)
        self.run(f'"{perl}" -I "{amd}" "{real_automake}" --foreign '
                 f'--add-missing --copy --libdir="{amd}"',
                 cwd=self.source_folder)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # tarball 无 configure（autoreconf 产物不进 Debian orig tarball），先自举
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            try:
                autotools.autoreconf()
            except Exception as e:
                self.output.warning(f"autoreconf 失败（{e}），"
                                 "疑似 HMDFS 执行位问题（E087），回退显式解释器自举")
                self._bootstrap_autotools()
        # E175/E046: setgid/HMDFS 下 `(umask 077 && mktemp -d ./confXXXXXX)` 会创建
        # 2700 权限目录，config.status 写入 subs1.awk 时 Permission denied。
        # 必须在 autoreconf 之后修改（autoreconf 会重新生成 configure）。
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
                self.output.info(f"已修复 {_cfg}: umask 077 -> umask 022")
        # E087: HMDFS 上生成的 configure/config.status 均无有效执行位，
        # autotools.configure()（exec ./configure）会 126 Permission denied。
        # 改为 sh 显式调用，并置 CONFIG_SHELL 使 configure 内部以
        # "$CONFIG_SHELL ./config.status" 方式运行 config.status。
        conf = os.path.join(self.source_folder, "configure")
        libevent = ""
        for d in sorted(glob.glob(os.path.join(
                os.environ.get("CONAN_HOME", ""), "p", "libev*", "p"))):
            if os.path.isfile(os.path.join(d, "include", "event.h")) and (
                    os.path.isfile(os.path.join(d, "lib", "libevent.a")) or
                    os.path.isfile(os.path.join(d, "lib", "libevent.so"))):
                libevent = d
                break
        args = (f'--prefix="{self.package_folder}" '
                # E007/E160: config.guess 不识别 HarmonyOS，显式三元组
                '--build=aarch64-unknown-linux-ohos '
                f'--bindir="${{prefix}}/bin" --sbindir="${{prefix}}/bin" '
                f'--libdir="${{prefix}}/lib" --includedir="${{prefix}}/include" '
                f'--oldincludedir="${{prefix}}/include" '
                f'--with-libevent="{libevent}"')
        # libevent/libtirpc conan 包仅提供 .so，conftest 运行时 musl ld.so
        # 找不到（Error loading shared library，exit 127）。conanbuild 环境不含
        # LD_LIBRARY_PATH，这里显式注入依赖包 lib 目录。
        _dep_libs = []
        for pref in ("libev", "libti"):
            for d in sorted(glob.glob(os.path.join(
                    os.environ.get("CONAN_HOME", ""), "p", pref + "*", "p", "lib"))):
                if os.path.isdir(d):
                    _dep_libs.append(d)
        if _dep_libs:
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                _dep_libs + [os.environ.get("LD_LIBRARY_PATH", "")]).rstrip(os.pathsep)
        # libtool 会读取依赖包 lib/*.la（其 libdir 记录 conan 打包前的安装
        # 前缀，如 /usr/local/lib），据此拼出不存在的 .so 绝对路径导致链接
        # 失败。删除本 job 隔离 conan-home 中依赖包的 .la，强制 libtool 直接
        # 用 -L/-l 解析。
        for pat in ("libev*", "libti*"):
            for la in glob.glob(os.path.join(
                    os.environ.get("CONAN_HOME", ""), "p", pat, "p", "lib", "*.la")):
                os.remove(la)
                self.output.info(f"已移除 {la}")
        # PKG_CHECK_MODULES(TIRPC, libtirpc)：pkgconf 的 pkg-config 二进制在
        # HMDFS 无执行位，改用 PKG_CHECK_MODULES 支持的环境变量直连
        # libtirpc 包（.pc 路径无关）
        for d in sorted(glob.glob(os.path.join(
                os.environ.get("CONAN_HOME", ""), "p", "libti*", "p"))):
            if os.path.isfile(os.path.join(d, "lib", "libtirpc.a")) or \
                    os.path.isfile(os.path.join(d, "lib", "libtirpc.so")):
                os.environ.setdefault("TIRPC_CFLAGS",
                                      f"-I{os.path.join(d, 'include', 'tirpc')}")
                os.environ.setdefault("TIRPC_LIBS",
                                      f"-L{os.path.join(d, 'lib')} -ltirpc")
                break
        self.run(f'CONFIG_SHELL=/bin/sh sh "{conf}" {args}')
        # VPATH 构建：Makefile.am 的 AM_CFLAGS=-Icompat 是相对路径，make 在
        # build 子目录执行时解析到错误位置（sys/tree.h not found）——改为
        # 指向源码 compat/ 的绝对路径。
        mk = os.path.join(self.build_folder, "Makefile")
        if os.path.isfile(mk):
            with open(mk, encoding="utf-8") as f:
                mk_text = f.read()
            if "-Icompat" in mk_text:
                mk_abs = os.path.join(self.source_folder, "compat")
                with open(mk, "w", encoding="utf-8") as f:
                    f.write(mk_text.replace("-Icompat", f"-I{mk_abs}"))
                self.output.info(f"Makefile: -Icompat -> -I{mk_abs}（VPATH 修正）")
        # E074: 真机 make -j 并行受 FIFO jobserver 限制，统一 -j1
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # BSD-3-Clause 许可证文件
        license_src = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(license_src):
            copy(self, "LICENSE", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))
        # 清理 libtool 归档（模块以裸 .so 形式安装，无需 .la）
        for la in glob.glob(os.path.join(self.package_folder, "**", "*.la"), recursive=True):
            os.remove(la)

    def package_info(self):
        # 命令行工具在 bin/；LD_PRELOAD 模块在 lib/trickle/（编译进
        # trickle 主程序的 LIBDIR 常量，运行时由 trickle 自行拼接查找）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
