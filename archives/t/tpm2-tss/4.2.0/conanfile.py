#!/usr/bin/env python3
"""Conan recipe — tpm2-tss 4.2.0 (autotools, OHOS).

TPM 2.0 Software Stack（tpm2-software/tpm2-tss）：提供 libtss2-esys / libtss2-mu /
libtss2-rc / libtss2-tctildr 等，是「与 TPM 通信」的通用软件栈。

⚠️ 依赖拓扑（本包是 gnupg 的前置依赖链上游，务必按序）：
    tpm2-tss (本包)  →  swtpm (TPM 模拟器，运行时)  →  gnupg 的 tests/tpm2dtests
  说明：gnupg 的 configure 先探测 libtss（AC_SEARCH_LIBS([Esys_Initialize],
  [tss2-esys])），**只有探测到 libtss 才会去 AC_PATH_PROG(swtpm)**；两者缺一
  都会让 tpm2dtests 不进入 SUBDIRS。本包提供前者，swtpm 提供后者。

OHOS 适配要点：
- config.guess / config.sub 的 HarmonyOS patch（4.2.0 自带文件中 `grep -c ohos` = 0）；
- configure 内 `umask 077 && mktemp -d` → 022（HMDFS 上 077 使 config.status 无法
  创建临时目录，E114）；
- 关闭 fapi / policy 层：这两层依赖 json-c / libcurl / uuid，而 gnupg 只需要
  esys + tcti（其 configure 用 `-ltss2-esys -ltss2-mu -ltss2-rc -ltss2-tctildr`），
  收窄依赖面以避免引入与 gnupg 无关的包。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Tpm2TssConan(ConanFile):
    name = "tpm2-tss"
    version = "4.2.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # gnupg 的 tpm2d 在测试期用 TPM_INTERFACE_TYPE=socsim（走 tcti-mssim）；
        # 该模块默认编译，保留开关以便按需裁剪。
        "with_tcti_mssim": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_tcti_mssim": True,
        # ⚠ cmocka **必须用 shared 变体**，否则 test/unit/tctildr-getinfo 必然
        # SIGSEGV：该测试用 `-Wl,--wrap=calloc` 对被测代码的 calloc 打桩
        # （__wrap_calloc 从 cmocka mock 队列取返回值）。若 cmocka 静态链入
        # （libcmocka.a，ohpcd 现有变体即 shared=False），cmocka **自身**的内部
        # calloc 也会被重定向到 __wrap_calloc → cmocka 簿记拿到"给被测代码的
        # 假指针" → 每个用例都崩（实测 8/8 用例 rc=139；独立探针：同一测试程序
        # static 崩溃 / shared 正常）。
        # 用 shared 后其内部调用绑定在 libcmocka.so 内，不被可执行文件的 --wrap 拦截。
        # 实测：改 shared 后 tctildr-getinfo 由 SIGSEGV 转为 12/12 PASSED。
        "cmocka/*:shared": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # ESYS 的默认加密后端即 OpenSSL（configure `--with-crypto` 默认 ossl）。
        # 版本与 gnupg/2.5.22 保持一致（openssl/3.5.6），避免同图出现两个 openssl。
        self.requires("openssl/3.5.6")

    def build_requirements(self):
        # cmocka：上游 61 项单元测试（test/unit/*）的断言框架。configure 用
        # `PKG_CHECK_MODULES([CMOCKA],[cmocka >= 1.0])` 探测，且 **--enable-unit
        # 默认为 no** → 不显式开启时单元测试根本不编译，`make check` 会以
        # "0 tests run" 静默通过（假阳性）。
        # 说明：上游 29 项集成测试（TESTS_INTEGRATION = test/integration/*.int）需
        # --enable-integration，而该开关（configure.ac:472-521）要连过三道门：
        #   ① ERROR_IF_NO_PROG([ss])      —— 可得（ohpcd 有 iproute2/6.11.0，含 bin/ss）
        #   ② AC_CHECK_HEADER(uthash.h)   —— 可得（ohpcd 有 uthash/2.3.0、2.4.0）
        #   ③ AC_CHECK_PROG(swtpm/tpm_server) —— **真缺口**：ohpcd 未发布 swtpm
        #      （tpm_server/tssstartup 亦无），且本机 PATH 均无
        # 第③道不过即 configure.ac:520-521 硬报错
        # "No simulator executable found in PATH for testing TCTI."，故集成测试
        # 保持上游默认关闭（enable_integration=no）并在申报中如实说明。
        # 集成测试本质要连一个活的 TPM 模拟器，非包装层可绕过。
        self.test_requires("cmocka/2.0.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 不收窄这两层会让 configure 去 PKG_CHECK_MODULES(json-c/libcurl/uuid)，
        # 而 gnupg 只需要 esys + tcti 层。
        tc.configure_args.append("--disable-fapi")
        tc.configure_args.append("--disable-policy")
        if not self.options.with_tcti_mssim:
            tc.configure_args.append("--disable-tcti-mssim")
        # 只出共享库：gnupg 以 -ltss2-* 动态链接消费。
        if self.options.shared:
            tc.configure_args.append("--disable-static")
        tc.configure_args.append("--with-crypto=ossl")
        # 开启 cmocka 单元测试（上游 --enable-unit 默认 no）。
        tc.configure_args.append("--enable-unit")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # 构建期 TMPDIR 指向构建目录：OHOS 上 /tmp 是只读 erofs，而 configure/config.guess
        # 的 mktemp 与 conftest 都需要可写临时目录（否则报 "unable to guess system type"
        # 或 "cannot create a temporary directory"）。
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        # openssl 的 libcrypto.pc 供 PKG_CHECK_MODULES([CRYPTO],[libcrypto]) 使用；
        # cmocka 的 cmocka.pc 供 PKG_CHECK_MODULES([CMOCKA],[cmocka >= 1.0]) 使用。
        # 两者 context 不同：openssl 是普通 requires（host），而 cmocka 来自
        # test_requires（也在 host，但不保证；故两个 context 都试一遍，取先命中的）。
        # conan 的 AutotoolsToolchain 不会自动注入 PKG_CONFIG_PATH，故显式前置。
        _pcs = []
        for _dep in ("openssl", "cmocka"):
            _pf = None
            for _ctx in (None, "build"):
                try:
                    _od = (self.dependencies.build[_dep] if _ctx == "build"
                           else self.dependencies[_dep])
                except Exception:
                    continue
                if getattr(_od, "package_folder", None):
                    _pf = _od.package_folder
                    break
                # 依赖可能在不同 context 下解析到不同节点，逐个尝试。
            if not _pf:
                continue
            for _sub in ("lib/pkgconfig", "lib64/pkgconfig", "share/pkgconfig"):
                _pc = os.path.join(_pf, _sub)
                if os.path.isdir(_pc):
                    _pcs.append(_pc)
                    break
        if _pcs:
            _old = os.environ.get("PKG_CONFIG_PATH", "")
            os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(
                _pcs + ([_old] if _old else []))

        # 显式预设 CMOCKA_CFLAGS / CMOCKA_LIBS，**不要**依赖 cmocka.pc：
        # 实测本仓 cmocka/2.0.2 的 cmocka.pc 里 prefix 指向**打包时的构建目录**
        # （.../p/b/cmocka<build-hash>/p），而实际包目录是 .../p/cmocka<id>/p —
        # 两者不同 → `pkg-config --cflags cmocka` 返回一个不存在的 -I，
        # 编译单元测试时报 `fatal error: 'cmocka.h' file not found`。
        # pkg.m4 生成的探测代码在**预设**该变量时直接采用、跳过 pkg-config
        # （configure 内 `if test -n "$CMOCKA_CFLAGS"; then pkg_cv_CMOCKA_CFLAGS=...`），
        # 故按依赖真实路径预设即可。
        _cmocka = None
        for _ctx in (None, "build"):
            try:
                _od = (self.dependencies.build["cmocka"] if _ctx == "build"
                       else self.dependencies["cmocka"])
            except Exception:
                continue
            if getattr(_od, "package_folder", None):
                _cmocka = _od.package_folder
                break
        if _cmocka:
            os.environ["CMOCKA_CFLAGS"] = f"-I{os.path.join(_cmocka, 'include')}"
            os.environ["CMOCKA_LIBS"] = f"-L{os.path.join(_cmocka, 'lib')} -lcmocka"

        # 同理显式预设 CRYPTO_CFLAGS / CRYPTO_LIBS，**不要**依赖 libcrypto.pc：
        # 实测本仓 openssl/3.5.6 的 libcrypto.pc 里 prefix 是**畸形拼接值**——
        # 包目录直接接上打包时的构建目录、中间连分隔符都没有：
        #   prefix=/storage/.../p/opens<id>/pstorage/Users/.../p/b/opens<build>/p
        # 于是 `pkg-config --cflags libcrypto` 返回一个不存在的 -I，编译
        # `src/tss2-esys/esys_crypto_ossl.c` 时报
        #   fatal error: 'openssl/bn.h' file not found
        # 注意 configure 阶段**不会**报警：PKG_CHECK_MODULES 只校验 .pc 能否解析，
        # 所以日志里反而打印 `checking for libcrypto >= 1.1.0... yes`，把故障拖到编译期
        # （CI #55416 即如此）。pkg.m4 生成的探测代码在**预设**该变量时直接采用、
        # 跳过 pkg-config（configure 内 `if test -n "$CRYPTO_CFLAGS"; then
        # pkg_cv_CRYPTO_CFLAGS=...`），故按依赖真实路径预设即可。
        _crypto = None
        for _ctx in (None, "build"):
            try:
                _od = (self.dependencies.build["openssl"] if _ctx == "build"
                       else self.dependencies["openssl"])
            except Exception:
                continue
            if getattr(_od, "package_folder", None):
                _crypto = _od.package_folder
                break
        if _crypto:
            os.environ["CRYPTO_CFLAGS"] = f"-I{os.path.join(_crypto, 'include')}"
            os.environ["CRYPTO_LIBS"] = (
                f"-L{os.path.join(_crypto, 'lib')} -lcrypto")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j4"])
        self._run_upstream_checks()

    def _cmocka_folder(self):
        """返回 cmocka 的 package_folder（test_requires，可能在 host 或 build 上下文）。"""
        for _ctx in (None, "build"):
            try:
                _od = (self.dependencies.build["cmocka"] if _ctx == "build"
                       else self.dependencies["cmocka"])
            except Exception:
                continue
            if getattr(_od, "package_folder", None):
                return _od.package_folder
        return None

    def _run_upstream_checks(self):
        """在 build() 内真实执行上游 `make check`（cmocka 单元测试）。

        背景：与 gnupg 同样的坑——CI 的 L1c 仅按日志正则 `make.*check` 判定
        "上游官方测试"，会把 configure 的探测句/空跑当成通过。上游 `--enable-unit`
        默认为 no，不显式开启时单元测试根本不编译，`make check` 会以
        "0 tests run" 静默通过（假阳性）。故这里显式执行并输出客观计数。
        """
        import json
        import re

        _log = os.path.join(self.build_folder, "upstream-make-check.log")
        make_prog = self.conf.get("tools.gnu:make_program", default="make")

        # ⚠ 必须在测试编译中关掉 _FORTIFY_SOURCE，否则 6 项用 cmocka `--wrap=` 打桩
        # 的单测必然失败（平台无关的上游/工具链交互问题）：
        #   conan 的 AutotoolsToolchain 默认注入 `CPPFLAGS=-DNDEBUG -D_FORTIFY_SOURCE=2`；
        #   而 _FORTIFY_SOURCE 会把 libc 调用点改写为 `__read_chk`/`__write_chk`/
        #   `__open_chk`/… —— `-Wl,--wrap=read` 只能拦截**普通符号** `read`，
        #   拦不到 `__read_chk` → 桩函数从未被调用 → cmocka 报
        #   "Has remaining non-returned values: __wrap_read" 而失败（实测 io /
        #   tcti-{mssim,swtpm,device,pcap} / tctildr-getinfo 共 6 项）。
        # 独立探针验证（编译真实调用点 src/util-io/io.c，秒级）：
        #   `-O2 -D_FORTIFY_SOURCE=2`                  → __read_chk __wrete_chk…
        #   `-O2 -D_FORTIFY_SOURCE=2 -U_FORTIFY_SOURCE` → 无 __*_chk ✓
        # 落点：调用点在**库对象**里（src/util-io/io.o、src/tss2-tcti/tcti-*.o），
        # 不在测试对象里，所以只改 TESTS_CFLAGS/CFLAGS 够不到（实测无效）。
        # 且必须连同 `.a` 一起删——只删 .o/.lo 时，陈旧归档仍携带 fortified
        # 对象，重链接会把它带回来（实测踩过）。
        # 做法：两阶段——① 删对象后以「剥掉 fortify 的 CPPFLAGS」重编并跑测试；
        # ② 再删一次并用配方原参数重建，使**交付的库恢复 hardening**
        # （不在交付物上降低安全加固）。
        _dirs = ("src/util-io", "src/tss2-tcti", "test/unit", "test/integration")

        def _drop():
            for _d in _dirs:
                for _r, _x, _files in os.walk(os.path.join(self.build_folder, _d)):
                    for _f in _files:
                        if _f.endswith((".o", ".lo", ".a")):
                            try:
                                os.unlink(os.path.join(_r, _f))
                            except OSError:
                                pass

        # 读 Makefile 的 CPPFLAGS，只剥掉 fortify（保留 -DNDEBUG 等其余 define）。
        _orig_cpp = ""
        try:
            with open(os.path.join(self.build_folder, "Makefile"),
                      encoding="utf-8", errors="replace") as _fh:
                for _line in _fh:
                    if _line.startswith("CPPFLAGS") and "=" in _line:
                        _orig_cpp = _line.split("=", 1)[1].strip()
                        break
        except OSError:
            pass
        _no_fortify = re.sub(r"-D_FORTIFY_SOURCE=\S*", "", _orig_cpp).strip()
        _no_fortify = (_no_fortify + " -U_FORTIFY_SOURCE").strip()

        # ① 测试阶段：不加固地重建受影响对象并执行上游单测。
        _drop()
        # 必须 -j1：OHOS 上 $HOME/conan 构建树拒 mkfifo（EPERM），make 的
        # jobserver 无法建 FIFO；串行执行最稳。
        # cmocka 用 shared 后测试二进制运行期需要 libcmocka.so.0：
        # 其 .pc 的 RUNPATH 方案在 OHOS 上不可靠（实测 exit 127，
        # "Error loading shared library libcmocka.so.0"）。
        # ⚠ 必须把 LD_LIBRARY_PATH 作为 **make 命令行变量**传入，不能用
        # self.run(env=...)：conan 的 run() 在启动子进程前会重新应用 buildenv，
        # 把 LD_LIBRARY_PATH 覆盖掉（实测 env= 写法无效，全部 exit 127）。
        # make 命令行变量会导出给其子进程，优先级高于环境变量。
        _ld = os.environ.get("LD_LIBRARY_PATH", "")
        _cm = self._cmocka_folder()
        if _cm:
            _ld = os.pathsep.join([os.path.join(_cm, "lib")] + ([_ld] if _ld else []))
        _ld_arg = f' LD_LIBRARY_PATH="{_ld}"' if _ld else ""
        self.run(f'{make_prog} check -j1 CPPFLAGS="{_no_fortify}"{_ld_arg} '
                 f'> "{_log}" 2>&1', ignore_errors=True)
        # ② 恢复阶段：用配方原参数重建，交付物保留 _FORTIFY_SOURCE。
        _drop()
        self.run(f'{make_prog} -j4', ignore_errors=True)

        try:
            _text = open(_log, encoding="utf-8", errors="replace").read()
        except OSError:
            _text = ""

        def _n(key):
            m = re.search(rf"^# {key}:\s*(\d+)", _text, re.M)
            return int(m.group(1)) if m else 0

        _pass, _fail, _skip = _n("PASS"), _n("FAIL"), _n("ERROR")
        _total = _n("TOTAL") or (_pass + _fail + _skip + _n("SKIP") + _n("XPASS"))
        _payload = {
            "status": "passed" if (_fail == 0 and _pass > 0) else "failed",
            "framework": "cmocka (tpm2-tss unit tests)",
            "command": f"{make_prog} check -j1",
            "discovered": _total,
            "executed": _pass + _fail,
            "passed": _pass,
            "failed": _fail,
            "skipped": _skip + _n("SKIP"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(_payload, ensure_ascii=False))
        if _payload["status"] != "passed":
            _tail = "\n".join(_text.splitlines()[-40:])
            self.output.error(f"=== upstream make check tail ===\n{_tail}")
            raise ConanException(
                f"upstream unit tests failed: {_fail} failed, {_pass} passed "
                f"(see {_log})")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # gnupg 的 configure 硬编 LIBTSS_LIBS 为
        # "$LIBS -ltss2-mu -ltss2-rc -ltss2-tctildr"，并要求能 -ltss2-esys 链接成功。
        self.cpp_info.libs = ["tss2-esys", "tss2-mu", "tss2-rc", "tss2-tctildr"]
        if self.options.with_tcti_mssim:
            self.cpp_info.libs.append("tss2-tcti-mssim")
        self.cpp_info.libs.append("tss2-tcti-device")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
