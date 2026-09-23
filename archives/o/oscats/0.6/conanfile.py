#!/usr/bin/env python3
"""Conan recipe for oscats 0.6 (OSCATS -- Open-Source Computerized Adaptive Testing System).

OSCATS 是 IRT（项目反应理论）自适应测验/仿真库：用 GObject 框架的面向对象 C
实现题项模型（1PL/2PL/3PL/nominal/GR/GPC/PC/hlgr/dina/nida）、能力估计
（MLE/EAP 等，走 GSL 数值 / 线性代数 / 积分）、选题算法（随机/最接近难度/
最大 Fisher/最大 KL/分层）与测验管理；另有 Python/Perl/PHP/Java 绑定
（默认关闭）。本配方只构建核心库 src/liboscats。

OHOS 适配要点：
- layout 必须 basic_layout(src_folder=".", build_folder=".")：默认 build_folder 是
  build-<build_type>，os.getcwd()（= build_folder）与 source_folder 分离 → configure
  变 out-of-source，配方里按 self.build_folder 定位的源码树文件（config/config.sub、
  configure）全部落空。2026-09-11 CI #44595 实测该坑。
- 2009 版 config.sub 不认识 aarch64（实测 aarch64-linux → not recognized），
  用 compat/config.sub（2022 FSF 版）覆盖 config/config.sub（configure.in 有
  AC_CONFIG_AUX_DIR([config])，aux 目录是 config/，不是构建根）；configure 显式
  --build/--host=aarch64-linux → 不触发 config.guess（2010 版同样不认 aarch64）。
- glib 2.80 起从 glib/gtypes.h 移除 G_MININT/G_MAXINT/G_MINUINT/G_MAXUINT/
  G_MAXDOUBLE/G_MINDOUBLE 等经典常量（改用 C99 limits/float）。oscats 0.6
  用它们做属性区间（1, G_MAXUINT, ...）与数值哨兵（±G_MAXDOUBLE / G_MINDOUBLE）。
  以 compat/glib-compat.h + `-include` 注入等价定义（gtypes.h 不引 limits/float，
  故必须在 -include 里自带）。
- src/liboscats/Makefile.am 把 `-Wall -Werror` 硬编码进 liboscats_la_CFLAGS；
  glib 2.84 下 G_TYPE_INSTANCE_GET_CLASS 等弃用宏的告警会变硬错误。
  CFLAGS 排在 liboscats_la_CFLAGS 之后，追加 -Wno-error 即可覆盖。
- -fcommon：2011 年的头文件里 tentative definition 依赖 -fcommon（gcc10/clang15
  默认 -fno-common 会报 multiple definition）。
- gsl 由上游 AX_PATH_GSL 经 gsl-config 脚本定位（gsl 普通 requires 的 bin/ 不在
  PATH 上）→ 显式设 GSL_CONFIG 指向**构建目录里改写过的副本**（AC_PATH_PROG 尊重
  预设值）。制品仓 gsl/2.8 的 bin/gsl-config 把前缀写死为 /，`--cflags` 输出
  `-I//include`、`--libs` 输出 `-L//lib`，AX_PATH_GSL 会原样抄进 GSL_CFLAGS，
  而 --disable-gsltest 又跳过自检 → 编译 models/*.c 时
  `fatal error: 'gsl/gsl_vector.h' file not found`（CI #44619）。故复制到构建目录
  后就地改写路径（不动共享缓存里的依赖包）。
  glib 由 AM_PATH_GLIB_2_0 → PKG_CHECK_MODULES(glib-2.0, gobject-2.0) →
  PKG_CONFIG_PATH 注入依赖的 pkgconfig 目录 + PkgConfigDeps 生成的 .pc。
  两个宏的 compile+run 自检（glibtest/gsltest）在交叉环境用 --disable-*-test 关掉。
- OHOS musl 的 sys/select.h 默认声明 POSIX select(2)；oscats 四个选题算法各自的
  文件内 `static gint select(...)` 回调与之冲突，clang 报硬错误（-Wno-error 无法
  降级）。用 patches/0001-rename-select-signal-callbacks.patch 把私有定义改名
  select_cb（GObject 信号名 "select" 不变）。2026-09-11 CI #44620 实测。
- 只编 src/liboscats：`make -C src`（不能用 `make SUBDIRS=src`，命令行变量会
  递归进 src/ 覆盖其 SUBDIRS=liboscats → cd src 不存在而失败）；bindings/
  （python/perl/php/java 默认全关）与 doc/（gtk-doc）不参与，--disable-gtk-doc 双保险。
- SHELL/CONFIG_SHELL 必须实测选定并统一：ohos-aarch64 profile 把两者都指向
  HNP bash（/data/service/hnp/bin/bash），该 bash 在 HMDFS 上 getcwd 失败
  （shell-init/chdir "cannot access parent directories"）。更致命的是
  configure 侧与 make 侧 shell 不一致时，libtool 的 ECHO 探测会写出
  `print -r --`，而 make 侧 shell 无 print 内建 → config.status 报 60+ 次
  `print: command not found` → 生成的 libtool 引号失衡 →
  `libtool: line 315: syntax error near unexpected token '}'`。2026-09-11
  CI #44609 实测。修法见 _pick_working_shell()（先例：blogc 0.20.1）。
- TMPDIR 不能指向 conan 构建目录（HMDFS）：make 4.4+ 在 $TMPDIR 下 mkfifo
  建 jobserver 命名管道，HMDFS 不支持 → `jobserver mkfifo: ...: Operation
  not permitted`。但 CI 沙箱默认 TMPDIR 又可能不可写（clang 链接 conftest
  报 "C compiler cannot create executables"）。修法见 _pick_tmpdir()：逐候选
  实测「可写 + mkfifo 可用」。
- 上游 0 自动化测试（Makefile.am 全仓无 TESTS/check_PROGRAMS），消费侧契约由
  test_package 承担。
"""
from conan import ConanFile
from conan.tools.files import (copy, get, load, save,
                               apply_conandata_patches, export_conandata_patches)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
