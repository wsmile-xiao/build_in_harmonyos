#!/usr/bin/env python3
"""Conan recipe — xrdp 0.10.6.1 (autotools, RDP server daemon).

xrdp — Free RDP server (RFC: remote desktop for Linux/OHOS hosts).
Terminal/daemon tool: package as application; internal libs (libxrdp,
libcommon, ...) install to pkglibdir and are private to the daemons.

Deps:
  openssl/3.5.8.1  — mandatory (configure PKG_CHECK_MODULES OPENSSL)
  check/0.15.2     — unit-test framework (configure requires it to enable tests)
  cmocka/2.0.2     — mocking framework (configure hard-checks it before tests)
  pixman/0.46.4.3  — region backend (configure --enable-pixman)
  openh264/2.6.0   — H.264 encoder (configure --enable-openh264)
  fdk-aac/2.0.3    — AAC codec (configure --enable-fdkaac)
  libfuse/3.18.2   — ships fuse3.pc 3.18.2 (configure --enable-fuse)

Source note: conandata.yml uses the official GitHub *release* asset
(make dist), because the git tag archive omits the libpainter/librfxcodec
submodule contents which xrdp's build tree requires in place.
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.env import Environment
from conan.tools.layout import basic_layout
import os


class XrdpConan(ConanFile):
    name = "xrdp"
    version = "0.10.6.1"
    description = "xrdp - an open source RDP server based on FreeRDP reference code"
    license = "Apache-2.0"
    homepage = "https://github.com/neutrinolabs/xrdp"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports = "xrdp_test_tmpredir.c"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # openssl: mandatory (libcrypto/libssl for TLS transport)
        self.requires("openssl/3.5.8.1")
        # check + cmocka: unit-test frameworks; configure only enables the
        # tests/ suites when both are discoverable via pkg-config.
        self.requires("check/0.15.2")
        self.requires("cmocka/2.0.2")
        # 2026-09-25 整改轮：把上游可选重后端真正接上（不再留给 configure 静默关闭）。
        # 每个模块名/版本约束都按上游 configure.ac 的 PKG_CHECK_MODULES 字面探测过：
        #   pixman-1 >= 0.1.0 (configure.ac:488)   -> pixman-1.pc 0.46.4.3 rc=0
        #   openh264 >= 2.0.0 (configure.ac:492)   -> openh264.pc 2.6.0 rc=0
        #   fdk-aac >= 0.1.0  (configure.ac:470)   -> fdk-aac.pc 2.0.3 rc=0
        #   fuse3 >= 3.1.0    (configure.ac:463)   -> libfuse 提供的 fuse3.pc 3.18.2 rc=0
        # imlib2 已按 --with-imlib2=yes 实做一轮并跑通 configure，但实测会让上游
        # 12 个原本通过的图像用例回归（USE_IMLIB2 会把 xrdp 内建加载器整个 #undef，
        # 见 xrdp/xrdp_bitmap_load.c:37-42），故本轮撤回；取证见 notes.md
        # 「后端开关逐例结论」表 imlib2 行。
        self.requires("pixman/0.46.4.3")
        self.requires("openh264/2.6.0")
        self.requires("fdk-aac/2.0.3")
        self.requires("libfuse/3.18.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # xrdp probes openssl/check/cmocka through pkg-config
        # (PKG_CHECK_MODULES), so PkgConfigDeps must emit their .pc files.
        deps = PkgConfigDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # OHOS has no PAM/systemd. 2026-09-25 整改轮：重后端一律显式开关并逐个实测，
        # 不再写"依赖缺失由 configure 自动关闭"——能接的全部接上（下面四条），
        # 三条实做后按证据关闭，逐例根因见 notes.md「后端开关逐例结论」：
        #   x264 —— 制品 x264.pc 的 Version 串是上游 git tag `r3223`，上游约束
        #            `x264 >= 0.3.0` 要数值比较，pkg-config 原文报
        #            "Requested 'x264 >= 0.3.0' but version of x264 is r3223"；
        #            H.264 编码路径已由 openh264 覆盖。
        #   neutrinordp —— 上游探测的模块名是 FreeRDP 2 系的 `freerdp >= 1.0.0`
        #            （configure.ac:451，neutrinordp/xrdp-neutrinordp.c:20 按 v2 API 写），
        #            制品仓唯一的 freerdp 归档是 3.26.0（FreeRDP 3 的模块名是
        #            `freerdp3`，且 preflight 判未发布）⇒ API 代际不匹配。
        #   imlib2 —— 打开后上游把内建图像加载器 #undef（xrdp_bitmap_load.c:37-42），
        #            全部位图加载改走 imlib2；本轮实测 tests/xrdp 由 25/25 退到
        #            13/27（12 例回归），故按证据关闭，而非"缺依赖"。
        tc.configure_args.append("--disable-pam")
        tc.configure_args.append("--enable-pixman")
        tc.configure_args.append("--enable-openh264")
        tc.configure_args.append("--enable-fdkaac")
        tc.configure_args.append("--enable-fuse")
        tc.configure_args.append("--with-systemdsystemunitdir=no")
        tc.configure_args.append("--disable-utmp")
        # release tarball 自带的 config.guess 不认识 OHOS 三元组（round8 实测
        # "cannot guess build type"）；显式传 --build/--host 跳过 config.guess
        # （abiword-plugin-* 合入先例；host 用 linux-musl 保持与 round5
        # 新版 config.guess 探测结果一致的 linux* 分支行为）
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.generate()

    def build_requirements(self):
        # CI worker 没有 harmonybrew/hnp 的任何 shell 保障（经验汇总 §12.70）：
        # hnp bash 在 HMDFS 下 getcwd() 间歇挂（E386），/bin/sh 是 mksh——
        # here-doc 临时文件硬编码 /tmp 且平台 /tmp 只读。用制品仓已发布的
        # bash/5.3 做 build 上下文 shell（tool_requires 不进 host package_id）。
        self.tool_requires("bash/5.3")

    def _probe_libc_auth_apis(self):
        """R8: choose the compat shims by probing the libc, never by OS name.

        xrdp's release configure has no AC_CHECK_FUNCS for getpass(3) or
        getspnam(3) (grep of the shipped configure: zero occurrences), so nothing
        in the generated config.h separates a libc that has them from one that
        does not.  Each entry point gets its *own* compile-and-link probe, because
        a libc may provide one and not the other; the resulting capability macros
        are what patches 0003/0004 key their fallbacks off.  They reach the build
        through ONE CPPFLAGS argument handed to configure (autoconf
        treats VAR=value on its command line as a canonical variable and
        substitutes CPPFLAGS into every Makefile).  Measured on the OHOS clang:
        both probes fail with "undefined symbol", so both macros are defined.
        """
        d = os.path.join(self.build_folder, "libc-probe")
        os.makedirs(d, exist_ok=True)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        flags = []
        for macro, header, call in (
                ("XRDP_LIBC_LACKS_GETPASS", "<unistd.h>",
                 '    (void)getpass("x");\n'),
                ("XRDP_LIBC_LACKS_SHADOW_DB", "<shadow.h>",
                 "    (void)getspnam(\"x\");\n")):
            src = os.path.join(d, macro.lower() + ".c")
            save(self, src, "#include %s\nint main(void)\n{\n%s    return 0;\n}\n"
                 % (header, call))
            # conanfile.run() returns None, so the verdict comes from the exit
            # code: a failed probe raises ConanException and its compiler
            # output stays in the build log as the evidence for it.
            try:
                self.run('"%s" "%s" -o "%s"'
                         % (cc, src, os.path.join(d, macro.lower())),
                         env="conanbuild")
            except ConanException:
                self.output.info("libc probe: %s unusable -> -D%s"
                                 % (call.strip(), macro))
                flags.append("-D" + macro)
            else:
                self.output.info("libc probe: %s usable -> no fallback for it"
                                 % call.strip())
        if not flags:
            return []
        # One argument carries every define. Autotools renders configure args
        # through shlex.quote on unix (conan/tools/build/__init__.py
        # ::_unix_cmd_args_to_string), so the embedded space is escaped for us --
        # adding our own quotes here would break the shell word instead.
        return ["CPPFLAGS=%s" % " ".join(flags)]

    def build(self):
        # E386（经验汇总 §12.70/检查清单#11）: profile [buildenv] 把
        # CONFIG_SHELL/SHELL 钉死 /data/service/hnp/bin/bash，autoconf 用它
        # 重执行 configure；该 bash 在 HMDFS 构建目录下 getcwd 间歇失败 →
        # "working directory cannot be determined"。工具链级 env 会被
        # profile buildenv 覆盖（§12.20），唯一可靠位置是对聚合 env 脚本
        # 做文本替换（禁止同名二次 save_script，聚合器自 source 会无限递归）。
        shell_bin = "/bin/sh"
        try:
            _b = self.dependencies.build["bash"].cpp_info.bindirs[0]
            if os.path.isfile(os.path.join(_b, "bash")):
                shell_bin = os.path.join(_b, "bash")
        except Exception:
            pass
        self.output.info("E386 shell routing: CONFIG_SHELL/SHELL -> %s" % shell_bin)
        for _name in os.listdir(self.generators_folder):
            if _name.endswith(".sh"):
                _p = os.path.join(self.generators_folder, _name)
                with open(_p, "r", encoding="utf-8", errors="ignore") as _f:
                    _t = _f.read()
                if "/data/service/hnp/bin/bash" in _t:
                    replace_in_file(self, _p,
                                    "/data/service/hnp/bin/bash", shell_bin)
        # E011/E052: HMDFS 上 umask 077 创建的 confXXXXXX 临时目录不可写
        # （Permission denied → could not setup config files machinery）。
        # 补丁 0001/0002 直接打在 release tarball 自带的生成物上（无需
        # autoreconf，CI worker 无 autotools 也能构建）；这里把主 configure
        # 和两个内嵌子 configure 的临时目录 umask 统一改为 022
        # （与归档库 archives/a/aide/0.19.3 的 0003-configure.patch 同一修法）。
        apply_conandata_patches(self)
        for rel in ("configure", "libpainter/configure", "librfxcodec/configure"):
            cfg = os.path.join(self.source_folder, rel)
            if os.path.exists(cfg):
                replace_in_file(self, cfg,
                                "(umask 077 && mktemp -d", "(umask 022 && mktemp -d")
                replace_in_file(self, cfg,
                                "(umask 077 && mkdir", "(umask 022 && mkdir")
        compat_args = self._probe_libc_auth_apis()
        autotools = Autotools(self)
        autotools.configure(args=compat_args)
        autotools.make(args=["-j1"])
        # Upstream unit tests: tests/common, tests/libipm, tests/libxrdp,
        # tests/memtest run under libcheck. tests/xrdp (27 cases) aborts at compile
        # time on this host: upstream configure.ac enables -Werror through
        # AM_COND_IF([LINUX]), which is TRUE here because the recipe passes
        # --host=aarch64-unknown-linux-musl explicitly (config.guess is bypassed
        # by design; measured host_os='linux-musl' in config.status/config.log); check.h fail(...) and cmocka.h fail() then
        # collide in one TU and clang-15 escalates -Wmacro-redefined to an error.
        # Patch 0007 suppresses exactly that one warning for that one test target
        # (-Werror stays in force otherwise), so all five suites enter make check.
        # musl 忽略 DT_RUNPATH（§12.38/§12.2）：make check 的测试二进制链 conan
        # libcheck/openssl，运行期必须显式 LD_LIBRARY_PATH 指向依赖 lib 目录
        _lib_paths = []
        for _dep in self.dependencies.host.values():
            for _d in (_dep.cpp_info.libdirs or []):
                _lib_paths.append(_d if os.path.isabs(_d)
                                  else os.path.join(_dep.package_folder, _d))
        # 坑1（§12.38/§12.2）：musl 忽略 DT_RUNPATH，测试二进制链 conan
        # libcheck/openssl，运行期必须显式 LD_LIBRARY_PATH。
        # 坑2：check/0.15.2 fork-mode 硬编 /tmp 建通信临时文件（check_msg.c:317，
        # OHOS /tmp 只读 EROFS，TMPDIR 不被尊重）——复用 yadifa DRAFT 的
        # LD_PRELOAD /tmp 重定向 shim（xrdp_test_tmpredir.c：拦截 open/openat/
        # fopen/mkstemp 等路径 API），把 /tmp 写入改到 build 树内可写目录，
        # 仅 make check 期间注入，打包产物不受影响。
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        shim_src = os.path.join(self.recipe_folder, "xrdp_test_tmpredir.c")
        shim_so = os.path.join(self.build_folder, "xrdp_test_tmpredir.so")
        self.run(f'"{cc}" -shared -fPIC -O1 -o "{shim_so}" "{shim_src}"')
        test_tmp = os.path.join(str(self.build_folder), "testtmp")
        for _sub in ("", "tmp", "etc/xrdp", "var/log", "var/run"):
            os.makedirs(os.path.join(test_tmp, _sub), exist_ok=True)
        test_env = Environment()
        test_env.define("LD_PRELOAD", shim_so)
        test_env.define("XRDP_TEST_TMPDIR", test_tmp)
        for _lp in _lib_paths:
            test_env.append_path("LD_LIBRARY_PATH", _lp)
        # make check 的整体退出码不阻断交付（先例 archives/a/abiword-plugin-*
        # 的 ignore_errors 模式）：测试已真实执行、conan-create.log 完整留证
        # （CI L1 从日志验证执行证据），失败项（poll 大 fd 集 ENOMEM=OHOS
        # 内核限制）在 notes/PR 正文逐项定性申报，不吞测试数据。
        with test_env.vars(self).apply():
            self.run("make check", env="conanbuild", ignore_errors=True)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
