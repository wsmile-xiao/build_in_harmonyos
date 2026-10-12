"""MUSIC 1.2.1 — Modular Software Interface for Computing Neuronal Processes."""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, export_conandata_patches, get,
                               replace_in_file, save)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class MusicConan(ConanFile):
    name = "music"
    version = "1.2.1"
    description = (
        "MUSIC: MPI-based Modular Software Interface for Computing Neuronal Processes — "
        "the spike-exchange layer between spiking neuronal network simulators"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/INCF/MUSIC"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("mpi", "neuroscience", "spike-exchange", "autotools")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # mpich/4.0.3 是已发布的 OHOS 二进制包（gforker + simple PMI），提供 libmpi 与 mpiexec。
    requires = "mpich/4.0.3"

    # 上游 sanity 套件预算：单条用例 45s（上游硬编码 4s 在共享设备上必然假超时），整套 1800s。
    _case_timeout = 45
    _suite_timeout = 1800

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--without-python")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._patch_autotools_for_ohos()
        self._patch_configure_umask()
        mpi = self._mpi_paths()
        shim = self._write_mpi_shim(mpi)
        stage = self._staging_dir()
        self._configure_make_install(mpi, shim, stage)
        self._run_upstream_suite(mpi, shim, stage)

    def _mpi_paths(self):
        pkg = self.dependencies["mpich"].package_folder
        paths = {name: os.path.join(pkg, name) for name in ("include", "lib", "bin")}
        if not os.path.isdir(paths["include"]):
            raise ConanException("mpich dependency has no include/ directory: %s" % paths["include"])
        if not os.path.isfile(os.path.join(paths["bin"], "mpiexec")):
            raise ConanException("mpich dependency has no bin/mpiexec: %s" % paths["bin"])
        return paths

    def _drivers(self):
        """R33: 编译器取自 tools.build:compiler_executables，不在配方里写死设备路径。"""
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        name = str(self.settings.compiler)
        cc = compilers.get("c") or os.environ.get("CC") or shutil.which(name)
        cxx = compilers.get("cpp") or os.environ.get("CXX") or shutil.which(name + "++")
        if not cc or not cxx:
            raise ConanException(
                "C/C++ drivers not resolvable: set tools.build:compiler_executables in the profile"
            )
        return cc, cxx

    def _write_mpi_shim(self, mpi):
        """Provide the MPI wrapper names MUSIC's configure requires.

        mpich/4.0.3 以 --disable-cxx 构建，不装 mpiCC/mpicxx；其 bin/mpicc 的 shebang
        (#! /data/service/hnp/bin/bash) 在 OHOS 上不存在，直接调用报 inaccessible or not found。
        而 MUSIC 的 configure 只在 $MPI_CXX 逐字等于 "mpiCC" 的分支里赋 SYSGUESS=mpich、
        LAUNCHSTYLE、TESTDIR、EXTRAS，并只在该分支从 "$MPI_CXX -compile_info" 反推编译器，
        所以包装器必须以裸名 mpiCC 出现在 PATH 上（绝对路径会错过该 case 分支）。
        """
        cc, cxx = self._drivers()
        shim = os.path.join(self.build_folder, "_mpishim")
        os.makedirs(shim, exist_ok=True)
        # HMDFS 大小写不敏感：mpiCC 与 mpicc 是同一个文件名，因此只落一个包装器，
        # 按调用名（$0 保留调用时的大小写）分派 C / C++ 驱动。
        wrapper = os.path.join(shim, "mpiCC")
        save(self, wrapper, "\n".join([
            "#!/bin/sh",
            'CC_DRIVER="%s"' % cc,
            'CXX_DRIVER="%s"' % cxx,
            'MPI_INCLUDE="%s"' % mpi["include"],
            'MPI_LIBDIR="%s"' % mpi["lib"],
            'case "$(basename "$0")" in',
            "  mpiCC|mpicxx|mpic++|mpi-c++) driver=\"$CXX_DRIVER\" ;;",
            "  *) driver=\"$CC_DRIVER\" ;;",
            "esac",
            'case "$1" in',
            "  -compile_info) echo \"$driver -I$MPI_INCLUDE\"; exit 0 ;;",
            "  -link_info)    echo \"$driver -L$MPI_LIBDIR -lmpi\"; exit 0 ;;",
            "esac",
            'exec "$driver" "-I$MPI_INCLUDE" "$@"',
            "",
        ]))
        os.chmod(wrapper, 0o755)
        # 上游按 mpirun 这个名字拉起子应用（LAUNCHSTYLE=_mpirun），mpich 只装了 mpiexec。
        mpirun = os.path.join(shim, "mpirun")
        save(self, mpirun, "\n".join([
            "#!/bin/sh",
            'export LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"' % mpi["lib"],
            'exec "%s" "$@"' % os.path.join(mpi["bin"], "mpiexec"),
            "",
        ]))
        os.chmod(mpirun, 0o755)
        return shim

    def _write_timeout_shim(self):
        """timeout that kills the whole process group.

        本机 toybox timeout 只给直接子进程发信号：run_test 的形状是
        `timeout N sh -c "musicrun ... 2> err | sort -o out"`，gforker 的 mpiexec 作为孙进程
        存活并持着管道写端 ⇒ sort 永无 EOF ⇒ 整条链路永久悬挂并泄漏进程树。
        替代器超时后 killpg(SIGTERM→SIGKILL) 并 exit 124，run_test 仍按上游语义记
        "Failed: timeout"，判定语义不变。解释器用运行 conan 的同一个 python，无需探测。
        """
        shim = os.path.join(self.build_folder, "_tmooshim")
        os.makedirs(shim, exist_ok=True)
        save(self, os.path.join(shim, "pkill.py"), '''import os, signal, subprocess, sys, time
tmo = int(sys.argv[1]); cmd = sys.argv[2:]
p = subprocess.Popen(cmd, start_new_session=True)
t0 = time.time(); rc = None
while True:
    rc = p.poll()
    if rc is not None:
        break
    if time.time() - t0 > tmo:
        pg = os.getpgid(p.pid)
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(pg, sig)
            except ProcessLookupError:
                pass
            time.sleep(0.5)
        try:
            p.wait(timeout=5)
        except Exception:
            pass
        sys.stderr.write("PKILL_SHIM timeout after %ds\\n" % tmo)
        sys.exit(124)
    time.sleep(0.2)
sys.exit(rc if isinstance(rc, int) else 1)
''')
        timeout = os.path.join(shim, "timeout")
        save(self, timeout, '#!/bin/sh\nexec "%s" "%s" "$@"\n'
             % (sys.executable.replace("\\", "/"), os.path.join(shim, "pkill.py").replace("\\", "/")))
        os.chmod(timeout, 0o755)
        # 返回目录（与 _write_mpi_shim 同形）：套件脚本按 os.path.join(dir, "timeout") 引用。
        return shim

    def _ohos_skill_script(self):
        """R15 helper lives in the repository the recipe is exported from, not in a fixed device path."""
        candidates = []
        skill_root = os.environ.get("OHC_SKILL_ROOT", "")
        if skill_root:
            candidates.append(os.path.join(skill_root, "scripts", "patch-autotools-ohos.pl"))
        folder = os.path.dirname(os.path.abspath(self.recipe_folder))
        for _ in range(6):
            candidates.append(os.path.join(folder, "scripts", "patch-autotools-ohos.pl"))
            parent = os.path.dirname(folder)
            if parent == folder:
                break
            folder = parent
        for path in candidates:
            if os.path.isfile(path):
                return path
        return ""

    #: config.guess 的大 case 语句开头，两个 vintage 都以此为锚
    _CG_CASE = 'case "${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}" in'

    def _patch_autotools_for_ohos(self):
        """R15/E007: config.guess/config.sub 的 OHOS 支持，并以真机执行做硬校验。

        skill 脚本 (patch-autotools-ohos.pl) 是 rec_priority 1 的方案，但它在缓存里跑的配方
        拿不到（recipe_folder 是导出目录，不是 worktree），且对 2015-08-20 vintage 实测只做到
        1/5：注入的分支写的是新 vintage 的 `GUESS=…` 约定，而本 vintage 每个分支自带
        echo+exit、case 之后无条件落入文件末尾的 "has failed to recognize" 块 ⇒ 分支命中了
        仍然返回空串，configure 报 "cannot guess build type"。config.sub 的三处锚点在本
        vintage 也不存在。所以两条路径都以"真机执行 config.guess/config.sub"为准：
        脚本改好了就补 echo，脚本没到位就自己按本 vintage 的形态注入。
        """
        guess = os.path.join(self.source_folder, "config.guess")
        sub = os.path.join(self.source_folder, "config.sub")
        script = self._ohos_skill_script()
        if script and os.path.exists(guess):
            self.output.info("Patching config.guess/config.sub with %s (R15)" % script)
            subprocess.run(["perl", script, guess, sub], check=False)
        if os.path.exists(guess):
            self._patch_config_guess(guess)
            self._patch_config_sub(sub)
            self._verify_triplet(guess, sub)

    def _patch_config_guess(self, guess):
        if self._read_count(guess, "HarmonyOS"):
            # skill 脚本已注入分支：把新 vintage 的 GUESS 赋值补成本 vintage 的 echo+exit。
            replace_in_file(self, guess,
                            '\tGUESS=${MACHINE}-unknown-linux-ohos\n\t;;',
                            '\techo "${MACHINE}-unknown-linux-ohos"\n\texit 0\n\t;;',
                            strict=False)
            return
        replace_in_file(self, guess, self._CG_CASE, "\n".join([
            self._CG_CASE,
            '    *:HarmonyOS:*:*)',
            '\techo ${UNAME_MACHINE}-unknown-linux-ohos',
            '\texit 0',
            '\t;;',
        ]))
        self.output.info("config.guess: HarmonyOS branch injected")

    def _patch_config_sub(self, sub):
        if not os.path.exists(sub):
            return
        if self._read_count(sub, "linux-ohos"):
            return
        # 两处白名单：内核-OS 组合表（决定 -linux-ohos 能否整体当成 os 字段）与 os 枚举表。
        replace_in_file(self, sub, "linux-musl* | linux-uclibc* |",
                        "linux-ohos* | linux-musl* | linux-uclibc* |", strict=False)
        replace_in_file(self, sub, "| -linux-newlib* | -linux-musl* |",
                        "| -linux-newlib* | -linux-musl* | -linux-ohos* |", strict=False)
        self.output.info("config.sub: linux-ohos added to both whitelists")

    def _verify_triplet(self, guess, sub):
        """不接受 configure 的 "cannot guess build type"：这里就把它变成可读签名。"""
        proc = subprocess.run(["sh", guess], cwd=self.source_folder,
                              capture_output=True, text=True)
        triplet = proc.stdout.strip()
        self.output.info("config.guess -> %s (rc=%d)" % (triplet, proc.returncode))
        if proc.returncode or not triplet:
            raise ConanException("config.guess still cannot guess the OHOS build type: rc=%d %s"
                                 % (proc.returncode, proc.stderr.strip()[-300:]))
        check = subprocess.run(["sh", sub, triplet], cwd=self.source_folder,
                               capture_output=True, text=True)
        self.output.info("config.sub %s -> %s (rc=%d)"
                         % (triplet, check.stdout.strip(), check.returncode))
        if check.returncode or not check.stdout.strip():
            raise ConanException("config.sub rejects %s: %s"
                                 % (triplet, (check.stdout + check.stderr).strip()[-300:]))

    def _patch_configure_umask(self):
        """E011/E114: HMDFS rejects the umask-077 protected temp dir configure creates.

        configure wraps its autoconf scratch dir in `umask 077 && mktemp`; on this file system
        the resulting directory is unreadable to the very shell that made it, so the probe for
        a working temp dir fails with "cannot create a temporary directory".  Widening the mode
        keeps the real temp-dir creation intact and is the controlled form used repo-wide.
        """
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            return
        before = self._read_count(configure, "umask 077")
        replace_in_file(self, configure, "umask 077", "umask 022", strict=False)
        self.output.info("configure umask 077 -> 022: %d site(s)" % before)

    @staticmethod
    def _read_count(path, needle):
        with open(path, "r", errors="replace") as handle:
            return handle.read().count(needle)


    def _staging_dir(self):
        return os.path.join(self.build_folder, "_teststage")

    def _stage_prefix(self, stage):
        """make install DESTDIR=<stage> 与 --prefix=<绝对 package_folder> 的合成前缀。"""
        prefix = self.package_folder.replace("\\", "/").lstrip("/")
        return os.path.normpath(os.path.join(stage, prefix))

    def _configure_make_install(self, mpi, shim, stage):
        src = self.source_folder.replace("\\", "/")
        prefix = self.package_folder.replace("\\", "/")
        configure_args = ['--prefix="%s"' % prefix]
        if not self.options.shared:
            configure_args += ["--enable-static", "--disable-shared"]
        configure_args.append("--without-python")
        # configure's `mpiCC)` case only forwards what we put in these three
        # variables — it does not splice CFLAGS/CXXFLAGS into them — so the
        # position-independent and optimisation flags have to be spelled out.
        mpi_cflags = ["-I%s" % mpi["include"].replace("\\", "/"), "-O2"]
        if self.options.get_safe("fPIC"):
            mpi_cflags.append("-fPIC")
        mpi_cxxflags = list(mpi_cflags) + ["-DHAVE_MPICH2"]
        lines = [
            "#!/bin/sh",
            "set -e",
            'cd "%s"' % src,
            # 包装器必须是裸名 mpiCC 且在 PATH 首位（见 _write_mpi_shim）。
            'export PATH="%s:$PATH"' % shim.replace("\\", "/"),
            'export LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"'
            % mpi["lib"].replace("\\", "/"),
            # configure 只在 mpicxx) 分支且存在 mpich2version 时才 AC_DEFINE(HAVE_MPICH2)，
            # 而本平台走的是 mpiCC) 分支 ⇒ 不显式声明就落进上游 MPICH 兜底分支：其 getConfig()
            # 用单一全局 $HOME/.musicconf（rank0 写 / rank>0 读、无任何同步），共享同一 $HOME 的
            # 各 rank 会读到上一条用例的配置。HAVE_MPICH2 让 mpidep.cc 走上游自己的 MPICH2 分支
            # （getRank=getenv("PMI_RANK")，getConfig=直接读 argv 里的配置文件）。
            'export MPI_CXXFLAGS="%s"' % " ".join(mpi_cxxflags),
            'export MPI_CFLAGS="%s"' % " ".join(mpi_cflags),
            'export MPI_LDFLAGS="-L%s -lmpi"' % mpi["lib"].replace("\\", "/"),
            'export CXX=mpiCC',
            'export CC=mpicc',
            # §14.1：全机 jobs=2，并发抬高内存峰值（configure 派生的子 make 也继承）。
            "export MAKEFLAGS=-j2",
        ]
        if str(self.settings.os) == "OHOS":
            # 设备上没有 GNU binutils（ar/nm/ranlib/ld/strip 全部 MISSING），只有 LLVM 的同名工具。
            lines.append('export AR=llvm-ar RANLIB=llvm-ranlib NM=llvm-nm STRIP=llvm-strip LD=ld.lld')
        lines += [
            'sh ./configure %s' % " ".join(configure_args),
            # §14.1：全机 jobs=2，并发抬高内存峰值。
            "make -j2",
            'make install DESTDIR="%s"' % stage.replace("\\", "/"),
            "",
        ]
        script = os.path.join(self.build_folder, "music-ohos-build.sh")
        save(self, script, "\n".join(lines))
        os.chmod(script, 0o755)
        self.run('"%s"' % script, env="conanbuild")

    def _run_upstream_suite(self, mpi, shim, stage):
        """跑上游 sanity 套件（configure 生成的 bin/music_tests），结果只汇总、不拦构建。

        装机版 music_tests 把 configure 期的绝对前缀烧死在脚本里，DESTDIR 暂存后指向的还是
        尚未存在的 package_folder；补丁 0001 让这些前缀可用 MUSIC_TEST_* 覆盖，于是同一份
        runner 既能对着暂存树跑，也不改变最终包内的默认行为。
        """
        if not can_run(self):
            self.output.warning("upstream suite skipped: cross-building, cannot execute target ELF")
            return
        prefix = self._stage_prefix(stage)
        runner = os.path.join(prefix, "bin", "music_tests")
        if not os.path.isfile(runner):
            self.output.warning("upstream suite skipped: %s not produced by make install" % runner)
            return
        if not os.access(runner, os.X_OK):
            # E543：HMDFS 新建文件默认 660，构建产物可能不可执行。
            os.chmod(runner, 0o755)
        tmooshim = self._write_timeout_shim()
        outdir = os.path.join(self.build_folder, "_testout")
        bindir = os.path.join(prefix, "bin").replace("\\", "/")
        extradir = os.path.join(prefix, "lib", "music-1.2.1").replace("\\", "/")
        datadir = os.path.join(prefix, "share", "music-1.2.1").replace("\\", "/")
        libdir = os.path.join(prefix, "lib").replace("\\", "/")
        lines = [
            "#!/bin/sh",
            'export PATH="%s:%s:%s:%s:$PATH"'
            % (tmooshim.replace("\\", "/"), shim.replace("\\", "/"), bindir,
               mpi["bin"].replace("\\", "/")),
            'export LD_LIBRARY_PATH="%s:%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"'
            % (libdir, mpi["lib"].replace("\\", "/")),
            'export MUSIC_TEST_BINDIR="%s"' % bindir,
            'export MUSIC_TEST_EXTRABINDIR="%s"' % extradir,
            'export MUSIC_TEST_DATADIR="%s"' % datadir,
            'export MUSIC_TEST_TIMEOUT=%d' % self._case_timeout,
            'export TEST_OUTDIR="%s"' % outdir.replace("\\", "/"),
            # 不能 cd 进 TEST_OUTDIR：runner 自己 `rm -rf` 再 `mkdir`（music_tests:271-275），
            # HMDFS 上删后重建的是新 inode ⇒ 旧 cwd 变孤儿，os.getcwd() 直接 FileNotFoundError
            # （本机实测），任何子进程（`env bash -c "time runtest.sh"`）起手就死，症状是
            # "所有用例无 log、无 ret、TIME_ELAPSED 空 → awk 语法错 → unexpected exit code"。
            'cd "%s"' % self.build_folder.replace("\\", "/"),
            # E386 家族第二道：PWD 预置 + 把 shell 路由出 hnp bash（conan 的 SHELL/CONFIG_SHELL
            # 指向 hnp bash，在 HMDFS 构建目录内 getcwd 必挂）。runner 内部用 `/usr/bin/env bash`
            # 起子 shell，故这里只保证环境里不再有人回落到 hnp bash。
            'export PWD="$(pwd)"',
            'unset CONFIG_SHELL',
            'export SHELL=/bin/sh',
            '"%s" %d sh "%s" 2>&1' % (os.path.join(tmooshim, "timeout").replace("\\", "/"),
                                      self._suite_timeout, runner),
            'echo "SUITE_RC=$?"',
            "",
        ]
        os.makedirs(outdir, exist_ok=True)
        script = os.path.join(self.build_folder, "music-ohos-suite.sh")
        save(self, script, "\n".join(lines))
        os.chmod(script, 0o755)
        # 上游套件在本平台有已知失败项（collective 通路、gforker 共享 stdout 行交错、
        # 上游用例自相矛盾的期望），一律如实汇总上报，不作为构建闸门。
        self.run('"%s"' % script, env="conanbuild", ignore_errors=True)
        self._report_suite(outdir)

    def _report_suite(self, outdir):
        log = os.path.join(outdir, "output.log")
        if not os.path.isfile(log):
            self.output.warning("UPSTREAM SUITE: no %s produced" % log)
            return
        with open(log, "r", errors="replace") as handle:
            text = handle.read()
        registered = text.count("Running test ")
        ok = text.count("...OK")
        failed = text.count("...FAILED")
        timeout = text.count("...TIMEOUT")
        aborts = text.count("unexpected exit code")
        self.output.info(
            "UPSTREAM SUITE (testsuite/sanitytests): registered=%d OK=%d FAILED=%d TIMEOUT=%d "
            "suite_abort=%d per_case_timeout=%ds" %
            (registered, ok, failed, timeout, aborts, self._case_timeout))
        for line in text.splitlines():
            if line.startswith("-> ") or line.startswith("Running test "):
                self.output.info("SUITE| %s" % line.strip())

    def package(self):
        stage = self._stage_prefix(self._staging_dir())
        if not os.path.isdir(stage):
            raise ConanException("staged install tree is missing: %s" % stage)
        shutil.copytree(stage, self.package_folder, dirs_exist_ok=True)
        self._copy_license()
        for pattern in ("*.la",):
            for root, _dirs, files in os.walk(os.path.join(self.package_folder, "lib")):
                for name in files:
                    if name.endswith(pattern):
                        os.remove(os.path.join(root, name))

    def _copy_license(self):
        copy_licenses = ("COPYING",)
        dst = os.path.join(self.package_folder, "licenses")
        os.makedirs(dst, exist_ok=True)
        for name in copy_licenses:
            src = os.path.join(self.source_folder, name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst, name))

    def package_info(self):
        self.cpp_info.libs = ["music"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # 消费者同时需要 MPI 头与 libmpi：与 globalarrays 同例（mpich 无命名组件）。
        self.cpp_info.requires = ["mpich::mpich"]
