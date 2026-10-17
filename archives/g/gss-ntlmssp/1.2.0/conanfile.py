#!/usr/bin/env python3
"""Conan recipe — gss-ntlmssp 1.2.0（GSSAPI NTLMSSP 机制模块）。

W0 实测（2026-09-25，全部一手命令）：
- 版本可得性：`git ls-remote --tags https://github.com/gssapi/gss-ntlmssp` →
  `refs/tags/v1.2.0` = 3c3077e2a24b47db1b4c459fb3173ba7f75b9b44；GitHub 无 release
  资产（releases/download/v1.2.0/gss-ntlmssp-1.2.0.tar.gz → 404，API 匿名限流），
  源取 tag 归档 tarball（sha256 见 conandata.yml，`sha256sum` 实测）。
- 硬依赖（conan list + 真实 `conan install --build=never`（-pr ci/conan/profiles/ohos-aarch64）
  双证在档）：krb5/1.22.1（包内 bin/krb5-config、include/gssapi/*、libgssapi_krb5.so 实物核过）、
  libunistring/1.0、openssl/3.0.21、zlib/1.3.1；iconv 由 OHOS libc 提供
  （设备探针 iconv_open("UTF16LE","UTF-8") + 转换 rc=0 → 不需要 libiconv）。
- configure.ac 硬门禁（缺一即 AC_MSG_ERROR）：GSSAPI（gssapi/gssapi.h + krb5-config +
  libgssapi_krb5 的 gss_import_cred/gss_export_cred）、libunistring（unicase.h/uniconv.h +
  u8_toupper）、OpenSSL（AX_CHECK_OPENSSL）、zlib（AX_CHECK_ZLIB）、pthread。
- 可选面显式关闭：wbclient（ohpcd `*wbclient*` 0 命中）→ --without-wbclient；
  NLS（设备/CI 均无 msgfmt）→ --disable-nls；manpage（docbook-xsl/xsltproc 缺）→
  --without-manpages；doxygen 缺省 `false` 不拦。
- 上游 tag 归档不含 configure/（无发行 tarball）→ build() 内 `autoreconf -f -i`；
  tool_requires autoconf+automake+libtool 三件套同源提供（CI worker 无 automake/libtool，
  device-facts §一.4；conan perl 与 autoreconf 同族避免 PERL5LIB ABI 崩溃，§一.23）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GssNtlmsspConan(ConanFile):
    name = "gss-ntlmssp"
    version = "1.2.0"
    description = "GSSAPI NTLMSSP authentication mechanism module (gss-ntlmssp)"
    license = "MIT"
    homepage = "https://github.com/gssapi/gss-ntlmssp"
    url = "https://github.com/gssapi/gss-ntlmssp"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}  # GSSAPI 机制是 dlopen 模块，必须共享链接

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 四件全部为 configure.ac 的硬门禁（见文件头），均已实测 `--build=never` 可取二进制
        self.requires("krb5/1.22.1")      # GSSAPI：gssapi/gssapi.h + krb5-config + libgssapi_krb5
        self.requires("libunistring/1.0")  # unicase.h/uniconv.h + u8_toupper（ohpcd 仅静态二进制）
        self.requires("openssl/3.0.21")    # AX_CHECK_OPENSSL 硬错
        self.requires("zlib/1.3.1")        # AX_CHECK_ZLIB 硬错

    def build_requirements(self):
        # tag 归档无 configure → autoreconf 自举；三件套同源（见文件头）
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # 可选面关闭（wbclient 不在档 / NLS 与 manpage 工具链缺，均非主功能）
        tc.configure_args.append("--without-wbclient")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--without-manpages")
        # 显式双三元组（止损先例 #1 / sdl-image·abiword 形态 B）：设备 uname -s =
        # `HarmonyOS`（config.guess 2024-07-27 不识别 → `cannot guess build type`）；
        # build==host ⇒ configure 按本地构建跑 conftest（不交叉），config.guess 不再被调用。
        # 用 gnu 通用三元组（config.sub 2024 原生接受；-linux-ohos 需补 config.sub，
        # 本包无该需求）。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # OpenSSL：AX_CHECK_OPENSSL 先试 `pkg-config openssl`（conan 的 openssl.pc
        # 不在默认 PKG_CONFIG_PATH，必然失败）再退固定前缀（/usr/local/ssl… 设备全无），
        # 而最终 AC_LINK_IFELSE 的 LIBS 已被 configure.ac:69 覆写（无 -lssl）→ 必报
        # "Could not find OpenSSL support"（首轮实测）。--with-openssl=DIR 走该宏的
        # 用户目录分支：头/库路径与 -lssl -lcrypto 全由宏注入。
        _ssl_pf = None
        for _n, _d in self.dependencies.host.items():
            if _d.ref.name == "openssl":
                _ssl_pf = _d.package_folder
        if not _ssl_pf or not os.path.isfile(os.path.join(_ssl_pf, "include", "openssl", "ssl.h")):
            raise ConanException(f"openssl 依赖包头文件缺失: {_ssl_pf}")
        tc.configure_args.append(f"--with-openssl={_ssl_pf}")
        tc.generate()
        # 依赖 -I/-L 注入（CPPFLAGS/LDFLAGS/LIBS 走 conanautotoolsdeps 环境）：
        # configure 的 AC_CHECK_HEADERS(gssapi/gssapi.h)/AC_CHECK_LIB 靠它；
        # 缺失时 AC_CHECK_LIB 只做链接探测会假绿，错到 make 才暴露（容器模板修订 1）
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)

        # ── 运行/构建环境注入（全部用可 grep 的显式行，落日志）────────────────
        # 0) tool_requires 的 bin 前置（device-facts §一.23 毒丸实测）：
        #    conanbuildenv 的 PATH 里 /data/service/hnp/bin 排在 tool_requires 之前，
        #    裸调 autoreconf 会命中 HNP 的 perl 脚本，而 PERL5LIB 已指向 conan 的
        #    perl 5.42.2 XS 模块 → HNP perl 5.42.0 加载即崩
        #    （`Perl_my_cxt_init: symbol not found`，本任务首轮实测 rc=255）。
        #    解法=让 autoreconf/aclocal/libtoolize/perl 四者全部取 conan 包内路径，
        #    与 PERL5LIB 同族同版本（11 个仓库先例"显式 tool_requires"的实质即此，
        #    还需 PATH 优先级这一半）。
        tool_bins = []
        for _tname, _tdep in self.dependencies.build.items():
            _tpf = getattr(_tdep, "package_folder", None)
            _tbin = os.path.join(_tpf, "bin") if _tpf else ""
            if _tbin and os.path.isdir(_tbin):
                tool_bins.append(_tbin)
        # 0b) aclocal/automake 显式 shim 到 conan perl（§一.23 的另一半）：
        #     ohpcd 的 automake/1.18 把 .aclocal-real/.automake-real 的 shebang 写死为
        #     `#!/data/service/hnp/bin/perl`（HNP perl 5.42.0 非 i-thread 构建），
        #     而 conanbuild 的 PERL5LIB 指向 conan perl 5.42.2 thread-multi 的 XS →
        #     HNP perl 加载即崩 `Perl_my_cxt_init: symbol not found`（两套 perl 的
        #     构建配置互不兼容，方向不可调和）。反过来 conan 的 autoconf 系 .real 脚本
        #     shebang 又是 conan perl（其 @INC 前缀也是坏的 `//lib/...`，脱离
        #     PERL5LIB 找不到 Cwd）。⇒ 唯一自洽解：把 automake 系两个入口用 shim 显式
        #     指到 conan perl，全链 perl 同一个解释器，PERL5LIB 原样保留。
        perl_pf = automake_pf = None
        for _tname, _tdep in self.dependencies.build.items():
            _tpf = getattr(_tdep, "package_folder", None)
            if _tdep.ref.name == "perl":
                perl_pf = _tpf
            elif _tdep.ref.name == "automake":
                automake_pf = _tpf
        shim_dir = os.path.join(self.build_folder, "_perlshim")
        os.makedirs(shim_dir, exist_ok=True)
        conan_perl = os.path.join(perl_pf or "", "bin", "perl")
        shimmed = []
        # shim 必须复刻 ohpcd 包装脚本的重定位参数（其 .real 脚本编译进的前缀是
        # `/`（AutotoolsToolchain 默认 --prefix=/ 家族），不带参数会去找
        # `//share/aclocal-1.18` 而失败——首轮 shim 实测即此）：
        #   aclocal  → --automake-acdir=<pkg>/share/aclocal-1.18 --system-acdir=<pkg>/share/aclocal
        #   automake → --libdir=<pkg>/share/automake-1.18
        _ambin = os.path.join(automake_pf or "", "bin")
        _shim_args = {
            "aclocal": [f'--automake-acdir={automake_pf}/share/aclocal-1.18',
                        f'--system-acdir={automake_pf}/share/aclocal'],
            "automake": [f'--libdir={automake_pf}/share/automake-1.18'],
        }
        for _t, _args in _shim_args.items():
            _real = os.path.join(_ambin, f".{_t}-real")
            if os.path.isfile(_real):
                _sh = os.path.join(shim_dir, _t)
                _argstr = " ".join(f'"{a}"' for a in _args)
                with open(_sh, "w", encoding="utf-8") as _f:
                    _f.write(f'#!/bin/sh\nexec "{conan_perl}" "{_real}" {_argstr} "$@"\n')
                os.chmod(_sh, 0o755)
                if not os.access(_sh, os.X_OK):
                    raise ConanException(f"shim 执行位设置失败（HMDFS exec 位边界）: {_sh}")
                shimmed.append(_sh)
        tool_bins = [shim_dir] + tool_bins
        self.output.info(f"[shim] {len(shimmed)} perl shims -> {conan_perl}: "
                         f"{', '.join(os.path.basename(s) for s in shimmed)}")
        # 1) krby-config：conan 的 AutotoolsToolchain 默认 --prefix=/ → krb5 包装的
        #    krby-config 输出 `-I//include`、`-L//lib`（实测），真实 -I/-L 由
        #    AutotoolsDeps 的 CPPFLAGS/LDFLAGS 提供；这里只把 krb5 bin 放进 PATH，
        #    供 configure 的 AC_PATH_PROG(KRB5_CONFIG, krb5-config, failed) 找到它。
        krb5_pf = self.dependencies["krb5"].package_folder
        krb5_bin = os.path.join(krb5_pf, "bin")
        os.environ["PATH"] = os.pathsep.join(tool_bins + [krb5_bin]) + \
            os.pathsep + os.environ.get("PATH", "")
        self.output.info(f"[env] PATH tools-first ({len(tool_bins)} tool bins): "
                         f"{'; '.join(tool_bins)}")
        # 2) LD_LIBRARY_PATH：依赖共享库（krb5 系/openssl 若共享）供 make check 与
        #    test_package 运行期解析模块 DT_NEEDED。
        ld_dirs = []
        for _name, _dep in self.dependencies.host.items():
            _pf = getattr(_dep, "package_folder", None)
            if _pf and os.path.isdir(os.path.join(_pf, "lib")):
                ld_dirs.append(os.path.join(_pf, "lib"))
        _old_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(ld_dirs + ([_old_ld] if _old_ld else []))
        # 3) KRB5_CONFIG 双保险（AC_PATH_PROG 若尊重预置值则直接用绝对路径）
        os.environ["KRB5_CONFIG"] = os.path.join(krb5_bin, "krb5-config")
        # 4) OPENSSL_MODULES：ohpcd 的 openssl/3.0.21 是静态包（libcrypto.a），
        #    MD4 走 legacy provider。上游 crypto.c 的 init_ossl3_ctx() 会显式
        #    OSSL_PROVIDER_load(libctx, "legacy")，但模块文件查找路径默认用编译前缀
        #    （AutotoolsToolchain 默认 --prefix=/ 家族 → //ossl-modules，不存在）→
        #    EVP_MD_fetch("MD4") 返回 NULL → NTOWF/NTHash 全链 ERR_CRYPTO
        #    （本地实测 16 个 Test 块失败，含全部 GSSAPI 会话）。指向包内
        #    lib/ossl-modules 即通（ppp/2.5.2 先例）；消费期同款注入在 package_info()。
        _ssl_pf = None
        for _n, _d in self.dependencies.host.items():
            if _d.ref.name == "openssl":
                _ssl_pf = _d.package_folder
        _ssl_modules = os.path.join(_ssl_pf or "", "lib", "ossl-modules")
        if not os.path.isdir(_ssl_modules):
            raise ConanException(f"openssl provider 模块目录缺失: {_ssl_modules}")
        os.environ["OPENSSL_MODULES"] = _ssl_modules
        self.output.info(f"[env] PATH += {krb5_bin}")
        self.output.info(f"[env] KRB5_CONFIG = {os.environ['KRB5_CONFIG']}")
        self.output.info(f"[env] LD_LIBRARY_PATH += ({len(ld_dirs)} dirs)")
        self.output.info(f"[env] OPENSSL_MODULES = {_ssl_modules}")

        # ── autoreconf 自举（上游 tag 归档不带 configure）────────────────────
        # 内联 PATH 前缀：conanbuild 环境脚本会把 profile 的 /data/service/hnp/bin
        # 重新压到最前（os.environ 改写会被它覆盖，首轮实测仍命中 HNP autoreconf
        # → Perl_my_cxt_init 崩），所以必须在命令行层把 conan 的
        # autoreconf/aclocal/libtoolize/perl 顶到 PATH 首位，与 PERL5LIB 同族同版本。
        # rc 必须显式判：autoreconf 失败不许带病进 configure。
        _tool_path = os.pathsep.join(tool_bins + [krb5_bin])
        _sh_ac = os.path.join(shim_dir, "aclocal")
        _sh_am = os.path.join(shim_dir, "automake")
        rc = self.run(f'ACLOCAL="{_sh_ac}" AUTOMAKE="{_sh_am}" '
                      f'PATH="{_tool_path}:{os.environ.get("PATH", "")}" autoreconf -f -i',
                      cwd=self.source_folder, env="conanbuild", ignore_errors=True)
        if rc != 0:
            raise ConanException(f"autoreconf -f -i 失败 rc={rc}（tool_requires 三件套缺失或宏缺失）")
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException("autoreconf 后 configure 未生成（假绿防护）")
        self.output.info("[autoreconf] configure 已生成")

        autotools = Autotools(self)
        autotools.configure()
        # rc=0 假绿防护（止损先例 #9）：configure 成功必须核 Makefile 实物
        if not os.path.exists(os.path.join(self.build_folder, "Makefile")):
            raise ConanException(
                f"configure rc=0 但 {self.build_folder}/Makefile 未生成（config.status 假绿族）")
        self.output.info(f"[configure] Makefile 已生成: {self.build_folder}/Makefile")

        # ── make + make check（上游测试硬门禁）────────────────────────────────
        # LIBS 命令行覆盖（止损先例形态，零源码补丁）：
        #   configure.ac:69 `LIBS="$PTHREAD_CFLAGS $CFLAGS"` 是上游笔误（68 行刚把
        #   AutotoolsDeps 的 -l 集合收进 LIBS，69 行随即整体覆写），环境/命令行传入的
        #   LIBS 都会被吃掉；而 Makefile.am 只把 $(UNISTRING_LIBS) 给 ntlmssptest，
        #   模块 gssntlmssp.la 的链接行（$(GN_MECHGLUE_LIBS) 位于 objects 之前）拿不到
        #   静态库 → ohpcd libunistring 仅静态二进制（shared: False）、openssl 亦静态，
        #   模块会留下 u8_conv_to_encoding/SSL_* 未解析 → **dlopen 必炸**。
        #   make 命令行变量优先级最高：LIBS 出现在链接行 objects 之后，静态库可被抽取，
        #   共享库重复列出无副作用。
        unistring_pf = self.dependencies["libunistring"].package_folder
        link_libs = " ".join([
            "-pthread",
            "-lunistring",
            "-lssl", "-lcrypto",
            "-lgssapi_krb5", "-lkrb5", "-lk5crypto", "-lcom_err",
            "-lz",
        ])
        self.output.info(f"[link] LIBS override = {link_libs}（-L 由 LDFLAGS 提供）")
        autotools.make(args=["-j2", f'"LIBS={link_libs}"'])
        # 上游测试：automake TESTS = ntlmssptest + tests/env1.sh + tests/env2.sh
        autotools.make(args=["-j2", "check", f'"LIBS={link_libs}"'])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # libtool .la 带 prefix=/ 家族的绝对残链（//lib），不入包
        for _root, _dirs, _files in os.walk(self.package_folder):
            for _f in _files:
                if _f.endswith(".la"):
                    os.remove(os.path.join(_root, _f))
                    self.output.info(f"[pkg] removed {os.path.join(_root, _f)}")

        # install 假绿防护（止损先例 #9）：rc=0 必须核安装树实物
        mod = os.path.join(self.package_folder, "lib", "gssntlmssp", "gssntlmssp.so")
        hdr = os.path.join(self.package_folder, "include", "gssapi", "gssapi_ntlmssp.h")
        missing = [p for p in (mod, hdr) if not os.path.exists(p)]
        if missing:
            raise ConanException(f"install 产物缺失（make install 假绿）: {missing}")
        self.output.info(f"[install] module = {mod} ({os.path.getsize(mod)} bytes)")
        self.output.info(f"[install] header = {hdr} ({os.path.getsize(hdr)} bytes)")

    def package_info(self):
        # 消费期 OPENSSL_MODULES（runenv → conanrun）：模块内静态链接的 libcrypto
        # 在任何消费进程里取 MD4(legacy) 都需要该路径（ppp/2.5.2 先例形态）。
        # 守卫：openssl 是静态包，纯运行期图（如只看共享产物的场景）可能把它判为
        # skipped → package_folder=None（test_package 图首轮实测），此时不能硬崩，
        # 由 test_package/消费者自行注入（本包 notes.md 已知限制同样记录）。
        # 系统级集成（非 conan 消费者）须自行设置 OPENSSL_MODULES 或在 openssl.cnf
        # 激活 legacy——已写入 notes.md 已知限制。
        _ssl_pf = getattr(self.dependencies["openssl"], "package_folder", None)
        if _ssl_pf:
            self.runenv_info.define_path(
                "OPENSSL_MODULES", os.path.join(_ssl_pf, "lib", "ossl-modules"),
            )
        else:
            self.output.warning(
                "openssl package_folder 不可用（静态依赖被运行期图跳过）："
                "未注入 OPENSSL_MODULES，消费进程须自行设置")
        # 产物形态：lib/gssntlmssp/gssntlmssp.so（libtool `-module -avoid-version`，
        # SONAME=gssntlmssp.so，文件名无 lib 前缀）+ include/gssapi/gssapi_ntlmssp.h。
        # **libs 必须为空**（W4 轮1 P1）：模块是 dlopen 交付物、不具备可链接库语义——
        # 实测 `-L<libdir> -lgssntlmssp` → ld.lld `unable to find library`，
        # CMakeDeps find_library 会 FATAL_ERROR；写进 cpp_info.libs 即交付面声明与
        # 实物语义不符（知识库 DRAFT-E623 forbid_1 同形禁令）。消费者按 libdirs/
        # package_folder 定位后 dlopen（test_package 端到端 20/20 实测）。
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/gssntlmssp"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
