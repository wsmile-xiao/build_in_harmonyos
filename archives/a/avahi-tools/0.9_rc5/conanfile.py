#!/usr/bin/env python3
"""Conan recipe — avahi-tools 0.9_rc5 (Autotools, Avahi client command-line utilities).

Builds the four Avahi client utilities shipped in avahi-utils/ (avahi-browse,
avahi-resolve, avahi-publish, avahi-set-host-name) plus the in-tree
avahi-common and avahi-client libraries they link against. Only these three
subdirectories of the avahi source tree are built; the daemon, core, compat
layers and language/UI bindings are excluded.

The GitHub tag tarball does NOT ship a generated configure script, so the
recipe bootstraps it with autogen.sh. autoconf/m4 come from the platform SDK;
automake (aclocal), libtool (libtoolize) and gettext (gettextize) come from
Conan tool_requires and are wrapped in task-local launchers because HMFS
rejects direct shebang execution of cross-UID Conan cache scripts and the
packaged scripts carry non-relocatable data paths (knowledge E337).
avahi-client talks to avahi-daemon over D-Bus, so dbus is a requirement and a
dbus-1.pc pkg-config shim is generated from its package.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class AvahiToolsConan(ConanFile):
    name = "avahi-tools"
    version = "0.9_rc5"
    description = (
        "Avahi command-line client utilities: avahi-browse, avahi-resolve, "
        "avahi-publish, avahi-set-host-name")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/avahi/avahi"
    url = "https://github.com/avahi/avahi"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    # bin_PROGRAMS of avahi-utils/Makefile.am.
    _PROGRAMS = (
        "avahi-browse",
        "avahi-resolve",
        "avahi-publish",
        "avahi-set-host-name",
    )
    # Convenience aliases created by upstream install-exec-local.
    _ALIASES = {
        "avahi-browse": ("avahi-browse-domains",),
        "avahi-resolve": ("avahi-resolve-host-name", "avahi-resolve-address"),
        "avahi-publish": ("avahi-publish-address", "avahi-publish-service"),
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The utilities talk to avahi-daemon through libavahi-client over D-Bus.
        self.requires("dbus/1.14.10")
        # dbus 传递 expat/2.8.2；预检 remote 顺序 conancenter 在前，同版本会解析到
        # conancenter 上游配方，其依赖树 tool_require cmake/4.4.2 在 OHOS 上构建失败
        # （cmake 配方 build() 按 OS 键取预编译包，OHOS 无键 → KeyError 'OHOS'）。
        # 强制到仓库独有已发布版本 2.8.2.1（conancenter 无同版本 → 自动落 ohpcd
        # 本仓适配配方，无 conan cmake tool_require），与 avahi-compat-libdns_sd /
        # goffice / vips / exiv2 同款做法。
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
            handle.write(
                "Cflags: -I${includedir}/dbus-1.0 -I${includedir}\n")
        env = Environment()
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}) or {}
        for variable, key in (("CC", "c"), ("CXX", "cpp")):
            compiler = compilers.get(key)
            if not compiler:
                raise ConanException(
                    f"{variable} missing from tools.build:compiler_executables")
            env.define(variable, compiler)
        env.prepend_path("PKG_CONFIG_PATH", pc_dir)
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
            # --with-xml=none：XML(expat/bsdxml) 仅被 avahi-daemon 使用；不指定时
            # configure.ac 走 else 分支强制 AC_CHECK_LIB 探测 expat/bsdxml，
            # OHOS 上报 "*** neither libexpat not libbsdxml could be found ***"
            # （avahi-compat-libdns_sd R20 同源修复；上游显式支持 none 直接跳过）。
            "--with-xml=none",
            # 接入 avahi-common 的 automake TESTS（7 个离线单元测试）。
            "--enable-tests",
            # --disable-nls：avahi-common/i18n.c 在 ENABLE_NLS 下调用
            # bindtextdomain/bind_textdomain_codeset（libintl 符号），OHOS/bionic
            # 无 libintl，静态库消费方最终链接报 undefined symbol
            # g_libintl_bindtextdomain（avahi-compat-libdns_sd R25 同源修复）。
            # NLS 关闭时 i18n.h 把这些调用宏化为空操作；autogen 仍需要 gettextize
            # 提供 AM_GNU_GETTEXT 宏。
            "--disable-nls",
            "--disable-introspection",
            "--disable-glib",
            "--disable-gobject",
            # 本包只构建 avahi-common/avahi-client/avahi-utils，其余组件全部关闭。
            "--disable-compat-libdns_sd",
            "--disable-compat-howl",
            "--disable-libevent",
            "--disable-qt3",
            "--disable-qt4",
            "--disable-qt5",
            "--disable-gtk",
            "--disable-gtk3",
            "--disable-python",
            "--disable-mono",
            "--disable-autoipd",
            "--disable-doxygen-doc",
            "--disable-manpages",
            "--disable-xmltoman",
            # gdbm 仅用于 avahi-browse 的 --dump-db 服务类型数据库特性，
            # OHOS 无 gdbm，关闭后 stdb.c 不参与编译。
            "--disable-gdbm",
            "--disable-libdaemon",
            # libsystemd 检查默认开启（configure.ac HAVE_LIBSYSTEMD=yes），会强制
            # PKG_CHECK_MODULES(LIBSYSTEMD, [libsystemd])；OHOS 无 systemd，
            # 报 "No package 'libsystemd' found"。libsystemd 仅用于 daemon 的
            # systemd 集成，本包不构建 daemon，显式关闭；同时关掉
            # systemdsystemunitdir 的 pkg-config 默认探测
            # （avahi-compat-libdns_sd R21 同源修复）。
            "--disable-libsystemd",
            "--with-systemdsystemunitdir=no",
            # 应用包：内置依赖库始终静态链进工具二进制，无 shared/fPIC 选项。
            "--disable-shared",
            "--enable-static",
        ]
        return args

    def _patch_generated_configure(self, configure):
        """HMFS workaround (E011/E112/E118): strip ``umask 077`` from the
        AS_TMPDIR temp-dir creation in the *generated* configure.

        config.status aborts with ``can't create ./confXXXXXX/subs1.awk:
        Permission denied`` because ``(umask 077 && mktemp -d ...)`` creates a
        drwx--S--- (2700 + setgid) directory that HMFS refuses to write into
        even for its creator. Removing ``umask 077`` (aaphoto/abiword/acl
        proven) lets mktemp use the default umask so the temp dir is writable.
        avahi ships no configure (autogen.sh generates it), so the patch is
        applied in build() right after autogen, before configure runs.
        config.status is written from a heredoc embedded in configure, so
        patching configure covers both scripts; the ``um(?:ask|ash) 077``
        alternation also covers autoconf's historic ``umash`` typo used by the
        mkdir fallback line.
        """
        with open(configure, "r", encoding="utf-8") as handle:
            text = handle.read()
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
            f"NOCONFIGURE=1 CONFIG_SHELL={shell} SHELL={shell} "
            f"{shell} autogen.sh",
            cwd=src, env=env)
        if not os.path.exists(os.path.join(src, "configure")):
            raise ConanException("autogen.sh did not produce configure")
        # HMFS 安全机制拒绝写入 mktemp -d 的 2700+setgid 临时目录，导致
        # config.status 报 "can't create ./confXXXXXX/subs1.awk: Permission
        # denied"（E011/E112/E118）。configure 由 autogen.sh 动态生成，无法打
        # 归档补丁；在运行前文本 patch 生成的 configure，覆盖 configure 本体与
        # 其内嵌的 config.status heredoc 模板（aaphoto/abiword/acl 同款方案）。
        self._patch_generated_configure(os.path.join(src, "configure"))
        # Run configure explicitly via sh (bypass HarmonyOS script-exec limit).
        self.run(
            f"CONFIG_SHELL={shell} SHELL={shell} {shell} configure "
            + " ".join(self._configure_args()),
            cwd=src, env=env)
        # Build in dependency order: avahi-common -> avahi-client -> avahi-utils.
        self.run("make -C avahi-common -j1", cwd=src, env=env)
        self.run("make -C avahi-client -j1", cwd=src, env=env)
        self.run("make -C avahi-utils -j1", cwd=src, env=env)

        # ── Upstream tests (make check in avahi-common) ──
        # TESTS = strlst-test domain-test alternative-test timeval-test
        # watch-test watch-test-thread utf8-test。全部为纯输入/编码类单元测试，
        # 不需要运行中的 avahi-daemon 或 D-Bus 总线，真机可直接执行。
        # avahi-utils/Makefile.am 未声明任何 TESTS；avahi-client 只在
        # ENABLE_TESTS 下构建 noinst 测试程序但未注册 TESTS（语义上需要活的
        # daemon/总线，见 test_package/MANIFEST.yml 的 upstream_test_audit）。
        log = os.path.join(self.build_folder, "make-check.log")
        failed_run = False
        try:
            self.run(
                f'{shell} -c "make -C avahi-common check > %s 2>&1; '
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
            "command": "make -C avahi-common check",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if failed_run or failed > 0 or discovered == 0:
            raise ConanException(
                f"upstream make check failed: {passed} passed, {failed} failed, "
                f"{skipped} skipped, {discovered} discovered")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as binary:
                return binary.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_program_binary(self, utils_dir, name):
        # libtool 把真实可执行文件放在 .libs/，顶层可能是 wrapper 脚本；
        # 用 ELF 魔数挑出真身，两种布局都兼容。
        candidates = (
            os.path.join(utils_dir, ".libs", name),
            os.path.join(utils_dir, name),
        )
        for candidate in candidates:
            if os.path.isfile(candidate) and self._is_elf(candidate):
                return candidate
        raise ConanException(
            f"built program {name} not found under {utils_dir} "
            "(looked in .libs/ and top level)")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        utils_dir = os.path.join(self.source_folder, "avahi-utils")
        # 应用包不跑 make install：HMBS install shim 对批量安装有限制且 HMFS
        # 符号链接能力不确定，直接按 ELF 魔数收集产物（abbtr/git-who 工具包先例）。
        for name in self._PROGRAMS:
            binary = self._find_program_binary(utils_dir, name)
            shutil.copy2(binary, os.path.join(bin_dir, name))
        # 复刻上游 install-exec-local 的便捷别名：先 rm -f（HMFS 不能 ln -sf
        # 覆盖已存在名字）；符号链接失败时退化为独立副本，功能等价。
        for target, aliases in self._ALIASES.items():
            target_path = os.path.join(bin_dir, target)
            for alias in aliases:
                alias_path = os.path.join(bin_dir, alias)
                if os.path.lexists(alias_path):
                    os.remove(alias_path)
                try:
                    os.symlink(target, alias_path)
                except OSError:
                    shutil.copy2(target_path, alias_path)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Application package: ships executables only, nothing to link against.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