import os
import shutil
import subprocess


class OscatsConan(ConanFile):
    name = "oscats"
    version = "0.6"
    description = "OSCATS - Open-Source Computerized Adaptive Testing System (GObject/GSL IRT library)"
    license = "GPL-3.0-or-later"
    homepage = "https://code.google.com/archive/p/oscats/"
    url = ""  # CI fills this
    topics = ("adaptive-testing", "psychometrics", "irt", "gobject", "gsl")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        copy(self, "compat/*", self.recipe_folder, self.export_sources_folder)
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("gsl/2.8")

    def layout(self):
        # build_folder 必须显式设 "."：basic_layout 默认把 build 目录设为
        # build-<build_type>（如 build-release），于是 os.getcwd()（= build_folder）
        # 与 source_folder 分离，configure 变成 out-of-source、配方里所有按
        # self.build_folder 定位的源码树文件（config/config.sub、configure、
        # oscats.pc、src/liboscats/.libs）全部落空。2026-09-11 CI #44595 实测：
        # config.sub 替换被 os.path.isdir 守卫静默跳过，configure 仍用 2009 版
        # config.sub → "machine 'aarch64' not recognized"。强制 in-source 构建
        # 让 build_folder == source_folder。先例：kismet、ttfautohint。
        basic_layout(self, src_folder=".", build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=aarch64-linux",
            "--host=aarch64-linux",
            "--disable-glibtest",
            "--disable-gsltest",
            "--disable-gtk-doc",
            "--disable-gtk-doc-html",
        ])
        tc.extra_cflags.append("-fcommon")
        # liboscats_la_CFLAGS 自带 -Wall -Werror；CFLAGS 在其后 → -Wno-error 生效
        tc.extra_cflags.append("-Wno-error")
        # glib 2.80 移除的 G_MIN*/G_MAX* 常量（见 compat/glib-compat.h）
        tc.extra_cflags.extend([
            "-include",
            os.path.join(self.source_folder, "compat", "glib-compat.h"),
        ])
        tc.generate()
        PkgConfigDeps(self).generate()
        tmp = self._pick_tmpdir()
        self.output.info("using TMPDIR: %s" % tmp)
        self._pick_working_shell()

    def _pick_tmpdir(self):
        """挑一个既能写、又支持 mkfifo 的 TMPDIR。

        CI 沙箱默认 TMPDIR 可能不可写（clang 链接 conftest 报 "C compiler
        cannot create executables"），但把 TMPDIR 指到 conan 构建目录内
        （HMDFS）会让 make 4.4+ 的 jobserver mkfifo 失败（"jobserver mkfifo:
        ...: Operation not permitted"，CI #44609）。逐候选实测「可写文件 +
        mkfifo 成功」，取第一个合格者；都不可用则退回构建目录内 .conan_tmp
        以保证 clang 可写。先例：blogc 0.20.1 用 ~/tmp。
        """
        build_dir = self.build_folder
        fallback = os.path.join(build_dir, ".conan_tmp")
        cands = [os.path.expanduser("~/tmp"),
                 "/data/storage/el2/base/cache",
                 os.environ.get("TMPDIR") or "",
                 fallback]
        for c in cands:
            if not c or os.path.abspath(c) == os.path.abspath(fallback):
                continue
            try:
                os.makedirs(c, exist_ok=True)
                p = os.path.join(c, ".oscats_probe")
                with open(p, "w") as f:
                    f.write("x")
                os.remove(p)
                fifo = os.path.join(c, ".oscats_probe_fifo")
                try:
                    os.mkfifo(fifo)
                    os.remove(fifo)
                except (OSError, AttributeError) as e:
                    self.output.info("tmpdir %s: no mkfifo (%s)" % (c, e))
                    continue
            except OSError as e:
                self.output.info("tmpdir %s not writable: %s" % (c, e))
                continue
            self.buildenv.define("TMPDIR", c)
            os.environ["TMPDIR"] = c
            return c
        os.makedirs(fallback, exist_ok=True)
        self.buildenv.define("TMPDIR", fallback)
        os.environ["TMPDIR"] = fallback
        return fallback

    def _pick_working_shell(self):
        """实测挑一个能 getcwd 的 shell，统一给 configure/config.status/make/libtool。

        ohos-aarch64 profile 把 SHELL/CONFIG_SHELL 指向 HNP bash
        （/data/service/hnp/bin/bash，5.3.0），其 getcwd() 在 HMDFS 上失败
        （shell-init/chdir "cannot access parent directories"）。
        更要命的是 configure 侧与 make 侧 shell 不一致：autoconf 的
        libtool ECHO 探测（`print -r -- -n` 成功即 ECHO='print -r --'）在
        configure 用的 shell 上通过，而 make 用 Makefile 里的 SHELL（HNP
        bash，无 print）跑 config.status → 60+ 次 `print: command not
        found` → LT_OUTPUT 的引号/换行处理失效 → 生成的 libtool 失衡 →
        `libtool: line 315: syntax error near unexpected token '}'`。
        把同一个（可用的）shell 写进 buildenv 的 SHELL/CONFIG_SHELL，configure
        → config.status → make → libtool 全链一致即可（先例：blogc 0.20.1）。
        """
        build_dir = self.build_folder
        if not os.path.isdir(build_dir):
            os.makedirs(build_dir, exist_ok=True)
        candidates = [shutil.which("bash"),
                      os.path.expanduser("~/.harmonybrew/bin/bash"),
                      "/bin/sh"]
        for cand in candidates:
            if not cand or not os.path.isfile(cand):
                continue
            try:
                probe = subprocess.run([cand, "-c", "pwd"], cwd=build_dir,
                                       capture_output=True, timeout=30)
            except Exception as e:  # noqa: BLE001 - probe best-effort
                self.output.info("shell probe %s error: %s" % (cand, e))
                continue
            self.output.info("shell probe %s rc=%s err=%r"
                             % (cand, probe.returncode, probe.stderr[:80]))
            bad = (b"Not supported" in probe.stderr
                   or b"getcwd" in probe.stderr
                   or b"shell-init" in probe.stderr)
            if probe.returncode == 0 and not bad:
                self.buildenv.define("SHELL", cand)
                self.buildenv.define("CONFIG_SHELL", cand)
                os.environ["SHELL"] = cand
                os.environ["CONFIG_SHELL"] = cand
                self.output.info("using working shell: %s" % cand)
                return
        self.output.warning("no getcwd-capable shell found; keeping profile SHELL")

    def _dep_pkgconfig_dirs(self):
        dirs = []
        for dep in ("glib", "gsl"):
            try:
                pf = self.dependencies[dep].package_folder
            except Exception:
                continue
            if not pf:
                continue
            for sub in ("lib/pkgconfig", "lib64/pkgconfig", "share/pkgconfig"):
                d = os.path.join(pf, sub)
                if os.path.isdir(d):
                    dirs.append(d)
        return dirs

    def build(self):
        # TMPDIR：generate() 里已实测选好（buildenv + os.environ）。这里再断言
        # 一次目录存在并写回 os.environ —— conanbuild.sh 在 CI 沙箱偶有不生效
        # 的记载（bogofilter/libgsf），os.environ 一定生效。
        _tmp = os.environ.get("TMPDIR") or ""
        if not _tmp or not os.path.isabs(_tmp):
            _tmp = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        # 上游源码补丁（见 conandata.yml patches）：
        # OHOS musl 的 sys/select.h（经 glib/gmain.h 间接进来）在默认模式下无条件
        # 声明 POSIX `select(2)` 原型；oscats 四个选题算法各自定义了一个**文件内
        # static** 回调 `static gint select (OscatsTest*, OscatsExaminee*, ...)`，
        # 于是 clang 报硬错误（无法用 -Wno-error 降级）：
        #   algorithms/max_kl.c:626:13: error: static declaration of 'select'
        #   follows non-static declaration ... sys/select.h:40: previous
        #   declaration is here
        # 修法是把这些私有定义改名（GObject 信号名 "select" 保持不变），
        # 与知识库既有条目 DRAFT-musl-posix-decl-conflict-rename-legacy（blimps
        # 3.9 的 legacy getline 同款）一致。2026-09-11 CI #44620 实测。
        apply_conandata_patches(self)

        # PKG_CONFIG_PATH：AM_PATH_GLIB_2_0 → PKG_CHECK_MODULES(glib-2.0,
        # gobject-2.0)。PkgConfigDeps 生成的 .pc 在 generators 目录，依赖包
        # 自己的 pkgconfig 目录一并加入。
        pkg_dirs = [self.source_folder, self.build_folder]
        gen = getattr(self, "generators_folder", None)
        if gen:
            pkg_dirs.append(gen)
        pkg_dirs.extend(self._dep_pkgconfig_dirs())
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(pkg_dirs)

        # AX_PATH_GSL 通过 gsl-config 脚本取 CFLAGS/LIBS。gsl 是普通 requires，
        # 其 bin/ 不在 PATH 上 → 显式指路（AC_PATH_PROG 对预设 GSL_CONFIG 生效）。
        #
        # 但制品仓的 gsl/2.8 包内 bin/gsl-config 把 `--cflags`/`--libs` 硬编码成
        # `-I//include` / `-L//lib -lgsl -lgslcblas -lm`（该包用 --prefix=/ 生成
        # 后未改写这两行；实测 prefix=/、includedir=//include）。configure 会
        # 原样照抄进 GSL_CFLAGS → 编译 models/*.c 时
        # `fatal error: 'gsl/gsl_vector.h' file not found`（CI #44619）。
        # 故把 gsl-config 复制到构建目录、就地改写这两处（不改共享缓存里的依赖
        # 包），再让 GSL_CONFIG 指向副本；副本同时修正 prefix/exec_prefix/
        # includedir 头三行，供 `--prefix` 调用方使用。
        try:
            gsl_pf = self.dependencies["gsl"].package_folder
        except Exception:
            gsl_pf = None
        if gsl_pf:
            gsl_cfg = os.path.join(gsl_pf, "bin", "gsl-config")
            if os.path.exists(gsl_cfg):
                dst = os.path.join(self.build_folder, ".gsl-config")
                text = load(self, gsl_cfg)
                text = (text
                        .replace("-I//include", "-I%s/include" % gsl_pf)
                        .replace("-L//lib", "-L%s/lib" % gsl_pf))
                lines = []
                for ln in text.splitlines():
                    if ln.startswith("prefix="):
                        ln = "prefix=%s" % gsl_pf
                    elif ln.startswith("exec_prefix="):
                        ln = "exec_prefix=%s" % gsl_pf
                    elif ln.startswith("includedir="):
                        ln = "includedir=%s/include" % gsl_pf
                    lines.append(ln)
                save(self, dst, "\n".join(lines) + "\n")
                try:
                    os.chmod(dst, 0o755)
                except OSError:
                    pass
                os.environ["GSL_CONFIG"] = dst
                self.output.info(
                    "patched gsl-config -> %s (-I%s/include -L%s/lib)"
                    % (dst, gsl_pf, gsl_pf))

        # 2009 config.sub 不认识 aarch64（实测 `config.sub aarch64-linux` →
        # "machine `aarch64' not recognized"，rc=1）→ 覆盖 config/config.sub。
        # 注意 configure.in 声明了 AC_CONFIG_AUX_DIR([config])，configure 实际
        # 调用 $ac_aux_dir/config.sub = config/config.sub，故必须落到 config/ 下。
        # configure 已显式传 --build/--host=aarch64-linux，config.guess 不会被调用
        # （2010 config.guess 同样不认 aarch64）。
        compat_sub = os.path.join(self.source_folder, "compat", "config.sub")
        aux_sub = os.path.join(self.build_folder, "config", "config.sub")
        if os.path.exists(compat_sub) and os.path.isdir(os.path.dirname(aux_sub)):
            save(self, aux_sub, load(self, compat_sub))
            self.output.info("patched config/config.sub: aarch64 support (2022 FSF)")

        # config.status 的 `umask 077 && mktemp -d ./confXXXXXX` 在 HMFS 上
        # 写不进 0700 目录（cracklib/libmatheval/bogofilter 同款）。
        cfg = os.path.join(self.build_folder, "configure")
        if os.path.exists(cfg):
            text = load(self, cfg)
            if "umask 077" in text:
                save(self, cfg, text.replace("umask 077", "umask 022"))
                self.output.info("patched configure: umask 077 -> 022")

        autotools = Autotools(self)
        autotools.configure()
        # 只编 src/liboscats：用 `make -C src`，src/Makefile 自己的
        # SUBDIRS=liboscats 不被覆盖。不能用 `make SUBDIRS=src`——命令行变量会
        # 经 MAKEFLAGS 递归传进 src/，把 src 的子目录也改成 "src"，cd src 不存在
        # 而失败。bindings/（python/perl/php/java 默认全关）与 doc/（gtk-doc）
        # 因此不参与。
        autotools.make(target="-C src")

    def package(self):
        inc_dst = os.path.join(self.package_folder, "include", "liboscats")
        src_inc = os.path.join(self.source_folder, "src", "liboscats")
        copy(self, "*.h", src=src_inc, dst=inc_dst)
        copy(self, "*.h", src=os.path.join(src_inc, "models"),
             dst=os.path.join(inc_dst, "models"))
        copy(self, "*.h", src=os.path.join(src_inc, "algorithms"),
             dst=os.path.join(inc_dst, "algorithms"))

        lib_dst = os.path.join(self.package_folder, "lib")
        copy(self, "*.a", src=os.path.join(src_inc, ".libs"), dst=lib_dst)
        copy(self, "*.so", src=os.path.join(src_inc, ".libs"), dst=lib_dst)
        copy(self, "*.so.*", src=os.path.join(src_inc, ".libs"), dst=lib_dst)
        # libtool .la 里 libdir/dependency_libs 硬编码指向构建树，消费时报错
        for name in os.listdir(lib_dst) if os.path.isdir(lib_dst) else []:
            if name.endswith(".la"):
                os.remove(os.path.join(lib_dst, name))

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        pc = os.path.join(self.build_folder, "oscats.pc")
        if os.path.exists(pc):
            copy(self, "oscats.pc", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "oscats")
        self.cpp_info.libs = ["oscats"]
        self.cpp_info.includedirs = ["include/liboscats"]
