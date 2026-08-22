#!/usr/bin/env python3
"""Conan recipe — avahi-compat-libdns_sd 0.9_rc5 (Autotools, Bonjour-compatible libdns_sd).

Builds the avahi compat layer libdns_sd (dns_sd.h / DNSService* / TXTRecord*
API compatible with Apple's Bonjour) plus the in-tree avahi-common and
avahi-client libraries it links against. Only the three required subdirectories
of the avahi source tree are built; the avahi daemon/core/utilities are not.

The GitHub tag tarball does NOT ship a generated configure script, so the
recipe bootstraps it with autogen.sh (autoreconf). autoconf/m4 are provided by
the SDK; automake (aclocal), libtool (libtoolize) and gettext (gettextize) come
from Conan tool_requires. avahi-client needs D-Bus, so dbus is a runtime
requirement and a dbus-1.pc pkg-config shim is generated from the package.
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class AvahiCompatLibdnsSdConan(ConanFile):
    name = "avahi-compat-libdns_sd"
    version = "0.9_rc5"
    description = "Bonjour-compatible DNS Service Discovery library (libdns_sd) on top of Avahi"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/avahi/avahi"
    url = "https://github.com/avahi/avahi"
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

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # avahi-client links against D-Bus; the compat layer talks to the
        # avahi daemon through avahi-client over D-Bus.
        self.requires("dbus/1.14.10")
        # dbus 传递 expat/2.8.2；预检 remote 顺序 conancenter 在前，同版本会解析到
        # conancenter 上游配方，其 tool_require cmake/4.4.2 在 OHOS 上构建失败
        # （cmake 配方 build() 按 OS 键取预编译包，OHOS 无键 → KeyError 'OHOS'）。
        # 强制到仓库独有已发布版本 2.8.2.1（conancenter 无同版本 → 自动落 ohpcd
        # 本仓适配配方，无 conan cmake tool_require），与 goffice/vips/exiv2 同款做法。
        self.requires("expat/2.8.2.1", override=True)

    def build_requirements(self):
        # The GitHub tag archive has no generated configure; autogen.sh needs
        # gettextize (gettext), libtoolize (libtool), aclocal/automake.
        # autoconf and m4 are provided by the SDK (/data/service/hnp/bin).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("gettext/0.22.5.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        # configure.ac runs PKG_CHECK_MODULES(DBUS, [dbus-1 >= 0.34]); the
        # dbus Conan package does not install a dbus-1.pc itself, so generate
        # a pkg-config shim pointing at the package folders.
        dbus = self.dependencies["dbus"]
        pc_dir = os.path.join(self.build_folder, "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        pc = os.path.join(pc_dir, "dbus-1.pc")
        with open(pc, "w", encoding="utf-8") as handle:
            handle.write(f"prefix={dbus.package_folder}\n")
            handle.write("exec_prefix=${prefix}\n")
            handle.write("libdir=${prefix}/lib\n")
            handle.write("includedir=${prefix}/include\n")
            handle.write("Name: dbus\n")
            handle.write("Description: D-Bus message bus\n")
            handle.write("Version: 1.14.10\n")
            handle.write("Libs: -L${libdir} -ldbus-1\n")
            handle.write("Cflags: -I${includedir}/dbus-1.0 -I${includedir}\n")
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", pc_dir)
        # gettextize 0.22.5 把 gettext_datadir（及 gettext m4 宏目录）硬编码为
        # gettext 制品构建机的绝对路径（@datadir@ 在 gettext 构建期展开），而
        # Conan 制品可重定位：预检机 conan-home 与构建机不同 → baked 路径不存在，
        # gettextize 报 "gettext source directory '...' doesn't exist" 并以
        # "*** Stop." 中止（R19 真机预检失败；已用 gettext-0.22.5 的 gettextize.in
        # 本机模拟精确复现）。gettextize 支持 $gettext_datadir 环境覆盖
        # （脚本首部 `: ${gettext_datadir=...}`），aclocal 支持 $ACLOCAL_PATH：
        # 指向真实工具包目录即可，无需修改上游 autogen.sh。
        gettext_pkg = self.dependencies.build["gettext"].package_folder
        gettext_datadir = os.path.join(gettext_pkg, "share", "gettext")
        if os.path.isdir(gettext_datadir):
            env.define("gettext_datadir", gettext_datadir)
        else:
            self.output.warning(
                f"gettext package lacks share/gettext: {gettext_datadir}")
        gettext_aclocal = os.path.join(gettext_pkg, "share", "aclocal")
        if os.path.isdir(gettext_aclocal):
            env.prepend_path("ACLOCAL_PATH", gettext_aclocal)
        else:
            self.output.warning(
                f"gettext package lacks share/aclocal: {gettext_aclocal}")
        env.vars(self).save_script("avahi_env")

    def _configure_args(self):
        args = [
            f"--prefix={self.package_folder}",
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--with-distro=none",
            # --with-xml=none：本配方只构建 avahi-common/avahi-client/
            # avahi-compat-libdns_sd，XML(expat/bsdxml) 仅被 avahi-daemon 使用；
            # 真机日志 configure 报 "*** neither libexpat not libbsdxml could
            # be found ***"（AC_CHECK_LIB 链接探测失败，expat 包头/库未进
            # CPPFLAGS/LDFLAGS）。上游 configure.ac 显式支持 none（直接跳过
            # 错误分支），三个子目录 Makefile.am 均无 XML_CFLAGS/HAVE_XML 引用，
            # 关闭后不构建 daemon，无功能损失。
            "--with-xml=none",
            "--enable-compat-libdns_sd",
            "--enable-tests",
            # --disable-nls：avahi-common/i18n.c 在 ENABLE_NLS 下调用
            # bindtextdomain/bind_textdomain_codeset，链接为 g_libintl_* 符号
            # （libintl 库），OHOS/bionic 无 libintl，静态库消费方（test_package
            # test_dns_sd）最终链接报 undefined symbol: g_libintl_bindtextdomain。
            # i18n.h 在 ENABLE_NLS 未定义时将这些调用宏化为空操作，本 compat 层
            # 不依赖本地化（OpenWrt 构建 avahi 同款 --disable-nls），从源头消除
            # libintl 链接依赖；autogen 仍需要 gettextize 提供 AM_GNU_GETTEXT 宏。
            "--disable-nls",
            # Disable every optional component: only avahi-common,
            # avahi-client and avahi-compat-libdns_sd are needed.
            "--disable-glib",
            "--disable-gobject",
            "--disable-libevent",
            "--disable-qt3",
            "--disable-qt4",
            "--disable-qt5",
            "--disable-gtk",
            "--disable-gtk3",
            "--disable-python",
            "--disable-mono",
            "--disable-manpages",
            "--disable-xmltoman",
            "--disable-gdbm",
            "--disable-libdaemon",
            # libsystemd 检查默认开启（configure.ac:825 HAVE_LIBSYSTEMD=yes），
            # 会强制 PKG_CHECK_MODULES(LIBSYSTEMD, [libsystemd])；真机日志报
            # "No package 'libsystemd' found"（OHOS 无 systemd）。libsystemd
            # 仅用于 avahi-daemon 的 systemd 集成，本配方不构建 daemon，显式
            # 关闭；同时关掉 systemdsystemunitdir 的 pkg-config 探测。
            "--disable-libsystemd",
            "--with-systemdsystemunitdir=no",
        ]
        if not self.options.shared:
            args.extend(["--disable-shared", "--enable-static"])
        else:
            args.extend(["--enable-shared", "--disable-static"])
        return args

    def _patch_generated_configure(self, configure):
        """HMFS workaround (E011/E112/E118): strip ``umask 077`` from the
        AS_TMPDIR temp-dir creation in the *generated* configure.

        config.status aborts with ``can't create ./confXXXXXX/subs1.awk:
        Permission denied`` because ``(umask 077 && mktemp -d ...)``
        creates a drwx--S--- (2700 + setgid) directory that HMFS refuses
        to write into even for its creator.  Removing ``umask 077``
        (aaphoto/abiword/acl proven) lets mktemp use the default umask so
        the temp dir is writable.  avahi ships no configure (autogen.sh
        generates it), so the patch is applied in build() right after
        autogen, before configure runs.  config.status is written from a
        heredoc embedded in configure, so patching configure covers both
        scripts; the ``umask 077 && mktemp -d`` / ``umask 077 && mkdir``
        substrings contain no ``$``/backticks and match in both the live
        code and the heredoc template (also the ``\``$-escaped copy).
        """
        with open(configure, "r", encoding="utf-8") as handle:
            text = handle.read()
        # autoconf 的 AS_TMPDIR 里 mktemp 行拼写是 `umask 077`，而 mkdir
        # fallback 行是 autoconf 自带的拼写错误 `umash 077`（aaphoto/abiword
        # 补丁均为 `umash 077 && mkdir`），两种拼写都要覆盖。
        patched, n_mktemp = re.subn(
            r"um(?:ask|ash) 077 && mktemp -d", "mktemp -d", text)
        patched, n_mkdir = re.subn(
            r"um(?:ask|ash) 077 && mkdir", "mkdir", patched)
        if n_mktemp == 0 and n_mkdir == 0:
            self.output.warning(
                "generated configure has no AS_TMPDIR 'umask 077' pattern; "
                "HMFS workaround not applied")
            return
        with open(configure, "w", encoding="utf-8") as handle:
            handle.write(patched)
        self.output.info(
            "patched generated configure AS_TMPDIR: removed 'umask 077 && ' "
            f"(mktemp:{n_mktemp}, mkdir:{n_mkdir})")

    def build(self):
        apply_conandata_patches(self)
        env = ["conanbuild", "avahi_env"]
        src = self.source_folder
        # HMFS 工作目录下 HNP bash 启动即 getcwd 失败（[shell_getcwd]：cannot
        # access parent directories: Not supported），平台诊断要求改用 HMBS 注入的
        # SHELL=/bin/sh（并同步 CONFIG_SHELL）解释脚本，禁止硬编码 bash。
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")
        # The tarball has no configure: generate it via autogen.sh.
        # NOCONFIGURE=1 prevents autogen.sh from running configure itself
        # (it would exec the script via shebang, which HarmonyOS refuses).
        self.run(
            f"NOCONFIGURE=1 CONFIG_SHELL={shell} SHELL={shell} {shell} autogen.sh",
            cwd=src, env=env)
        if not os.path.exists(os.path.join(src, "configure")):
            raise ConanException("autogen.sh did not produce configure")
        # HMFS 安全机制拒绝写入 mktemp -d 的 2700+setgid 临时目录，导致
        # config.status 报 "can't create ./confXXXXXX/subs1.awk: Permission
        # denied"（E011/E112/E118）。configure 由 autogen.sh 动态生成，无法打
        # 归档补丁；这里直接在运行前文本 patch 生成的 configure（aaphoto/
        # abiword/acl 同款方案，不依赖可执行位/env），覆盖 configure 本体与
        # 其内嵌的 config.status heredoc 模板。
        self._patch_generated_configure(os.path.join(src, "configure"))
        # Run configure explicitly via sh (bypass HarmonyOS script-exec limit).
        self.run(
            f"CONFIG_SHELL={shell} SHELL={shell} {shell} configure "
            + " ".join(self._configure_args()),
            cwd=src, env=env)
        # Build in dependency order: avahi-common -> avahi-client -> compat.
        self.run("make -C avahi-common -j1", cwd=src, env=env)
        self.run("make -C avahi-client -j1", cwd=src, env=env)
        self.run("make -C avahi-compat-libdns_sd -j1", cwd=src, env=env)

        # ── Upstream tests (make check in avahi-compat-libdns_sd) ──
        # TESTS = txt-test null-test; both are input/encoding tests that do
        # not require a running avahi daemon. Emit the HMBS_UPSTREAM_TEST_RESULT
        # marker from the actual harness output.
        log = os.path.join(self.build_folder, "make-check.log")
        failed_run = False
        try:
            self.run(
                f'{shell} -c "make -C avahi-compat-libdns_sd check > %s 2>&1; '
                'rc=$?; cat %s; exit $rc"' % (log, log),
                cwd=src,
                env=env,
            )
        except ConanException:
            failed_run = True
        with open(log, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        passed = len(re.findall(r"(?m)^PASS:", text))
        failed = len(re.findall(r"(?m)^FAIL:", text))
        skipped = len(re.findall(r"(?m)^SKIP:", text))
        discovered = passed + failed + skipped
        upstream = {
            "status": "passed" if (failed == 0 and failed_run is False) else "failed",
            "framework": "make check (automake TESTS)",
            "command": "make -C avahi-compat-libdns_sd check",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if failed_run or failed > 0:
            raise ConanException(
                f"upstream make check failed: {passed} passed, {failed} failed")

    def _write_install_shim(self):
        """HMBS 的 install shim（runtime/<task>/bin/install）只接受单文件
        两参调用；automake 批量头安装 `install -c -m 644 f1..fN dir/`
        直接 exit 64 (EX_USAGE)（E182/E188 同型先例：adms 2.3.7 /
        libgsf 1.14.58 / xeyes 1.3.1 已过门禁）。这里写一个 cp/mkdir shim
        替代：解析 -c/-m/-d 等选项，末参为目标（目录或文件），逐源
        cp 复制；HMFS 不支持 chmod（HMBS_CAP_CHMOD=0），chmod 步骤
        容错跳过。返回 shim 绝对路径供 Makefile INSTALL 重定向。
        """
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        # HMFS 在创建时按 open mode 给权限（chmod 能力为 0），用 os.open
        # 指定 0o755 直接生成可执行 shim（adms 2.3.7 / xeyes 同款）。
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                    "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    "for arg in \"$@\"; do dest=$arg; done\n"
                    "count=$(($# - 1))\n"
                    "if [ \"$count\" -gt 1 ]; then\n"
                    "  # 多源形态：末参是目标目录，先确保目录存在\n"
                    "  mkdir -p \"$dest\"\n"
                    "else\n"
                    "  mkdir -p \"$(dirname \"$dest\")\"\n"
                    "fi\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  # HMFS 不支持 chmod（HMBS_CAP_CHMOD=0），设权限失败不阻断复制\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then\n"
                    "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else\n"
                    "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
                    "    fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
                    "done\n"
                )
        except Exception:  # noqa: BLE001 - 写 shim 失败不静默，关闭 fd 后上抛
            os.close(fd)
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass  # HMFS 可能不支持 chmod（HMBS_CAP_CHMOD=0）
        return install

    def _redirect_install_to_shim(self, root, shim_install):
        # configure 已把探测到的 install 路径写死进各生成 Makefile 的
        # INSTALL 变量。把 `INSTALL = <.../install ...>` 替换为
        # `INSTALL = <shim>`，INSTALL_DATA/INSTALL_PROGRAM 默认
        # `${INSTALL} -m 644`/`${INSTALL}` 引用 ${INSTALL} 自动重算，
        # make install 全程走 shim（adms 2.3.7 / xeyes 1.3.1 同款）。
        for _root, _, _files in os.walk(root):
            if "Makefile" not in _files:
                continue
            _mp = os.path.join(_root, "Makefile")
            try:
                with open(_mp, "r", encoding="utf-8", errors="ignore") as _f:
                    _content = _f.read()
            except OSError:
                continue
            if "INSTALL =" not in _content:
                continue
            _lines = []
            _changed = False
            for _line in _content.splitlines(True):
                _stripped = _line.lstrip()
                if _stripped.startswith("INSTALL = ") and "/install" in _stripped:
                    _indent = _line[:len(_line) - len(_stripped)]
                    _lines.append(f"{_indent}INSTALL = {shim_install}\n")
                    _changed = True
                else:
                    _lines.append(_line)
            if _changed:
                with open(_mp, "w", encoding="utf-8") as _f:
                    _f.write("".join(_lines))

    def package(self):
        env = ["conanbuild", "avahi_env"]
        # HMBS 的 install shim 只接受单文件两参调用，automake 批量头安装
        # `install -c -m 644 f1..fN dir/` 报 exit 64 (EX_USAGE)
        # （avahi-common 14 个头文件、avahi-client 3 个头文件均命中）。
        # 写 cp/mkdir shim 并重定向生成的 Makefile 的 INSTALL 变量，
        # INSTALL_DATA/INSTALL_PROGRAM 引用 ${INSTALL} 自动重算
        # （adms 2.3.7 / libgsf 1.14.58 / xeyes 1.3.1 已过门禁同款）。
        shim = self._write_install_shim()
        self._redirect_install_to_shim(self.source_folder, shim)
        for subdir in ("avahi-common", "avahi-client", "avahi-compat-libdns_sd"):
            self.run(f"make -C {subdir} install", cwd=self.source_folder, env=env)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # libdns_sd links avahi-client and avahi-common (static by default),
        # so all three libraries and their headers are shipped together.
        self.cpp_info.libs = ["dns_sd", "avahi-client", "avahi-common"]
        self.cpp_info.requires = ["dbus::dbus"]
        self.cpp_info.set_property("cmake_file_name", "avahi-compat-libdns_sd")
        self.cpp_info.set_property("cmake_target_name",
                                   "avahi-compat-libdns_sd::avahi-compat-libdns_sd")
