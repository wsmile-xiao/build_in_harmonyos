#!/usr/bin/env python3
"""Conan recipe — minimodem 0.24 (autotools application).

minimodem 是通用软件 FSK 音频调制解调器（Bell103/202、V.21、RTTY、Caller-ID、
SAME 等波特模式）。上游用 autotools 构建，PKG_CHECK_MODULES(DEPS, [fftw3f
sndfile]) 解析依赖；音频后端按 USE_PULSEAUDIO/USE_ALSA/USE_SNDFILE 宏编译
（src/simpleaudio*.c 各自整文件 #if 包裹）。

适配要点（根因与证据见 notes.md / reports/）：

- 依赖：ohpcd 制品仓的 libsndfile/1.2.2 与 fftw/3.3.10.3（armv8/clang15/OHOS
  二进制，conan list 实查）。fftw 制品只有双精度构建（configure 无
  --enable-single，包内只有 libfftw3 + fftw3.pc），而上游用单精度 fftw3f →
  补丁 0001 把依赖与 src/fsk.{h,c} 的 fftwf_* API 机械替换为 fftw_*（double
  变换，幅值口径不变）。W0 三判据（版本可得 / 硬依赖 / 平台可移植）全过。
- 可选依赖缺省禁用：--without-alsa --without-pulseaudio（alsa 在 ohpcd 无
  制品；pulseaudio 虽有制品但音频设备后端在无头构建/测试环境不可用）。sndfile
  后端保留（--file 模式为上游测试与 test_package 的唯一 I/O 通道）。
- 自举：源 tarball 是 git tag 自动打包，不含 configure/aclocal.m4/Makefile.in，
  build() 内按 aclocal → autoconf → autoheader → automake --add-missing 链
  生成（abiword-plugin-* 先例）。automake 来自 tool_requires（CI worker 的
  PATH 没有 automake，设备 harmonybrew 的 automake 不进 conanbuild 环境，
  统一用制品仓 automake/1.18，其 buildenv_info 导出 ACLOCAL/AUTOMAKE/
  ACLOCAL_PATH/PERL5LIB 并已把 HNP pkg-config 的 pkg.m4 目录纳入 ACLOCAL_PATH）。
- E007：automake --add-missing 拷入的 config.guess 不识别 HarmonyOS（实测
  exit 1 "unable to guess"），build() 内幂等补 HarmonyOS 分支（fftw/3.3.10.3
  patches/0003 同款），不传 --build/--host 交叉参数。
- E011/E114：configure 的 umask 077 与 config.status 的 ac_tmp=$tmp 在
  HMDFS/鸿蒙安全框架下失败，build() 内做 umask 022 替换 + 把 ac_tmp 指向
  配方预建的可写目录并中和其退出 trap（abiword-plugin-eml 先例）。
- 上游测试：tests/ 的 28 个 *.test 经 automake 并行 harness（test-driver）
  由 `make check` 驱动，全部只走 --file WAV 往返（纯用户态，不需要音频设备）。
  补丁 0002 修测试脚本的可运行性（解释器路径 + /tmp 只读）。测试工作目录的
  TMPDIR 指向构建目录下的可写目录。
- 交付物为单个可执行文件 bin/minimodem（package_type="application"），
  conan-verify 的 G4/L2/L4/L5 对该形态整组跳过，按口径在
  reports/conan-verify-supplement.md 人工补测（产物清单/真跑/readelf/聚合 sha256）。
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class MinimodemConan(ConanFile):
    name = "minimodem"
    version = "0.24"
    description = ("General-purpose software FSK audio modem "
                   "(Bell103/202, V.21, RTTY, TDD, Caller-ID, SAME)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/kamalmostafa/minimodem"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("audio", "fsk", "modem", "telephony")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "minimodem is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "OHOS builds require armv8/aarch64")

    def requirements(self):
        # W0 conan list -r=ohpcd 实查（armv8/Release/OHOS 二进制在场）：
        # libsndfile/1.2.2（上游 sndfile.pc 依赖，--file 模式必需）、
        # fftw/3.3.10.3（上游 fftw3f 依赖；制品只有双精度 → 补丁 0001 适配）。
        self.requires("libsndfile/1.2.2")
        self.requires("fftw/3.3.10.3")

    def build_requirements(self):
        # git-tag tarball 无 configure：build() 内自举（aclocal/autoconf/
        # autoheader/automake）。CI worker 的 PATH 没有 automake（设备
        # harmonybrew 的 automake 也进不了 conanbuild 环境）→ 一律用制品仓
        # automake/1.18（abiword-plugin-* 等 11 个配方同先例）。autoconf 2.73/
        # autoheader/pkg-config 0.29.2 来自 HNP 基线（/data/service/hnp/bin，
        # 设备与 CI worker 的 PATH 都含该目录）。
        # 注意 tool_requires 按 *build* profile 解析，conan create 需同时传
        # -pr:h 与 -pr:b（conan-verify 已按此口径调用）。
        self.tool_requires("automake/1.18")

    def layout(self):
        # in-source 构建（build==source）：上游 tests/Makefile.am 用
        # `TESTS = $(sort $(wildcard *.test))` 且脚本以 cwd 相对路径读
        # testdata/*.txt、exec ./self-test、回退 ../src/minimodem——全部依赖
        # 「构建目录 == 源码目录」的树内语义。basic_layout 默认 VPATH
        # （build-release/）下 wildcard 落空（实测 TOTAL: 0）且测试数据缺失。
        basic_layout(self, src_folder=".", build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps 生成 fftw3.pc / sndfile.pc（pkg-config 名称来自各包
        # 的 pkg_config_name 属性：fftw 包从包内 lib/pkgconfig/fftw3.pc 取
        # "fftw3"，libsndfile 为 "sndfile"），供 configure 的
        # PKG_CHECK_MODULES(DEPS, [fftw3 sndfile]) 解析。
        PkgConfigDeps(self).generate()
        # VirtualBuildEnv：把 tool_requires(automake) 的 bin 目录与
        # ACLOCAL/AUTOMAKE/ACLOCAL_PATH/PERL5LIB 注入 conanbuild 环境
        #（必须先于 tc.generate()，先例见 abiword-plugin-eml）。
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # 可选音频后端缺省禁用：alsa（ohpcd 无制品）、pulseaudio（无头环境
        # 不可用）。sndfile/benchmarks 沿用上游默认（开启）。
        tc.configure_args.append("--without-alsa")
        tc.configure_args.append("--without-pulseaudio")
        tc.generate()

    def build(self):
        # 1. 补丁先打（0001 改 configure.ac，必须在 autoconf 之前生效）
        apply_conandata_patches(self)
        # 2. 自举生成 configure / Makefile.in / test-driver 等
        self._bootstrap()
        # 3. E007/E011/E114：对自举产物做鸿蒙平台修复
        self._ohos_configure_fixes()
        # 4. 配置 + 构建（TMEDIR/PR PKG_CONFIG_PATH 注入，见 _runtime_env）
        autotools = Autotools(self)
        with self._runtime_env().vars(self).apply():
            autotools.configure()
            autotools.make(args=["-j4"])
            # 5. 上游测试：tests/Makefile.am 的 TESTS = 28 个 *.test，
            #    automake 并行 harness（test-driver）驱动，串行执行。
            self.run("make check -j1", cwd=self.build_folder,
                     env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        with self._runtime_env().vars(self).apply():
            autotools.install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        _bin = os.path.join(self.package_folder, "bin", "minimodem")
        if not os.path.isfile(_bin):
            raise ConanException(
                "package() 交付物缺失：bin/minimodem 未安装成功")

    def package_info(self):
        # application 包：只交付 bin/minimodem（+ man7 页），无库/头文件。
        self.cpp_info.bindirs = ["bin"]

    # ── helpers ──────────────────────────────────────────────────────

    def _bootstrap(self):
        """aclocal → autoconf → autoheader → automake --add-missing。

        必须走 conanbuild 环境：tool_requires(automake/1.18) 的 ACLOCAL/
        AUTOMAKE/ACLOCAL_PATH/PERL5LIB 只在该环境生效（abiword-plugin-eml
        先例；aclocal 是 perl 脚本，包内 Automake/Config.pm 的死前缀由其
        PERL5LIB 重定位补齐）。pkg.m4（PKG_CHECK_MODULES 宏）由 automake
        包的 ACLOCAL_PATH 指到 HNP pkg-config 的 share/aclocal。
        """
        self.run('"${ACLOCAL:-aclocal}" --force', cwd=self.source_folder,
                 env="conanbuild")
        self.run("autoconf -o configure configure.ac",
                 cwd=self.source_folder, env="conanbuild")
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException("autoconf 未能生成 configure")
        self.run("autoheader", cwd=self.source_folder, env="conanbuild")
        if not os.path.exists(os.path.join(self.source_folder,
                                           "config.h.in")):
            # autoheader 偶发空产出时 touch 兜底（abiword 先例）
            open(os.path.join(self.source_folder, "config.h.in"), "a").close()
        self.run('"${AUTOMAKE:-automake}" --add-missing --foreign',
                 cwd=self.source_folder, env="conanbuild")

    def _ohos_configure_fixes(self):
        """对自举产物做鸿蒙平台修复（全部幂等）。"""
        src = self.source_folder

        # E490：tarball/automake 拷入的脚本在 HMDFS 可能丢执行位，显式恢复
        for _s in ("configure", "config.guess", "config.sub", "install-sh",
                   "missing", "depcomp", "compile", "test-driver"):
            _p = os.path.join(src, _s)
            if os.path.exists(_p):
                os.chmod(_p, os.stat(_p).st_mode | 0o111)

        # E007：config.guess 不识别 HarmonyOS（uname -s = HarmonyOS，实测
        # 走到 fallback 前直接 exit 1 "unable to guess system type"）。
        # 幂等补 HarmonyOS 分支（fftw/3.3.10.3 patches/0003 同款判定），输出
        # aarch64-unknown-linux-ohos 三元组（config.sub 认 linux-ohos*）。
        # 锚点双形态兼容：fftw 3.3.10 老版是带引号的
        # case "$UNAME_MACHINE:..." in，automake 1.18 拷入的是不带引号的
        # case $UNAME_MACHINE:... in（两者都已实测）。
        _cg = os.path.join(src, "config.guess")
        if os.path.exists(_cg):
            with open(_cg, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if "*:HarmonyOS:*:*" not in text:
                import re as _re
                _m = _re.search(
                    r'^case\s+("?)\$UNAME_MACHINE:\$UNAME_SYSTEM:'
                    r'\$UNAME_RELEASE:\$UNAME_VERSION\1\s+in\s*$',
                    text, _re.M)
                if not _m:
                    raise ConanException(
                        "E007: config.guess 主 case 锚点未找到，"
                        "automake 版本可能变化")
                _branch = (
                    _m.group(0) + "\n"
                    + "    *:HarmonyOS:*:*)\n"
                    + "\tcase \"$UNAME_MACHINE\" in\n"
                    + "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                    + "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                    + "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                    + "\t    i?86)         MACHINE=i686 ;;\n"
                    + "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                    + "\tesac\n"
                    + "\techo \"${MACHINE}-unknown-linux-ohos\"\n"
                    + "\texit 0\n"
                    + "\t;;\n")
                text = text[:_m.start()] + _branch + text[_m.end():]
                with open(_cg, "w", encoding="utf-8") as f:
                    f.write(text)
            # 修复后立即自证：能识别出 ohos 三元组才继续
            # （绝对路径调用，规避 OHOS Python 裸命令名不搜 PATH 的问题）
            import subprocess
            r = subprocess.run([_cg], capture_output=True, text=True)
            if r.returncode != 0 or "ohos" not in (r.stdout or ""):
                raise ConanException(
                    "E007: config.guess 修复后仍无法识别本平台（rc=%s, "
                    "stdout=%r）" % (r.returncode, (r.stdout or "")[:80]))

        # E011 + E114：configure 的临时目录处理在 HMDFS/鸿蒙安全框架下失败
        # （umask 077 建的目录子进程不可写；AS_TMPDIR 的 ac_tmp=$tmp 在
        # build 目录新建 ./confXXXXXX 被拦）。双修：umask 022 替换 + ac_tmp
        # 指向配方主进程预建的可写目录 + 中和退出时的 rm -fr trap。
        _fixed_tmp = os.path.join(self.build_folder, "ac-tmp")
        os.makedirs(_fixed_tmp, exist_ok=True)
        _cfg = os.path.join(src, "configure")
        with open(_cfg, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        text = text.replace("umask 077", "umask 022")
        if "ac_tmp=$tmp" in text:
            text = text.replace("ac_tmp=$tmp",
                                "ac_tmp=%s" % _fixed_tmp)
            _old_trap = ('{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } '
                         '&& exit $exit_status')
            text = text.replace(_old_trap, "exit $exit_status")
        with open(_cfg, "w", encoding="utf-8") as f:
            f.write(text)

    def _runtime_env(self):
        """configure/build/check 期间的环境：可写 TMPDIR（/tmp 只读、
        /var/tmp 不存在）+ PkgConfigDeps 生成目录的 PKG_CONFIG_PATH
        （conan 不自动注入，configure 的 PKG_CHECK_MODULES 需要）。"""
        env = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        # ac-tmp 同步保底：若 configure 退出 trap 把它清掉（E114 中和失败时），
        # 后续 make/check 阶段也能即时重建
        os.makedirs(os.path.join(self.build_folder, "ac-tmp"), exist_ok=True)
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # host 依赖共享库的运行期查找：conanbuild 环境只有 build 上下文，
        # `make check` 真跑 ../src/minimodem 时加载器找不到 libfftw3.so.3
        # （实测 28/28 报 "Error loading shared library libfftw3.so.3"）。
        # 用环境注入而非 -rpath——避免把 conan 缓存绝对路径烘焙进交付物
        # （E537 红线：published 产物不得携带机器私有路径）。
        for _dep in self.dependencies.values():
            _pf = getattr(_dep, "package_folder", None)
            if not _pf:
                continue
            for _l in _dep.cpp_info.libdirs:
                _abs = _l if os.path.isabs(_l) else os.path.join(_pf, _l)
                env.prepend_path("LD_LIBRARY_PATH", _abs)
        return env
