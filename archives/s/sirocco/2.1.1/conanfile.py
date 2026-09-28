#!/usr/bin/env python3
"""Conan recipe — sirocco 2.1.1 (Autotools)

SIROCCO: certified homotopy continuation of polynomial roots (C++/MPFR).
Compute topologically certified root continuation of bivariate complex
polynomials, returning a piecewise-linear approximation of the path followed
by a root.  Depends on GMP and MPFR.
"""
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, download
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# 上游官方测试（Automake make check）：tests/Makefile.am 声明
#   check_PROGRAMS = sirocco_test sirocco_minimal_test
#   TESTS          = sirocco_test sirocco_minimal_test
# 即 `make check` 运行 2 个测试程序，test-suite.log 汇总 `# TOTAL: 2`。
UPSTREAM_TESTS_TOTAL = 2


class SiroccoConan(ConanFile):
    name = "sirocco"
    version = "2.1.1"
    description = (
        "SIROCCO — certified homotopy continuation of polynomial roots "
        "(C++/MPFR)"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/miguelmarco/SIROCCO2"
    url = "https://github.com/miguelmarco/SIROCCO2"
    topics = ("homotopy-continuation", "polynomial", "mpfr", "certified", "math")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def build_requirements(self):
        # sirocco 自身不用 m4（/bin/sh 原位驱动 + release 包自带 configure，
        # 无 autoreconf），无需声明任何 autotools build tool。
        #
        # 早期“为统一 gmp/mpfr 传递 m4 节点”加过 tool_requires("m4/1.4.19")，真机
        # 实测无效：gmp/mpfr 从源码重编时经各自 AutotoolsToolchain 建立的 m4 节点
        # 仍解析到 conancenter 未适配 m4（日志 patch 1.4.19-0004-disable-hardening
        # -in-source.patch 为 conancenter 命名），sirocco 根配方的 tool_require 覆盖
        # 不到，且会额外引入一次无谓的 m4 构建。因此【不声明 m4 tool_require】。
        #
        # 真正解决 m4 链路的方法是让 gmp/mpfr 命中 ohpcd 预编译二进制，不触发源码
        # 重编（见 requirements()）：仓库专属补丁版本 gmp/6.3.0.1、mpfr/4.2.2.1 仅
        # 存在于 ohpcd，conancenter 无这些版本，解析时被强制走本仓适配配方，其二进制
        # 预置在 ohpcd（arb/flint/soplex 同款先例）→ 不再进入 m4 源码构建。
        pass

    def requirements(self):
        # sirocco.h 直接 #include <mpfr.h>，且库以 -lmpfr -lgmp 链接，必须
        # 直接声明（未发布会触发 R36 依赖闸）。
        #
        # ⚠️ 版本选择（真机 m4 链根因，soplex/7.1.6 + arb/2.9.0 先例）：
        #   - gmp/6.3.0（裸版本）在 preflight 中解析到 conancenter 配方：conancenter
        #     的 gmp recipe 带 m4 tool_require，其 m4/1.4.19 未做 OHOS 适配，在
        #     CONFIG_SHELL=/data/service/hnp/bin/bash（HMDFS getcwd 损坏）下
        #     configure 报 "working directory cannot be determined" → 整链失败。
        #   - gmp/6.3.0.1 是本仓专属补丁版本（与 6.3.0 同一 tarball，sha256 逐字
        #     一致，仅多 --enable-cxx + shared=True），conancenter 无此版本，解析
        #     强制落在本仓 ohpcd 适配配方，其预编译二进制可直接复用（soplex 7.1.6
        #     2026-09-18 真机过，改 requires("gmp/6.3.0.1") 即切断 m4 链）。
        #   - mpfr/4.2.2 同理解析到 conancenter 时会带 m4；改用本仓专属补丁版本
        #     mpfr/4.2.2.1（同一 tarball，额外删 .la 修复），强制 ohpcd 解析。
        #   - gmp/mpfr 必须是【真实直接依赖】而非 override：_ohos_dep_env()/
        #     generate() 都要访问 self.dependencies["gmp"]/["mpfr"] 的 cpp_info，
        #     若只 override=True 则二者不是本包的直接依赖节点，真机报
        #     "KeyError: 'gmp' not found in the dependency set" → 编译失败。
        #     参见已发布 mpfi/linbox：gmp+mpfr 组合用真实 requires。
        #   - mpfr/4.2.2.1 自身钉 gmp/6.3.0，与本包要的 6.3.0.1 冲突；只有
        #     force=True 能压过传递依赖钉的版本（同 mpfi/1.5.3、linbox）。
        self.requires("mpfr/4.2.2.1")
        self.requires("gmp/6.3.0.1", force=True)

    def layout(self):
        # `basic_layout(self)`：source 与 build 同目录（in-source），与
        # gmp/anubis 等已发布 autotools 配方一致。configure 生成的
        # Makefile 与 tests/test-suite.log 落在源码树内，`make check`
        # 的 cwd 与日志定位都确定无疑。
        basic_layout(self)

    def _ohos_tool(self, name):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        c_compiler = compiler_executables.get("c")
        if c_compiler and os.path.isabs(c_compiler):
            return os.path.join(os.path.dirname(c_compiler), name)
        return name

    def source(self):
        # 用 Python 内置 tarfile 原位解压（流式 gzip），避免 OHOS toybox tar 在
        # 解压 .tar.gz 时派生子进程 `exec /usr/bin/zcat`，在共享真机内存紧张时报
        # "Out of memory / had errors"（同 autodiff/0.4.0 先例，本站 cookbook）。
        # 同时保留 conandata.yml 的有序镜像回退与 sha256 校验。
        src = self.conan_data["sources"]
        urls = src["url"]
        if isinstance(urls, str):
            urls = [urls]
        sha256 = src.get("sha256")

        dl_dir = os.path.join(self.source_folder, ".dl")
        os.makedirs(dl_dir, exist_ok=True)
        archive = os.path.join(dl_dir, "libsirocco-2.1.1.tar.gz")
        last_err = None
        for url in urls:
            try:
                download(self, url, filename=archive, sha256=sha256)
                last_err = None
                break
            except Exception as e:  # noqa: BLE001 - any download error -> try next mirror
                last_err = e
                self.output.warning(
                    "sirocco: download failed for %s (%s); trying next mirror", url, e)
        if last_err is not None:
            raise ConanException("sirocco: all download URLs failed: %s" % last_err)

        tmp = os.path.join(self.source_folder, ".extract")
        if os.path.exists(tmp):
            shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp)
        with tarfile.open(archive, "r:gz") as tf:
            if hasattr(tarfile, "data_filter"):
                tf.extractall(tmp, filter="data")
            else:
                tf.extractall(tmp)
        # strip_root：单一顶层目录时上移其内容，否则整体上移
        members = sorted(os.listdir(tmp))
        if len(members) == 1 and os.path.isdir(os.path.join(tmp, members[0])):
            top = os.path.join(tmp, members[0])
            for item in os.listdir(top):
                shutil.move(
                    os.path.join(top, item), os.path.join(self.source_folder, item))
        else:
            for item in members:
                shutil.move(
                    os.path.join(tmp, item), os.path.join(self.source_folder, item))
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(dl_dir, ignore_errors=True)
        apply_conandata_patches(self)

    def _patch_config_guess_for_ohos(self, base=None):
        # E007：GNU config.guess 不识别 HarmonyOS → configure 启动即报
        #   `./build-aux/config.guess: unable to guess system type`
        #   `configure: error: cannot guess build type; you must specify one`
        # 真机预检确认（2026-09-24）：sirocco 2.1.1 自带 2024-07-27 版现代
        # config.guess（UNAME_SYSTEM=HarmonyOS 无法匹配任何分支）。其 config.sub
        # 已是现代版，原生支持 ohos/linux-ohos（已实测 `config.sub
        # aarch64-unknown-linux-ohos` 返回 rc=0），故只须补 config.guess。
        #
        # 现代脚本用统一尾部输出形态（分支只赋 GUESS=，脚本尾部统一 echo $GUESS），
        # 因此注入 GUESS= 形式（DRAFT-config-guess-era-echo-exit 判定现代脚本用
        # GUESS=；旧代脚本才需 echo+exit）。禁止用 --build/--host 绕过
        # （P-AUTOTOOLS-001：会误判交叉编译，跳过 AC_RUN_IFELSE）。
        if base is None:
            base = self.source_folder
        cg = os.path.join(base, "build-aux", "config.guess")
        if not os.path.isfile(cg):
            self.output.warning(
                "sirocco: config.guess not found at {!r}; skipping "
                "HarmonyOS patch".format(cg))
            return
        with open(cg, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        changed = False

        # 1) HarmonyOS 系统识别分支（核心修复）：插到 *:NetBSD:*:*) 之前。
        if "HarmonyOS" not in content:
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                '\t;;\n\n'
                '    *:NetBSD:*:*)'
            )
            if "    *:NetBSD:*:*)" in content:
                content = content.replace("    *:NetBSD:*:*)", block, 1)
                changed = True
            else:
                self.output.warning(
                    "sirocco: config.guess NetBSD anchor not found; "
                    "cannot inject HarmonyOS branch")

        # 2) __OHOS__ libc 探测（与 E007 官方形态一致）。sirocco 的
        #    LIBC 探测段用 Tab 缩进（<<-EOF here-doc），故按空白无关的
        #    #if defined(__ANDROID__)/LIBC=android 序列定位。
        if "__OHOS__" not in content:
            m = re.search(
                r"#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android",
                content)
            if m:
                content = (
                    content[:m.start()] +
                    "#if defined(__ANDROID__)\n    LIBC=android"
                    "\n#elif defined(__OHOS__)\n    LIBC=ohos" +
                    content[m.start() + len("#if defined(__ANDROID__)\n    LIBC=android"):]
                )
                changed = True

        if changed:
            with open(cg, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info("sirocco: patched build-aux/config.guess for HarmonyOS")

    def generate(self):
        if self.settings.os == "OHOS":
            # OHOS 分支的 configure/make/install 全程由 /bin/sh 原位脚本驱动
            # （_build_ohos/_bootstrap_ohos_script/package 内脚本），不经过
            # Conan Autotools helper，也就不需要 AutotoolsToolchain 生成的
            # 环境文件。而 AutotoolsToolchain 一经实例化，会要求 Conan 额外
            # 拉建 m4/autoconf/automake 这些 tool_requires（构建期从源码重编
            # m4），既拖慢每个预检轮次，也在共享真机内存紧张时触发
            # configure 的 `fork: Out of memory`。OHOS 下直接短路，避免拉建
            # 这套用不到的工具链。
            return
        toolchain = AutotoolsToolchain(self)
        if self.options.shared:
            toolchain.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            toolchain.configure_args.extend(["--disable-shared", "--enable-static"])
            if self.options.get_safe("fPIC"):
                toolchain.configure_args.append("--with-pic")
        if self.settings.os == "OHOS":
            # OHOS 系统目录没有 GNU binutils 的同名工具，configure 的
            # AM_PROG_AR / LT_INIT 需要显式给出 llvm 工具链（同 mpfr）。
            toolchain.configure_args.extend(
                [
                    "AR={}".format(self._ohos_tool("llvm-ar")),
                    "LD={}".format(self._ohos_tool("ld.lld")),
                    "RANLIB={}".format(self._ohos_tool("llvm-ranlib")),
                    "NM={}".format(self._ohos_tool("llvm-nm")),
                    "OBJDUMP={}".format(self._ohos_tool("llvm-objdump")),
                    "STRIP={}".format(self._ohos_tool("llvm-strip")),
                ]
            )
        # 依赖注入（R49 精神：指向 conan 依赖包目录，绝不污染系统路径）。
        # sirocco 的 configure.ac 没有 --with-gmp/mpfr 选项，库源码要
        # #include <mpfr.h>/<gmp.h> 且以 -lmpfr -lgmp 链接，只能通过
        # CPPFLAGS/LDFLAGS 把制品仓 gmp/mpfr 的 include/lib 目录注入。
        env = toolchain.environment()
        incs, libs = [], []
        for dep in ("gmp", "mpfr"):
            info = self.dependencies[dep].cpp_info
            base = self.dependencies[dep].package_folder or ""
            for p in info.includedirs:
                incs.append("-I" + (p if os.path.isabs(p) else os.path.join(base, p)))
            for p in info.libdirs:
                libs.append("-L" + (p if os.path.isabs(p) else os.path.join(base, p)))
        if incs:
            env.prepend("CPPFLAGS", " ".join(incs))
        if libs:
            env.prepend("LDFLAGS", " ".join(libs))
        toolchain.generate(env)

    def _fix_umask(self):
        # HMDFS 下 configure 的 `umask 077` 会让 conftest 临时目录不可用，
        # 与 FHS 不一致导致 configure 探针失败（gmp/fplll/arb 同源问题）。
        for cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" not in text:
                continue
            with open(cfg, "w", encoding="utf-8") as f:
                f.write(text.replace("umask 077", "umask 022"))

    # ---- OHOS /bin/sh 原位驱动（同 flint/arb 的 HMDFS getcwd 规避）----
    # profile 的 [buildenv] 把 CONFIG_SHELL/SHELL 指向 /data/service/hnp/bin/bash，
    # 该 bash 在 HMDFS 深层 conan 构建目录上 getcwd 失败，configure 报
    # "working directory cannot be determined"，且 OHOS conan fork 用
    # Autotools helper 时会额外拉建 m4/autoconf/automake tool_requires。
    # 改用 /bin/sh 直接原位驱动 configure/make（绕过 helper 的 bash wrapper），
    # /tmp 只读 → TMPDIR 重定向到 $HOME/tmp（flint/arb 同款）。

    def _resolve_cc(self):
        # 编译器解析链（R33，无硬编码）：tools.build:compiler_executables
        # conf → profile [buildenv] 的 CC（经 VirtualBuildEnv）→ 报错。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c")
        if not cc:
            with VirtualBuildEnv(self).vars().apply():
                cc = os.environ.get("CC")
        if not cc:
            raise ConanException(
                "sirocco: C compiler not found — set the "
                "tools.build:compiler_executables conf or the CC "
                "environment variable"
            )
        return cc

    def _bootstrap_ohos_script(self, script_path, configure_args, cppflags, ldflags, make_cmd):
        cc = self._resolve_cc()
        jobs = self.conf.get("tools.build:jobs", default=os.cpu_count() or 1, check_type=int)
        tmp_root = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmp_root, exist_ok=True)
        # 编译器可执行文件来自 tools.build:compiler_executables 的绝对路径，
        # 但 CI worker 的 PATH 不含工具链目录，clang 找不到同伴工具（ld.lld、
        # nm、m4、make...）。从编译器所在目录推导工具链目录（同 flint/arb）。
        toolchain_dir = os.path.dirname(cc)

        with open(script_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/bin/sh\n")
            f.write("set -e\n")
            f.write('cd "{}"\n'.format(self.source_folder))
            f.write('PATH="{}:$PATH"\n'.format(toolchain_dir))
            f.write("CONFIG_SHELL=/bin/sh\nSHELL=/bin/sh\nTMPDIR={}\n".format(tmp_root))
            f.write("export PATH CONFIG_SHELL SHELL TMPDIR\n")
            f.write("CC={}\nexport CC\n".format(cc))
            if cppflags:
                f.write("CPPFLAGS={}\nexport CPPFLAGS\n".format(shlex.quote(cppflags)))
            if ldflags:
                f.write("LDFLAGS={}\nexport LDFLAGS\n".format(shlex.quote(ldflags)))
            f.write("./configure {}\n".format(" ".join(shlex.quote(a) for a in configure_args)))
            f.write("{}\n".format(make_cmd))
        os.chmod(script_path, 0o755)

    def _ohos_dep_env(self):
        # 汇聚 gmp/mpfr 的 include/lib 目录（绝对路径），供 CPPFLAGS/LDFLAGS。
        cppflags, ldflags = [], []
        for dep in ("gmp", "mpfr"):
            info = self.dependencies[dep].cpp_info
            for p in info.includedirs:
                cppflags.append("-I" + p)
            for p in info.libdirs:
                ldflags.append("-L" + p)
        return " ".join(cppflags), " ".join(ldflags)

    def _configure_args(self):
        args = ["--prefix={}".format(self.package_folder)]
        if self.options.shared:
            args += ["--enable-shared", "--disable-static"]
        else:
            args += ["--disable-shared", "--enable-static"]
            if self.options.get_safe("fPIC"):
                args.append("--with-pic")
        args += [
            "AR={}".format(self._ohos_tool("llvm-ar")),
            "LD={}".format(self._ohos_tool("ld.lld")),
            "RANLIB={}".format(self._ohos_tool("llvm-ranlib")),
            "NM={}".format(self._ohos_tool("llvm-nm")),
            "OBJDUMP={}".format(self._ohos_tool("llvm-objdump")),
            "STRIP={}".format(self._ohos_tool("llvm-strip")),
        ]
        return args

    def _run_upstream_check(self, build_root, use_sh=False):
        # 运行 Automake `make check`（上游 tests/Makefile.am 的 TESTS）。
        # 运行 `make check` 的目录（build_root）与 log/test-suite.log 一致：
        # OHOS in-source 构建生成 Makefile 的目录是 source_folder，桌面端
        # autotools 则是 build_folder，二者作为 build_root 传入。
        log_file = os.path.join(build_root, "upstream-check.log")
        tt = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tt, exist_ok=True)
        if use_sh:
            # OHOS：用 /bin/sh + 可写 TMPDIR 跑 make check，避免 hnp bash
            # getcwd 缺陷与只读 /tmp。
            #
            # 关键：测试程序（sirocco_test / sirocco_minimal_test）通过
            # `-lmpfr -lgmp` 链接。mpfr/4.2.2.1 是静态包（libmpfr.a），
            # 但 gmp/6.3.0.1 是共享包（libgmp.so.10）——链接期 `-lgmp` 生效为
            # 共享库 → 测试可执行文件带 DT_NEEDED libgmp.so.10。若运行期找不到
            # conan 包里那个正确的 libgmp.so.10（无 rpath），OHOS 加载器会回退到
            # 系统自带的 stub libgmp.so.10，符号缺失 → "Error relocating ...
            # symbol not found"，测试 exit 127（真机日志实证）。因此 make check
            # 运行前把依赖（gmp/mpfr）的 libdir 前置进 LD_LIBRARY_PATH，确保
            # 加载到 conan 的正确共享库。
            libdirs = set()
            for dep in ("gmp", "mpfr"):
                for p in self.dependencies[dep].cpp_info.libdirs:
                    libdirs.add(p)
            ld_library_path = ":".join(shlex.quote(p) for p in sorted(libdirs))
            cmd = "export CONFIG_SHELL=/bin/sh SHELL=/bin/sh TMPDIR={t}; " \
                  "export LD_LIBRARY_PATH=\"{llp}:$LD_LIBRARY_PATH\"; " \
                  "make -j1 check > {log} 2>&1".format(
                      t=shlex.quote(tt), llp=ld_library_path,
                      log=shlex.quote(log_file))
            rc = subprocess.call(["/bin/sh", "-c", cmd], cwd=build_root)
            if rc != 0:
                self._emit_check_log(log_file, build_root)
                raise ConanException(
                    "sirocco: upstream `make check` failed with rc={} "
                    "(log: {})".format(rc, log_file))
        else:
            command = "make -j1 check > {} 2>&1".format(shlex.quote(log_file))
            try:
                self.run(command, env="conanbuild", cwd=build_root)
            except ConanException:
                self._emit_check_log(log_file, build_root)
                raise

        log = ""
        for log_path in (
            os.path.join(build_root, "tests", "test-suite.log"),
            os.path.join(self.source_folder, "tests", "test-suite.log"),
            log_file,
        ):
            if os.path.isfile(log_path):
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    log = f.read()
                break

        values = {}
        for key in ("TOTAL", "PASS", "SKIP", "XFAIL", "FAIL", "XPASS", "ERROR"):
            m = re.search(r"^# {}:\s+(\d+)\s*$".format(key), log, re.MULTILINE)
            if m:
                values[key.lower()] = int(m.group(1))
        if "total" not in values:
            raise ConanException(
                "sirocco: upstream `make check` produced no Automake "
                "test-suite.log summary (searched: tests/test-suite.log "
                "under build and source trees); log at {}".format(log_file)
            )

        result = {
            "status": "passed" if (values.get("fail", 0) + values.get("error", 0)) == 0 else "failed",
            "framework": "make check (Automake)",
            "command": "make check",
            "discovered": values["total"],
            "executed": values["total"] - values.get("skip", 0),
            "passed": values.get("pass", 0),
            "failed": values.get("fail", 0) + values.get("error", 0),
            "skipped": values.get("skip", 0),
            "log": log_file,
        }
        if result["discovered"] != UPSTREAM_TESTS_TOTAL:
            raise ConanException(
                "sirocco: upstream test-suite registered {} tests, expected "
                "{} (tests/Makefile.am check_PROGRAMS={} TESTS={})".format(
                    result["discovered"], UPSTREAM_TESTS_TOTAL,
                    "sirocco_test sirocco_minimal_test",
                    "sirocco_test sirocco_minimal_test"))
        if result["failed"]:
            raise ConanException(
                "sirocco: upstream `make check` failed={}".format(result["failed"]))
        with open(os.path.join(build_root, "upstream_test_result.json"),
                  "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(result, ensure_ascii=False)))

    def _emit_check_log(self, log_file, build_root=None):
        if os.path.isfile(log_file):
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                tail = [l for l in f.read().splitlines() if l.strip()]
            for line in tail[-60:]:
                self.output.info("upstream-check| " + line)
        # Automake 并行 harness 把每个测试的 stdout/stderr 单独写到 tests/<test>.log，
        # 并聚合进 tests/test-suite.log；`make check` 的 stdout 不包含这些内容。
        # 上游测试为确定性数值测试，仅凭 rc 无法判断 OHOS 上是崩溃(signal)还是
        # "Singularity detected" 返回 NULL 后被测试解引用崩溃。因此失败时把
        # per-test 日志与 test-suite.log 一并 dump，供真机/CI 定位确切原因。
        if build_root:
            for cand in (
                os.path.join(build_root, "tests", "test-suite.log"),
                os.path.join(self.source_folder, "tests", "test-suite.log"),
            ):
                if os.path.isfile(cand):
                    self.output.info("suitesummary-dump| " + cand)
                    with open(cand, "r", encoding="utf-8", errors="replace") as f:
                        for line in f.read().splitlines():
                            if line.strip():
                                self.output.info("suite| " + line)
                    break
            for tests_dir in (
                os.path.join(build_root, "tests"),
                os.path.join(self.source_folder, "tests"),
            ):
                if not os.path.isdir(tests_dir):
                    continue
                for log in sorted(glob.glob(os.path.join(tests_dir, "*.log"))):
                    if os.path.basename(log) == "test-suite.log":
                        continue
                    self.output.info("testlog-dump| " + log)
                    with open(log, "r", encoding="utf-8", errors="replace") as f:
                        for line in f.read().splitlines():
                            if line.strip():
                                self.output.info("test| " + line)

    def _build_ohos(self):
        self.output.info(
            "sirocco: OHOS build driven by /bin/sh (bash getcwd workaround)")
        # 兜底：直接对 configure 实际运行的目录（source_folder/build_folder）
        # 重新确认 config.guess 已注入 HarmonyOS 分支。source() 已打一次，此处在
        # 运行 configure 前再确保命中，规避 Conan 拷贝 source→build 目录后目录
        # 语义差异（幂等：已含 HarmonyOS/__OHOS__ 则跳过）。
        for base in (self.source_folder, self.build_folder):
            self._patch_config_guess_for_ohos(base)
        cppflags, ldflags = self._ohos_dep_env()
        script = os.path.join(self.source_folder, "_build_ohos.sh")
        self._bootstrap_ohos_script(
            script,
            self._configure_args(),
            cppflags,
            ldflags,
            "make -j1",
        )
        subprocess.check_call(["/bin/sh", script], cwd=self.source_folder)

    def build(self):
        src = self.source_folder
        # 发布 tarball（make dist）自带 configure；GitHub archive 快照则需自举。
        if not os.path.isfile(os.path.join(src, "configure")):
            self.output.info("源码树无 configure，先 autoreconf 自举")
            autotools = Autotools(self)
            autotools.autoreconf(build_script_folder=src)
        self._fix_umask()

        if str(self.settings.os) == "OHOS":
            self._build_ohos()
            # ⚠️ 上游测试必须在包内容就位前跑（此时 build 树齐全）。OHOS 走
            # _build_ohos 的 in-source 构建（cd source_folder 原位 configure+make），
            # 生成 Makefile 的目录是 source_folder 而非 build_folder，因此上游
            # check 也必须在那里跑，否则 build-release 里没有 Makefile → `make
            # check` 报 "No rule to make target 'check'"。
            self._run_upstream_check(self.source_folder, use_sh=True)
            return

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_check(self.build_folder, use_sh=False)

    def package(self):
        if str(self.settings.os) == "OHOS":
            # build() 已完成 configure+make（in-source），这里用 /bin/sh
            # 跑 make install --prefix=package_folder。
            tt = os.path.join(os.path.expanduser("~"), "tmp")
            script = os.path.join(self.source_folder, "_install_ohos.sh")
            cc = self._resolve_cc()
            toolchain_dir = os.path.dirname(cc)
            with open(script, "w", encoding="utf-8", newline="\n") as f:
                f.write("#!/bin/sh\n")
                f.write("set -e\n")
                f.write('cd "{}"\n'.format(self.source_folder))
                f.write('PATH="{}:$PATH"\n'.format(toolchain_dir))
                f.write("CONFIG_SHELL=/bin/sh\nSHELL=/bin/sh\nTMPDIR={}\n".format(tt))
                f.write("export PATH CONFIG_SHELL SHELL TMPDIR\n")
                f.write("make install -j1\n")
            os.chmod(script, 0o755)
            subprocess.check_call(["/bin/sh", script], cwd=self.source_folder)
            if not glob.glob(os.path.join(self.package_folder, "lib", "libsirocco.*")):
                raise ConanException(
                    "sirocco: no libsirocco.* in package folder — 'make install' "
                    "did not populate it"
                )
        else:
            autotools = Autotools(self)
            autotools.install(args=["-j1"])
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
        # LICENSE 在源码根（dist-hook 会把 LICENSE 拷进发布包）。
        for lic in ("LICENSE", "LICENSE.md", "COPYING"):
            src = os.path.join(self.source_folder, lic)
            if os.path.exists(src):
                copy(self, lic, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
                break
        if self.options.shared:
            self._sign_binaries()

    def _sign_binaries(self):
        # HarmonyOS PC XPM 要求被 dlopen 的 .so 带代码签名（同 arb/flint）。
        if str(self.settings.os) != "OHOS":
            return
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True)
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{} --remove-section .codesign "{}" 2>/dev/null || true'.format(objcopy, f))
            self.run('{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, f, f))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["sirocco"]
        # sirocco.h 包含 <mpfr.h>/<fenv.h>，库链接 -lmpfr -lgmp，下游需要
        # gmp/mpfr 的头与库，显式声明以便 CMakeDeps/PkgConfigDeps 透传。
        self.cpp_info.requires = ["gmp::gmp", "mpfr::mpfr"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "sirocco")
        self.cpp_info.set_property("cmake_target_name", "sirocco::sirocco")
        self.cpp_info.set_property("pkg_config_name", "sirocco")
