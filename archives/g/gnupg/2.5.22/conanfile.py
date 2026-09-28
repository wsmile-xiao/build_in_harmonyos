#!/usr/bin/env python3
"""Conan recipe — gnupg 2.5.22 (autotools, OHOS).

GnuPG（OpenPGP 实现）：提供 gpg / gpgv / gpgsm / gpg-agent 等。**gpgv** 是
apt Release 签名验证所需（本包为此适配）。

OHOS 适配要点：
- config.guess/config.sub 的 HarmonyOS patch（本 PR 生成，2.5.22 上游不含 ohos）；
- `0003-configure.patch`：① 让 `*-linux-ohos*` 走 android 分支（`require_iconv=no`，
  避免对 libiconv 的强依赖）；② `umask 077` → `022`（HMDFS 上 077 导致临时文件
  权限异常）；
- `0004-gpgconf-link-fallback.patch`：gpgconf 的原子提交用 `link(2)`，而 OHOS 各
  挂载点均拒绝硬链接 → 改为仅在文件系统本身拒绝时回退 `copy_file`（与上游
  HAVE_W32_SYSTEM 分支同构）；
- `0005-gpgscm-tmpdir.patch`：测试框架 `tests/gpgscm/ffi.c` 在非 Windows 平台
  硬编码 `/tmp`，而 OHOS 的 `/tmp` 是只读 erofs → `_mkdtemp` 直接失败、上游测试
  全都跑不起来。改读 `$TMPDIR`；
- `0006-gnupg-tmpfile-tmpdir.patch`：`common/sysutils.c` 的 `gnupg_tmpfile` 在
  musl 下走 `tmpfile()`（编译期 `P_tmpdir`，忽略 `$TMPDIR`）同理失败；
- 关闭非必要子系统以缩小依赖面（card-support/ccid → 免 libusb；ldap/libdns/
  gnutls/ntbtls/selinux → 免对应依赖），保留 gpg/gpgv/gpgsm 核心。
  注：**sqlite3 不再关闭**——它启用 TOFU 与 keyboxd，是上游 tofu/issue2929 用例
  的前置；bzip2 同理用于 4gb-packet 用例。

测试：`build()` 内真实执行上游 `make check`（tests/ 下的 gpgscm 套件），并以
`HMBS_UPSTREAM_TEST_RESULT` marker 输出客观计数。测试期 TMPDIR 会切到本设备
可 AF_UNIX bind 的目录（见 `_bindable_tmpdir`）。

前置依赖：gnupg 2.5.22 要求 `NEED_GPGRT_VERSION=1.56`（libgpg-error ≥ 1.56）；
`libgpg-error/1.61`（PR #9612）**已合入并发布 ohpcd**，依赖已就绪。
"""
import glob
import json
import os
import re
import socket
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnupgConan(ConanFile):
    name = "gnupg"
    version = "2.5.22"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_nls": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_nls": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # gnupg 2.5.22 要求 libgpg-error >= 1.56（NEED_GPGRT_VERSION=1.56）。
        # 而 libgcrypt/1.12.2 配方硬钉 libgpg-error/1.55（1.11.0 亦同）→ 版本冲突。
        # 用 override=True 强制全图统一到 1.61：libgpg-error 1.x 保持 ABI 稳定
        # （soname 仍为 libgpg-error.so.0），libgcrypt 按其 package_folder 取
        # prefix 亦一致，故安全。
        self.requires("libgpg-error/1.61", override=True)
        self.requires("libgcrypt/1.12.2")
        self.requires("libassuan/3.0.2")
        self.requires("libksba/1.6.7.1")
        self.requires("npth/1.8")
        # bzip2：启用 gpg 的 BZIP2 压缩算法（configure 探测 bzlib.h + -lbz2）。
        # 未编译时上游 tests/openpgp/4gb-packet.scm 直接 SKIP
        # （"BZIP2 support not compiled in"）。
        self.requires("bzip2/1.0.8.2")
        # tpm2-tss：TPM 2.0 软件栈（提供 libtss2-esys / -mu / -rc / -tctildr）。
        # gnupg 的 configure 先 `AC_SEARCH_LIBS([Esys_Initialize],[tss2-esys])` 探测
        # **Intel TSS 路径**，探测到才会把 tpm2d 编出来、并进一步 `AC_PATH_PROG(swtpm)`；
        # 两者齐备后 tests/tpm2dtests（4 项：rsa/ecc/longpassphrase/unimportable）
        # 才会进入 SUBDIRS 并真正执行。缺任一 → 该组静默不跑（此前即此状态）。
        self.requires("tpm2-tss/4.2.0")
        # sqlite3：启用 TOFU 信任模型与 keyboxd（configure 经 pkg-config 探测
        # sqlite3）。未启用时 configure 打印 "Building without SQLite support -
        # TOFU and Keyboxd disabled"，上游 tests/openpgp/tofu.scm 与
        # issue2929.scm 均 SKIP（"Tofu not supported"）。
        self.requires("sqlite3/3.49.1")

    def build_requirements(self):
        # openssh：纯构建期工具——上游 tests/openpgp/ssh-import.scm 需要 `ssh-add`
        # （未找到时该用例 SKIP "ssh-add not found"）。用 **tool_requires**（而非
        # test_requires）是为了让 conan 的 VirtualBuildEnv 自动把它的 bindirs
        # （usr/local/bin 等）前置到 build() 的 PATH 上——本配方在 build() 内执行
        # `make check`，必须有 ssh-add 可用。
        # ohpcd 的 openssh/10.0p1 实测含 usr/local/bin/ssh-add。
        # 注意：openssh 不会进入交付产物（tool_requires 不传播给消费者）。
        self.tool_requires("openssh/10.0p1")
        # swtpm：软件 TPM 模拟器，供上游 tests/tpm2dtests 在测试期启动
        # （该组经 tests/tpm2dtests/Makefile 的 `SWTPM="$(SWTPM)"` 传入
        #  start_sw_tpm.sh，以 `swtpm socket --tpm2 ...` 起一个软件 TPM）。
        # 用 **tool_requires**：它是**测试期工具**、不应进入交付产物（与 openssh 同理），
        # 且 conan 的 VirtualBuildEnv 会把其 bindirs 前置到 build() 的 PATH，
        # 使 configure 的 `AC_PATH_PROG(SWTPM, swtpm)` 能探测到。
        self.tool_requires("swtpm/0.10.1.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-all-tests")
        tc.configure_args.append("--disable-doc")
        # ⚠ 不能关 card-support：`keytotpm` 命令**只在 `#ifdef ENABLE_CARD_SUPPORT`
        # 下编译**（g10/keyedit.c:1439-1448），而 ENABLE_CARD_SUPPORT 由 configure 的
        # `card_support` 决定。关闭后 gpg 会报 "Invalid command"，
        # 上游 tests/tpm2dtests 的 4 项（rsa/ecc/longpassphrase/unimportable）便全部
        # 失败于 "key is not in the TPM" —— 这是**构建配置**问题，不是「缺软件 TPM」。
        # 实测对照（同源编译 g10/keyedit.c）：带该宏 `keytotpm` 命中 1，不带为 0。
        # 注：card_support=yes 即上游默认值（configure.ac:117），同时会构建 scdaemon；
        # 内部 CCID 驱动仍需 libusb，未提供时 configure 只提示
        # "without internal CCID driver"（configure.ac:1814），非致命，故下述
        # `--disable-ccid-driver` 保留（避免引入 libusb 依赖）。
        tc.configure_args.append("--disable-ccid-driver")
        tc.configure_args.append("--disable-ldap")
        tc.configure_args.append("--disable-libdns")
        tc.configure_args.append("--disable-gnutls")
        tc.configure_args.append("--disable-ntbtls")
        # 注：原 `--disable-sqlite` 已移除——sqlite3 现为显式依赖，用于启用
        # TOFU 信任模型与 keyboxd（否则上游 tofu.scm / issue2929.scm 会被 SKIP）。
        tc.configure_args.append("--disable-selinux-support")
        tc.configure_args.append("--disable-rpath")
        # 显式给出各 gnupg 家族依赖的 prefix。gnupg 的 m4 宏（AM_PATH_LIBASSUAN /
        # AM_PATH_KSBA / AM_PATH_NPTH / AM_PATH_LIBGCRYPT / AM_PATH_GPG_ERROR）
        # 不会自动在 conan 缓存里找，必须按 --with-<lib>-prefix 指定，否则
        # configure 报 "You need libassuan/libksba/npth to build this program"。
        for _dep, _opt in (
            ("libgpg-error", "--with-libgpg-error-prefix"),
            ("libgcrypt", "--with-libgcrypt-prefix"),
            ("libassuan", "--with-libassuan-prefix"),
            ("libksba", "--with-ksba-prefix"),
            ("npth", "--with-npth-prefix"),
        ):
            try:
                _pf = self.dependencies[_dep].package_folder
            except Exception:
                continue
            if _pf:
                tc.configure_args.append(f"{_opt}={_pf}")

        if not self.options.with_nls:
            tc.configure_args.append("--disable-nls")

        # 关键：libgpg-error 的 .pc 里 prefix 写死为 `/`（conan 的 --prefix=/ 约定），
        # 故 gpgrt-config 代查时输出的是 `-I//include` 与 `-L//lib -lgpg-error`
        # （实测：`gpgrt-config --libdir=<pkg>/lib gpg-error --cflags/--libs`），
        # 导致编译报 `fatal error: 'gpg-error.h' file not found`。而 gnupg 的
        # m4 宏（AM_PATH_GPG_ERROR 等）**不提供** CFLAGS/LIBS 的环境变量覆盖入口，
        # 故改为在工具链层显式补上各依赖真实的 include / lib 目录——不存在的
        # `-I//include` 无害，真正需要的头/库路径由本层保证存在。
        for _dep in ("libgpg-error", "libgcrypt", "libassuan", "libksba", "npth",
                     "bzip2", "sqlite3", "tpm2-tss"):
            try:
                _pf = self.dependencies[_dep].package_folder
            except Exception:
                continue
            _inc = os.path.join(_pf, "include")
            _lib = os.path.join(_pf, "lib")
            if os.path.isdir(_inc):
                tc.extra_cflags.append(f"-I{_inc}")
                tc.extra_cxxflags.append(f"-I{_inc}")
            if os.path.isdir(_lib):
                tc.extra_ldflags.append(f"-L{_lib}")

        tc.generate()

    def _bindable_tmpdir(self):
        """选一个能承载 AF_UNIX 路径名 socket 的 TMPDIR（OHOS 平台限制）。

        OHOS 上 /tmp 是只读 erofs 挂载，而多数可写挂载点（$HOME 下的 HMDFS、
        /dev/shm、conan 构建树）对 AF_UNIX **路径名** bind(2) 返回
        EPERM/EACCES；实测仅 /data/storage/el*/base 可用。
        上游测试框架把 GNUPGHOME 建在 $TMPDIR 之下（tests/openpgp/setup.scm:44
        的 `(setenv "GNUPGHOME" (getcwd) #t)`），gpg-agent 随后要 bind
        "$GNUPGHOME/S.gpg-agent" —— TMPDIR 选错则 agent 起不来，整套测试在
        setup 阶段中止。故这里先探测再选用，而不是无条件用构建树。
        """
        # 目录名刻意取极短（单个字母）：socket 绝对路径还要叠加 mkdtemp 目录名
        # 与 "S.gpg-agent"，而 sockaddr_un.sun_path 上限 108 字节。实测用 71 字符
        # 的 TMPDIR 时 2 项 agent 用例超时，缩到 24 字符后消失。
        for _d in ("/data/storage/el2/base/cache/g",   # CI 自身的 TMPDIR 所在挂载点
                   "/data/storage/el1/base/g",
                   "/data/storage/el3/base/g"):
            if not os.path.isdir(os.path.dirname(_d)):
                continue
            try:
                os.makedirs(_d, exist_ok=True)
                _p = os.path.join(_d, ".probe")
                _s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    _s.bind(_p)
                finally:
                    _s.close()
                os.unlink(_p)
                return _d
            except Exception:
                continue
        _fallback = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_fallback, exist_ok=True)
        return _fallback

    def build(self):
        apply_conandata_patches(self)

        # TMPDIR 必须落在可 bind 的挂载点（见 _bindable_tmpdir）。
        os.environ["TMPDIR"] = self._bindable_tmpdir()

        # 关键：libgpg-error 1.56+ 已**移除** gpg-error-config，只提供 gpgrt-config。
        # 而 `--with-libgpg-error-prefix` 只按约定拼出 $prefix/bin/gpg-error-config
        # （不校验存在性）→ configure 拿到一个不存在的路径；真正的 gpgrt-config
        # 又不在 PATH 中 → GPGRT_CONFIG=no → 报 "You need libgpg-error"。
        # 故显式导出 GPGRT_CONFIG，并把各 gnupg 家族依赖的 bin 目录前置到 PATH
        # （libksba/libassuan/npth 的 AM_PATH_* 同样按 PATH 查找其 -config 工具）。
        try:
            gp = self.dependencies["libgpg-error"].package_folder
            _gpgrt = os.path.join(gp, "bin", "gpgrt-config")
            if os.path.isfile(_gpgrt):
                os.environ["GPGRT_CONFIG"] = _gpgrt
        except Exception:
            pass
        for _dep in ("libgpg-error", "libgcrypt", "libassuan", "libksba", "npth"):
            try:
                _pf = self.dependencies[_dep].package_folder
            except Exception:
                continue
            _bin = os.path.join(_pf, "bin")
            if os.path.isdir(_bin):
                os.environ["PATH"] = _bin + os.pathsep + os.environ.get("PATH", "")

        # 关键（npth 场景）：npth 1.8 的 conan 包**不提供 bin/npth-config**，只有
        # lib/pkgconfig/npth.pc。而 gnupg 的 m4/npth.m4 在找不到 npth-config 时会
        # 回退到 `$GPGRT_CONFIG npth`（即 gpgrt-config 代查 npth.pc）——该回退要求
        # gpgrt-config 能通过 PKG_CONFIG_PATH 找到 npth.pc。实测：
        #   PKG_CONFIG_PATH=<npth>/lib/pkgconfig gpgrt-config npth --exists  → rc=0
        # 故把所有依赖的 lib/pkgconfig 前置到 PKG_CONFIG_PATH。
        # 另：sqlite3 的 configure 探测走 pkg-config（`No package 'sqlite3' found`
        # 时打印 "Building without SQLite support - TOFU and Keyboxd disabled"），
        # 实测 PKG_CONFIG_PATH=<sqlite3>/lib/pkgconfig pkg-config --exists sqlite3 → rc=0。
        # bzip2 无 .pc（仅 bzlib.h + libbz2.a），列入无副作用。
        _pcs = []
        for _dep in ("libgpg-error", "libgcrypt", "libassuan", "libksba", "npth",
                     "bzip2", "sqlite3", "tpm2-tss"):
            try:
                _pf = self.dependencies[_dep].package_folder
            except Exception:
                continue
            _pc = os.path.join(_pf, "lib", "pkgconfig")
            if os.path.isdir(_pc):
                _pcs.append(_pc)
        if _pcs:
            _old = os.environ.get("PKG_CONFIG_PATH", "")
            os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(
                _pcs + ([_old] if _old else []))

        # 关键（sqlite3 场景）：gnupg 用 `PKG_CHECK_MODULES([SQLITE3], [sqlite3 >= 3.27])`
        # 探测 SQLite，而本仓 sqlite3 配方的 package() **只装 bin/libsqlite3.a/include/*.h，
        # 不装 lib/pkgconfig/sqlite3.pc**（实测构建实际使用的变体
        # ~/.conan2/p/sqlitaf82001134154/p 下无 lib/pkgconfig）→ configure 报
        # `checking for SQLITE3... no` + `No package 'sqlite3' found`
        # → "Building without SQLite support - TOFU and Keyboxd disabled"
        # → 上游 tests/openpgp/tofu.scm 与 issue2929.scm 被 SKIP "Tofu not supported"。
        #
        # 修法：pkg.m4 生成的探测代码在**预设** SQLITE3_CFLAGS / SQLITE3_LIBS 时直接采用、
        # 完全跳过 pkg-config（实测 configure 对应分支：
        #   `if test -n "$SQLITE3_CFLAGS"; then pkg_cv_SQLITE3_CFLAGS="$SQLITE3_CFLAGS"`，
        # 另一处同理 for LIBS）。故按依赖实际路径预设这两个变量——既不改动 sqlite3
        # 配方（避免新增已发布制品的变体，R37），也无需 .pc 文件。
        try:
            _sq = self.dependencies["sqlite3"].package_folder
            os.environ["SQLITE3_CFLAGS"] = f"-I{os.path.join(_sq, 'include')}"
            os.environ["SQLITE3_LIBS"] = f"-L{os.path.join(_sq, 'lib')} -lsqlite3"
        except Exception:
            pass

        autotools = Autotools(self)
        autotools.configure()
        # gnupg 为并行安全的标准 autotools 工程；构建机 nproc=8，-j1 串行过慢。
        autotools.make(args=["-j4"])

        # ── L1：在 build() 内真实执行上游 make check ──
        # build_and_test.sh:1351 明确「CI 必须始终重新构建目标包，确保运行
        # make check + test_package」——CI 不会替我们跑测试，必须在配方里跑。
        #
        # 运行期库路径：测试二进制在编译期被写入指向**打包机 conan home** 的
        # RUNPATH，CI 上该路径不存在 → 报
        #   "Error loading shared library libgcrypt.so.20" /
        #   "Error relocating ./gpgscm: gpgrt_setusage: symbol not found"
        # （实测复现）。故把依赖闭包的 lib 目录注入 LD_LIBRARY_PATH，
        # 让 musl 先于 RUNPATH 命中。
        _libs = []
        # 注：tpm2-tss 必须在此列表内——`tpm2d/tpm2daemon` 的 NEEDED 含
        # libtss2-esys.so.0 / -mu / -rc / -tctildr，缺这些库时 tpm2daemon 起不来，
        # gpg 便回退为「密钥不在 TPM 中」，4 项 tpm2dtests 全报
        # "key is not in the TPM" / "Importing Key succeeded"（实测）。
        for _dep in ("libgpg-error", "libgcrypt", "libassuan", "libksba", "npth",
                     "bzip2", "sqlite3", "tpm2-tss"):
            try:
                _l = os.path.join(self.dependencies[_dep].package_folder, "lib")
            except Exception:
                continue
            if os.path.isdir(_l):
                _libs.append(_l)
        # ssh-add 来自 tool_requires("openssh")（build 上下文），其自身还链接
        # libcrypto/libssl 等。若不把它的 lib 目录一并注入，ssh-add 会因缺库无法
        # 启动 → tests/openpgp/ssh-import.scm 由"跳过"变成"失败"。故一并加入。
        try:
            _ol = os.path.join(self.dependencies.build["openssh"].package_folder, "lib")
            if os.path.isdir(_ol):
                _libs.append(_ol)
        except Exception:
            pass
        if _libs:
            _old_ld = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                _libs + ([_old_ld] if _old_ld else []))

        _check_log = os.path.join(self.build_folder, "upstream-make-check.log")
        # ssh-add：tests/openpgp/ssh-import.scm 用 `path-expand "ssh-add" (PATH)`
        # 查找，找不到就 skip。conan 为 tool_requires 生成的 VirtualBuildEnv 里
        # 那条 PATH 实测指向 **不存在的** 包目录（.../p/<hash>/p/usr/local/bin），
        # 导致该用例仍被 SKIP。故这里直接从依赖解析出 openssh 的包目录，把其中
        # 含 ssh-add 的 bin 目录显式前置到 PATH（不依赖 conan env 文件的正确性）。
        _osh_bins = []
        for _ctx in ("build", None):
            try:
                _od = (self.dependencies.build["openssh"] if _ctx == "build"
                       else self.dependencies["openssh"])
                _opf = _od.package_folder
            except Exception:
                continue
            if not _opf:
                continue
            # 候选目录：包目录下的常见 bindir，以及本地构建时包目录的兄弟
            # build 目录（.../b/<hash>/b/build-release）。必须**实测可执行**再选用：
            # OHOS 上部分已打包二进制 exec 会报 EPERM（签名/装载限制），若选到这类
            # 目录，ssh-import.scm 会从"跳过"变成"失败"（`ssh -V` 输出被
            # 误判为 "This doesn't look like OpenSSH"）。故逐个验证 ssh-add -h。
            _sib_build = os.path.join(os.path.dirname(_opf), "b")
            for _cand in (os.path.join(_opf, "usr/local/bin"),
                          os.path.join(_opf, "bin"),
                          os.path.join(_opf, "usr/local/sbin"),
                          os.path.join(_sib_build, "build-release"),
                          _sib_build):
                # 该用例同时需要 ssh / ssh-add / ssh-keygen 三者。
                _need = ("ssh", "ssh-add", "ssh-keygen")
                if not all(os.path.isfile(os.path.join(_cand, t)) for t in _need):
                    continue
                # 用与该用例**完全相同的判据**来验证可执行：它执行 `ssh -V` 并
                # 要求输出以 "OpenSSH_" 开头，否则 skip "This doesn't look like
                # OpenSSH"。OHOS 上部分已打包二进制 exec 直接报 EPERM（输出为空/
                # 无 OpenSSH_），据此即可筛掉。
                try:
                    _r = subprocess.run([os.path.join(_cand, "ssh"), "-V"],
                                        capture_output=True, timeout=30)
                except Exception:
                    continue
                _out = (_r.stdout + _r.stderr).decode("utf-8", "replace")
                if "OpenSSH_" not in _out:
                    continue
                _osh_bins.append(_cand)
                break
            if _osh_bins:
                break
        if _osh_bins:
            os.environ["PATH"] = os.pathsep.join(_osh_bins + [os.environ.get("PATH", "")])
            self.output.info(f"ssh-add dir prepended to PATH: {_osh_bins[0]}")
        else:
            self.output.warning("ssh-add not located; ssh-import.scm will be skipped")
        # ⚠ 测试期 TMPDIR 必须改到**可 AF_UNIX 路径名 bind** 的目录。
        # 构建期用的 self.build_folder/_tmp（上面的 _tmp）在 OHOS 上 **不可 bind**
        # （HMDFS 拒绝），而上游测试框架把 GNUPGHOME 建在临时目录之下
        # （tests/openpgp/setup.scm:44 `(setenv "GNUPGHOME" (getcwd) #t)`）→
        # gpg-agent 的 S.gpg-agent 落点由 TMPDIR 决定 → 指向构建树会在 setup
        # 阶段整包中止（"IPC connect call failed"）。实测可用落点为
        # /data/storage/el1/base 与 CI 自身的 /data/storage/el2/base/cache。
        _gpgtmp = self._bindable_tmpdir()
        os.environ["TMPDIR"] = _gpgtmp
        self.output.info(f"upstream tests TMPDIR={_gpgtmp}")
        if _gpgtmp.startswith(self.build_folder):
            self.output.warning(
                "未找到可 AF_UNIX bind 的目录，退回构建树；"
                "fork gpg-agent 的用例预期失败")
        # 上游 `make check` 递归进各子系统；tests/ 下的 gpgscm 驱动套件即上游
        # 集成测试（openpgp/cms/migrations/gpgme/pkits）。tpm2dtests 仅在探测到
        # 软件 TPM 时才进入 SUBDIRS，这里无 TPM，故不会因缺 TPM 而报失败。
        #
        # ⚠ 必须显式 -j1：Autotools.make 在未指定 -j 时会自动注入 `-j<nproc>`
        # （实测本机为 -j20）。而每个 gpgscm 用例都会 fork gpg-agent 等进程，
        # 20 路并发会瞬间耗尽内存——实测触发 "fork failed: out of memory"，
        # 连 `make` 自身都无法继续（load 一度飙到 26）。测试阶段串行执行。
        # ⚠ 必须把 PATH 作为 **make 命令行变量** 传入，只改 os.environ 无效：
        # ① 上游 tests/openpgp/Makefile 的 TESTS_ENVIRONMENT 执行
        #      PATH="../gpgscm:$(PATH)"
        # ② conan 的 run() 在启动子进程前会重新应用 buildenv，把 tool_requires
        #    生成的 PATH 重新顶到最前——而该目录里的二进制在本机 exec 报
        #    EPERM（见上方说明），用例执行 `ssh -V` 取不到 "OpenSSH_" 前缀，
        #    于是打印 "This doesn't look like OpenSSH" 并 skip。
        # make 命令行变量优先级高于环境变量，故只有由它喂给 $(PATH) 才真正生效。
        # 实测：用命令行 PATH 时 ssh-import.scm 由 SKIP 转为 PASS。
        _make_args = ["-j1", f"> {_check_log} 2>&1"]
        if _osh_bins:
            _make_args.insert(0, f"PATH={os.environ.get('PATH', '')}")
        autotools.make(target="check", args=_make_args)
        self._report_upstream_tests(_check_log)

    def _report_upstream_tests(self, check_log):
        """解析 `make check` 输出，打印规范 marker；有失败则显式抛错。

        上游（automake 风格）每个套件输出一行汇总：
          "64 tests run, 64 succeeded, 0 failed, 0 failed expectedly,
           0 succeeded unexpectedly, 0 skipped."
        另统计 PASS/FAIL/SKIP 行数作为交叉校验。
        """
        _pat = re.compile(
            r"(\d+) tests run, (\d+) succeeded, (\d+) failed, "
            r"(\d+) failed expectedly, (\d+) succeeded unexpectedly, (\d+) skipped")
        run = ok = bad = skip = 0
        suites = 0
        try:
            _text = open(check_log, encoding="utf-8", errors="replace").read()
        except OSError:
            _text = ""
        for _m in _pat.finditer(_text):
            suites += 1
            run += int(_m.group(1))
            ok += int(_m.group(2))
            bad += int(_m.group(3)) + int(_m.group(5))
            skip += int(_m.group(6))

        # tests/gpgscm 只跑一个 check-local（t-child.scm），成功时打印 "All good."，
        # **没有** automake 风格汇总行，故上面的累加会漏掉它，需单独计入。
        if re.search(r"All good\.", _text):
            run += 1
            ok += 1

        _pass_lines = len(re.findall(r"^PASS:", _text, re.M))
        _fail_lines = len(re.findall(r"^(?:FAIL|ERROR):", _text, re.M))

        if suites == 0 and _pass_lines == 0:
            raise ConanException(
                "upstream `make check` produced no recognisable test results; "
                f"see {check_log}")

        status = "passed" if (bad == 0 and _fail_lines == 0) else "failed"
        _payload = {
            "status": status,
            "framework": "gpgscm",
            "command": "make check",
            "discovered": run + skip,
            "executed": run,
            "passed": ok,
            "failed": bad,
            "skipped": skip,
            "pass_lines": _pass_lines,
            "fail_lines": _fail_lines,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(_payload, ensure_ascii=False))
        if status != "passed":
            _tail = "\n".join(_text.splitlines()[-40:])
            self.output.error(f"=== upstream make check tail ===\n{_tail}")
            raise ConanException(
                f"upstream tests failed: {bad} failed (see {check_log})")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
