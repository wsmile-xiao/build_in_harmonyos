#!/usr/bin/env python3
"""Conan recipe for GNU vcdimager 2.0.1 — VideoCD 镜像/打包命令行工具。

vcdimager（C++ + autotools，上游 2018-01-07 发布 2.0.1）构建产物是 7 个 CLI 程序
（frontends/cli/Makefile.am: bin_PROGRAMS = vcdimager cdxa2mpeg vcd-info；
frontends/xml/Makefile.am: bin_PROGRAMS = vcdxbuild vcdxgen vcdxrip vcdxminfo）
与内部库 libvcd / libvcdinfo。故 package_type = "application"，并按 R38 在**软件级**
目录提供 commands.json。

依赖（configure.ac 实测，见下方 requirements() 注释）：
  * libcdio   >= 2.0.0  PKG_CHECK_MODULES(LIBCDIO,    libcdio)     → 制品仓 libcdio/2.3.0
  * libiso9660>= 2.0.0  PKG_CHECK_MODULES(LIBISO9660, libiso9660)  → **同一 libcdio 包提供**
  * popt               PKG_CHECK_MODULES(LIBPOPT, popt)          → 制品仓 popt/1.16
  * libxml2   >= 2.3.8  PKG_CHECK_MODULES(XML, libxml-2.0)        → 制品仓 libxml2/2.15.3.1
  zlib/bzip2 不直接依赖（由 libcdio 的依赖链自行管理）。

为什么 libiso9660 不需要单独配方：libcdio 2.3.0 的**上游发布归档本身就是
libcdio+libiso9660+libudf 的合集**（归档内含 lib/iso9660/ 与 libiso9660.pc.in），
`archives/l/libcdio/2.3.0` 的 package_info() 也如实声明
`cpp_info.libs = ["iso9660", "udf", "cdio"]`。

W0 依赖发布态一手证据（2026-09-25 起、2026-09-26 复核，构建主机 B，
  CONAN_HOME=~/tmp/ch/home-主理-45-vcdimager；命令形态是 conan download <精确引用>
  配 --only-recipe 与制品仓 remote 参数 —— remote 名属 CI 环境配置，L0g 禁在配方里写死，
  故此处只记读数不记参数）：
  libcdio/2.3.0      → RC=0，rev 011d2512246208d85a9afec61a933dfe
  popt/1.16          → RC=0，rev cca44e0c65c2ff043d329f27a068a956
  libxml2/2.15.3.1   → RC=0，rev d306e63f5f09376deb0038a5da1f2837
  diffutils/3.12     → RC=0，rev 1847bcef5ee9aa67290e4a1ef7f69306（tool_requires，
                       且二进制包可直接下载：create 日志里 Package installed
                       6b129b068851896169fae42d399fa922d239ce8a）
  （zlib/1.3.1 亦 RC=0，rev 2ee7c0eeb8f4dfef8982d0c5c1551a61）

上游测试：test/Makefile.am 的 TESTS 共 8 项（check_sizeof、check_bitfield、
check_nrg.sh、check_vcd11.sh、check_vcd20.sh、check_svcd1.sh、testassert、testvcd），
XFAIL_TESTS = testassert（上游预期失败）。build() 里真跑 `make check`，
判决由 _emit_upstream_test_result() 从 automake 自己的 test-suite.log 读数，
逐条登记在 notes.md / reports/（R51 上游测试三步法）。

HMDFS getcwd 兜底：configure 起手报 `working directory cannot be determined`
（本仓已知的 HMDFS 拒绝 getcwd 家族，同 addchain/analog/open-mpi/adcli）。
按 `archives/a/adcli/0.9.2/conanfile.py:275-292` 的先例走**配方侧 Environment
注入**（不写补丁）：显式给 PWD=<build_folder>，并把 TMPDIR/TMP/TEMP 钉到可写
目录（/tmp 是只读 erofs）。autoconf 优先读 $PWD，bash 从环境初始化 $PWD 而不调
getcwd()，因此不需要改源码树。
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _automake_count(text, label):
    """Parse `# LABEL: N` from an automake parallel-tests test-suite.log."""
    for line in text.splitlines():
        if line.startswith("# " + label + ":"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return 0
    return 0


class VcdimagerConan(ConanFile):
    name = "vcdimager"
    version = "2.0.1"
    description = ("GNU VCDImager — 把 MPEG 视频流打包成 VCD/SVCD(2.0) 镜像与 "
                   "cue/bin、XML 描述的命令行工具")
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/vcdimager/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # 全部为 configure.ac 里的硬性 PKG_CHECK_MODULES：
    # 缺 popt 会让 configure 静默把 enable_cli_fe 置 no（= 不再产出 vcdimager
    # 本体），缺 libxml2 会静默关掉 xml 前端 —— 两者都会得到"绿灯但没功能"的
    # 残废包，所以按完整功能集声明依赖，不用 --disable-* 绕（R1 参数最少化）。
    def requirements(self):
        # 用 self.requires() 调用式声明（而非类属性元组）：
        # ci/scripts/preflight_check.sh 与 create-pr 的 PF4 依赖闸都只解析调用式，
        # 元组式会让 W0 预检打印「未找到依赖声明」并假通过（2026-09-26 实拍）。
        # 三个依赖的发布态一手证据见 notes.md 的 W0 节（reports/ 不入 git）。
        self.requires("libcdio/2.3.0")
        self.requires("popt/1.16")
        self.requires("libxml2/2.15.3.1")
        # test/ 用 diff 比对回归输出，必须是 GNU diffutils（见 _gnu_diff_path）。
        self.tool_requires("diffutils/3.12")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_pkgconfig_dirs(self):
        """依赖包里**已安装**的 .pc 目录（含 libcdio 附带的 libiso9660.pc）。"""
        dirs = []
        for dep in self.dependencies.host.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            for sub in ("lib/pkgconfig", "lib64/pkgconfig", "share/pkgconfig"):
                cand = os.path.join(folder, sub)
                if os.path.isdir(cand) and cand not in dirs:
                    dirs.append(cand)
        return dirs

    # configure.ac 里的 4 个 PKG_CHECK_MODULES：宏前缀 → (conan 依赖名, 该前缀要的子集)。
    # libiso9660 不是独立 conan 依赖，它由 libcdio 合集包提供（见文件头），
    # 所以要按 cpp_info.libs 里的真实库名切片。
    _PKG_MODULES = (
        ("LIBCDIO", "libcdio", ("cdio",)),
        ("LIBISO9660", "libcdio", ("iso9660",)),
        ("LIBPOPT", "popt", None),
        ("XML", "libxml2", None),
    )

    def _abs(self, folder, path):
        return path if os.path.isabs(path) else os.path.join(folder, path)

    def _all_dep_libdirs(self):
        dirs = []
        for dep in self.dependencies.host.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            for sub in getattr(dep.cpp_info, "libdirs", None) or []:
                cand = self._abs(folder, sub)
                if os.path.isdir(cand) and cand not in dirs:
                    dirs.append(cand)
        return dirs

    def _la_free_libdir(self):
        """E236：给 libtool 一个**只有 .a、没有 .la** 的构建私有目录。

        本仓制品按 `--prefix=/` 约定安装（见 archives/c/cdrdao/1.2.6/conanfile.py:145-148），
        于是依赖包 `.la` 里记的 `libdir` 是 `//lib`、`dependency_libs` 硬编码
        `//lib/<dep>.la`。libtool 在 `-L` 目录里对 `.la` 的优先级高于同名 `.a`，
        实拍（第 5 轮 conan-create.log:356）：
            libtool: warning: library '.../lib/libcdio.la' was moved.
            libtool:   error: cannot find the library '//lib/libcdio.la'
        照已合并先例 archives/e/ezstream/1.0.2/conanfile.py:96-116 与
        archives/l/libabw/0.1.4/conanfile.py:347-367：把要链的静态归档**复制**到
        generators 下的 la-free 目录（不带任何 .la 元数据），让 libtool 走干净的
        `-L/-l` 路径；**conan 缓存原样不动**（不违反"不改他人资产"）。
        """
        d = os.path.join(self.generators_folder, "la-free")
        os.makedirs(d, exist_ok=True)
        copied = []
        for dep in self.dependencies.host.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            for sub in getattr(dep.cpp_info, "libdirs", None) or []:
                src = self._abs(folder, sub)
                if not os.path.isdir(src):
                    continue
                for fname in sorted(os.listdir(src)):
                    if not fname.endswith(".a"):
                        continue
                    dst = os.path.join(d, fname)
                    if os.path.exists(dst):
                        # 同名归档只保留第一个（libcdio 合集内不会重名）
                        continue
                    shutil.copy2(os.path.join(src, fname), dst)
                    copied.append(fname)
        self.output.info("[E236 la-free] " + str(len(copied))
                         + " archives -> " + d)
        return d

    def _pkg_module_flags(self):
        """把 configure.ac 的 4 组 *_CFLAGS / *_LIBS 用 conan 依赖图的**绝对路径**钉死。

        PKG_CHECK_MODULES 的语义：`LIBCDIO_CFLAGS`/`LIBCDIO_LIBS` 这类变量若在
        configure 命令行预置（precious var），autoconf 就**跳过 pkg-config**。
        这里必须预置，因为实拍到两条 pkg-config 通路都不可信：
          1) 本配方没启用 PkgConfigDeps，generators 目录里没有依赖的 .pc；
          2) 依赖包**自己安装的** .pc 前缀是坏的 ——
             `p/libcde894bc8d0f1a1/p/lib/pkgconfig/libcdio.pc` 里
             `prefix=/`，于是 `Cflags: -I${includedir}` 展开成
             `-I//include`，configure 探测 "checking for LIBCDIO... yes" 假绿，
             真正编译 `lib/info.c` 时才炸：
             `fatal error: 'cdio/cdio.h' file not found`
             （第 4 轮 conan-create.log:311）。
        修法照已合并先例 archives/a/adcli/0.9.2/conanfile.py:266-272
        （同一个 "precious var 预置" 形态，那里是 KRB5_CFLAGS/KRB5_LIBS）。
        路径全部来自 conan 依赖图（不读裸 shell 环境变量，符合 R33；
        指向依赖包私有目录，符合 R49）。
        """
        by_name = {}
        for dep in self.dependencies.host.values():
            by_name[dep.ref.name] = dep
        # la-free 目录排在最前：libtool 先在它里面找 lib<name>.a（无 .la 干扰）。
        libdirs = ["-L" + self._la_free_libdir()]
        libdirs += ["-L" + d for d in self._all_dep_libdirs()]
        args = []
        for prefix, dep_name, lib_subset in self._PKG_MODULES:
            dep = by_name.get(dep_name)
            if dep is None:
                raise ConanException(
                    "dependency " + dep_name + " missing for PKG_CHECK_MODULES("
                    + prefix + ", ...) preset")
            folder = dep.package_folder
            cflags = ["-I" + self._abs(folder, p)
                      for p in (getattr(dep.cpp_info, "includedirs", None) or [])]
            own = list(getattr(dep.cpp_info, "libs", None) or [])
            picked = [lib for lib in own
                      if (lib_subset is None or lib in lib_subset)]
            sys_libs = list(getattr(dep.cpp_info, "system_libs", None) or [])
            libs = list(libdirs) + ["-l" + lib for lib in picked + sys_libs]
            args.append(prefix + "_CFLAGS=" + " ".join(cflags))
            args.append(prefix + "_LIBS=" + " ".join(libs))
            self.output.info("[pkg preset] " + prefix + "_LIBS=" + " ".join(libs))
        return args

    def _gnu_diff_path(self):
        """tool_requires(diffutils) 里 GNU diff 的绝对路径，供 configure 的 DIFF 覆盖。

        OHOS 的 /usr/bin/diff 是 toybox 软链（实测 /usr/bin/diff -> ../../bin/toybox，
        toybox 0.8.12）。configure 把探到的 @DIFF@ 烧进 test/check_common_fn，而 toybox diff
        对 -w --unified 直接报「diff: <file>: Invalid argument」（rc=2），同一条命令换 GNU
        diffutils 则 rc=0 且内容逐字一致 ⇒ check_vcd11/vcd20/svcd1 三个脚本在镜像 cksum 已过、
        只差内容比对那一步被判 FAIL。上游 configure 明写 "Let the user override the test with a
        path"（DIFF 是命令行可预置的 precious var），所以不动 TESTS 分母、不关测试、不改测试
        文件，只把 DIFF 钉到 conan 依赖图里的 GNU diffutils（R33/R49：路径来自依赖图，不读裸
        shell 变量；不写死 /data/service/hnp 这类机器特定路径，保证 CI 同源）。
        """
        # tool_requires 落在构建上下文；按名查找只覆盖 host 上下文（第 8 轮实拍
        # KeyError: diffutils not found in the dependency set）⇒ 显式遍历 build 上下文。
        dep = None
        for _d in self.dependencies.build.values():
            if _d.ref.name == "diffutils":
                dep = _d
                break
        if dep is None:
            raise ConanException("diffutils is not in the build-context dependencies")
        cand = os.path.join(dep.package_folder, "bin", "diff")
        if not os.path.exists(cand):
            raise ConanException("diffutils tool_requires: no diff at " + cand)
        self.output.info("[GNU diff] DIFF=" + cand)
        return cand

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 兜底：把依赖包自己安装出来的 .pc 目录也挂上（libcdio 附带的
        # libiso9660.pc 等）；真正的 CFLAGS/LIBS 由下方预置变量决定。
        pc_dirs = [self.generators_folder] + self._dep_pkgconfig_dirs()
        tc.configure_args.append("PKG_CONFIG_PATH=" + ":".join(pc_dirs))
        tc.configure_args.extend(self._pkg_module_flags())
        tc.configure_args.append("DIFF=" + self._gnu_diff_path())
        # E007/E072 家族：本包 configure 自带的 config.guess 是 2016-10-02 版，
        # 不认 `uname -s` = HarmonyOS（实拍报错
        # `configure: error: cannot guess build type; you must specify one`）。
        # 按仓内主流先例显式传 --build/--host 跳过 config.guess（649 个已合并
        # 配方同款，如 archives/a/a52dec/0.7.4/conanfile.py:55-59）。
        # build 与 host 传**同一个**三元组 ⇒ autoconf 规范化后判定为本机编译，
        # AC_RUN_IFELSE 仍真跑，不会退化成交叉编译（E007 根因段警示的那条）。
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def _scratch(self):
        """配方主进程预建的可写工作目录（build_folder 内，随构建档期存在）。"""
        d = os.path.join(self.build_folder, ".hmdfs-tmp")
        os.makedirs(d, exist_ok=True)
        return d

    def _fs_env(self):
        """HMDFS 拒绝 getcwd() / /tmp 只读 erofs 的环境兜底。

        同 adcli/addchain/analog/open-mpi 家族签名：HMDFS 对 conan 构建树的父目录
        拒绝 getcwd()，bash/autoconf 的 `pwd` 随之失败
        （`configure: error: working directory cannot be determined`）。
        autoconf 先读 $PWD，bash 也是从环境初始化 $PWD 而不调 getcwd()，
        因此显式 define PWD=<build_folder> 即可绕过；同时把 TMPDIR/TMP/TEMP
        钉到配方预建的可写目录（/tmp 是只读 erofs，configure 的 tmp 探针会失败）。
        """
        tmpdir = self._scratch()
        env = Environment()
        env.define("PWD", self.build_folder)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        return env

    def _patch_configure_ac_tmp(self):
        """E114：HMDFS 拦「脚本子进程在**新建目录**里写文件」。

        autoconf 2.69 的 config.status 用 AS_TMPDIR 在 build 目录新建 ./confXXXXXX
        再往里写 subs1.awk，实拍报错（第 3 轮 conan-create.log:264-265）：
            ./config.status: line 888: ./confhpx64a/subs1.awk: Permission denied
            config.status: error: could not setup config files machinery
        目录本身建得出来（构建树内新建 OK），被拦的是「子进程往新目录写文件」。
        修法照已合并先例（archives/a/abiword-plugin-docbook/3.0.8/conanfile.py:312-341
        / libgsf 同款）：由**配方主进程**预建可写目录，把 configure 内嵌
        config.status 模板里的 `ac_tmp=$tmp` 改指该目录；并把退出 trap 从
        `rm -fr "$ac_tmp"` 改成只透传退出码 —— 否则首轮 config.status 结束就把
        预建目录删掉，make 之后重跑 config.status 必挂。
        """
        fixed_tmp = self._scratch()
        cfg_path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(cfg_path):
            raise ConanException(
                "E114: no generated configure at " + cfg_path)
        with open(cfg_path, "r", encoding="utf-8") as fh:
            text = fh.read()
        if "ac_tmp=$tmp" not in text:
            raise ConanException(
                "E114: ac_tmp=$tmp pattern not found in configure; "
                "autoconf may have changed the template")
        text = text.replace("ac_tmp=$tmp", "ac_tmp=" + fixed_tmp)
        old_trap = ('{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; }'
                    ' && exit $exit_status')
        if old_trap in text:
            text = text.replace(old_trap, "exit $exit_status")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(cfg_path, 0o755)
        self.output.info(
            "[HMDFS/E114] configure ac_tmp -> " + fixed_tmp)

    def _sync_generated_check_common_fn(self):
        """让 test/check_*.sh 读到**本次 configure 生成**的 check_common_fn。

        上游 tarball 里的 test/check_common_fn 是**上游机器上预先烧好 @DIFF@ 的生成物**
        （实拍 mtime 2018-01-08 08:46:41，内容是绝对路径 /usr/bin/diff），而
        test/check_*.sh 一律 source 源码树里的 . <srcdir>/check_common_fn ⇒ 读的是源码树那一份。
        out-of-tree 构建下 config.status 把新生成物写到 build 目录，所以配方在 configure
        命令行预置的 DIFF=<conan 依赖图里的 GNU diffutils>/bin/diff 根本进不到测试里
        （第 9 轮实拍：config.log:588 已 result 成 conan 的 diff，srcdir 那份仍是
        /usr/bin/diff，而 OHOS 的 /usr/bin/diff 是 toybox 软链，对 -w --unified 直接
        报 Invalid argument ⇒ 4 个 check_*.sh 被判 FAIL）。
        这里把 config.status 刚生成的那份原样搬到源码树，**不手改文件内容、不动 TESTS
        分母、不加 --disable-***；搬之前先自证新生成物里确实是我们的 GNU diff 路径，
        对不上就直接失败，避免静默退回 toybox。
        """
        fresh = os.path.join(self.build_folder, "test", "check_common_fn")
        stale = os.path.join(self.source_folder, "test", "check_common_fn")
        if not os.path.exists(fresh):
            raise ConanException("no config.status-generated " + fresh)
        with open(fresh, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        if "@DIFF@" in text:
            raise ConanException("@DIFF@ unsubstituted in " + fresh)
        want = self._gnu_diff_path()
        if want not in text:
            raise ConanException(
                "generated check_common_fn does not use the GNU diffutils diff at "
                + want)
        shutil.copyfile(fresh, stale)
        self.output.info("[GNU diff wired] srcdir check_common_fn <- " + fresh)
    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_ac_tmp()
        autotools = Autotools(self)
        with self._fs_env().vars(self).apply():
            autotools.configure()
            # 把源码树里上游预烧 /usr/bin/diff(=toybox) 的旧生成物换成上面这次
            # configure 生成的那份，否则 DIFF 覆盖传不进 test/check_*.sh。
            self._sync_generated_check_common_fn()
            autotools.make(args=["-j1"])
            # R51：上游 make check 在同一次 conan create 里真跑，不跳过、不裁剪。
            autotools.make(target="check", args=["-j1"])
        self._emit_upstream_test_result()

    def _emit_upstream_test_result(self):
        """从 automake 自己的 test-suite.log 取数上报上游测试判决。

        数字来自测试框架本身（不是估计）；TESTS 分母 8 由 test/Makefile.am 声明，
        XFAIL_TESTS = testassert 是上游自标的预期失败，照实计入 XFAIL 而非当通过。
        """
        suite_logs = []
        for root, _dirs, files in os.walk(self.build_folder):
            if "test-suite.log" in files:
                suite_logs.append(os.path.join(root, "test-suite.log"))
        if not suite_logs:
            raise ConanException(
                "make check produced no test-suite.log under "
                + self.build_folder)
        with open(suite_logs[0], "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        passed = _automake_count(content, "PASS")
        xfailed = _automake_count(content, "XFAIL")
        skipped = _automake_count(content, "SKIP")
        failed = (_automake_count(content, "FAIL")
                  + _automake_count(content, "XPASS")
                  + _automake_count(content, "ERROR"))
        total = _automake_count(content, "TOTAL")
        result = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "automake-parallel-tests",
            "command": "make check",
            "discovered": total,
            "executed": total - skipped,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "xfail": xfailed,
            "log": suite_logs[0],
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        if result["status"] != "passed":
            self.output.error(
                "upstream make check did not pass: " + json.dumps(result))

    def package(self):
        autotools = Autotools(self)
        with self._fs_env().vars(self).apply():
            autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # application：交付物是 bin/ 下的命令行程序（R38 → commands.json）。
        self.cpp_info.bindirs = ["bin"]
        # 上游同时 install libvcdinfo（libvcdinfo.pc 见 configure.ac AC_CONFIG_FILES），
        # 消费者可用；libvcd 是包内私有对象库，不对外声明。
        self.cpp_info.libs = ["vcdinfo"]
