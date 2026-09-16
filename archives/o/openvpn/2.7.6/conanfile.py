#!/usr/bin/env python3
"""Conan recipe for openvpn 2.7.6 - the open-source VPN client/server.

openvpn is the reference open-source SSL/TLS VPN daemon (client + server,
tun/tap based).  This package ships the `openvpn` CLI binary plus the
down-root plugin (auth-pam plugin disabled: OHOS has no PAM).

Build system: Autotools; the release tarball ships a pre-generated
`configure` (no autoreconf needed).

Runtime dependencies (all published on ohpcd, all linked statically into
the final binary):
  - openssl/3.5.6   (TLS/crypto backend, hard requirement)
  - lzo/2.10        (legacy LZO compression)
  - lz4/1.10.0      (LZ4 compression)
  - libcap-ng/0.8.5 (Linux privilege dropping, hard requirement of
                     configure.ac on *-*-linux* hosts)

OHOS adaptations (all done in build() via replace_in_file - no source
patches needed, see notes.md):
  1. config.sub (2022-01-09) does not know the `ohos` OS:
     - add `ohos-linux)` case mapping to `linux-ohos`
     - add `ohos*` to the accepted OS list
     - add `linux-ohos*` to the kernel-os validation list
  2. config.guess cannot identify HarmonyOS:
     - accept `HarmonyOS` as UNAME_SYSTEM (same LIBC probing as Linux)
     - add `aarch64:HarmonyOS:*:*` case emitting aarch64-unknown-linux-ohos
  3. E114 (HMDFS umask trap): the tarball's `configure` creates its temp
     dir via `umask 077 && mktemp/mkdir`; on HMDFS this yields an
     unwritable drwx--S--- dir that breaks config.status.  The two umask
     077 prefixes are dropped (same fix as codecrypt/openfortivpn).

Configure options:
  - --build/--host=aarch64-unknown-linux-gnu/...-ohos (explicit triplet,
    config.guess would fail on HarmonyOS)
  - --disable-plugin-auth-pam (no PAM on OHOS)
  - --disable-dco (ovpn-dco kernel module does not exist on OHOS and DCO
    would additionally require libnl-genl-3.0 >= 3.4.0)
  - pkcs11 stays disabled (upstream default=no; pkcs11-helper not
    published on ohpcd)

R32: settings.os checked with `in ("Linux", "OHOS")`.
R33: no hardcoded shell env vars - paths come from Conan dependencies.
R34: test_package runs the actual openvpn binary (version + cipher
     self-test round trip).
R38: CLI tool - commands.json declared at software level.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class OpenvpnConan(ConanFile):
    name = "openvpn"
    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    version = "2.7.6"
    description = ("Open-source SSL/TLS VPN client and server "
                   "(tun/tap based, OpenSSL crypto backend)")
    license = "GPL-2.0-or-later"
    homepage = "https://openvpn.net/"
    url = "https://github.com/OpenVPN/openvpn"

    # CLI application (openvpn daemon + down-root plugin), R38
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "openvpn only supports Linux/OHOS, got "
                + str(self.settings.os))

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("lzo/2.10")
        self.requires("lz4/1.10.0")
        self.requires("libcap-ng/0.8.5")

    def build_requirements(self):
        # Upstream unit tests (tests/unit_tests, 17 cmocka testdrivers) are
        # gated on `pkg-config --exists cmocka` in configure.  cmocka/2.0.2
        # is published on ohpcd for OHOS armv8/clang15 - use it so the
        # unit tests get built and executed for real instead of being
        # disabled.  It is a test-only dependency, hence tool_requires.
        self.tool_requires("cmocka/2.0.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # pkg-config 接线：openvpn configure 用 pkg-config 探测全部依赖
        # （libcap-ng/lzo/lz4/libnl/openssl/cmocka）——不喂 pc 路径则探测全挂
        # （libcap-ng "package not found" 实证）。生成 + 聚合注入。
        # cmocka 是 tool_requires（build context）——build_context_activated
        # 让 PkgConfigDeps 也为其生成 .pc，注入后 configure 的
        # `pkg-config --exists cmocka` 即可通过，单元测试被启用。
        from conan.tools.gnu import PkgConfigDeps
        from conan.tools.env import Environment
        pkg = PkgConfigDeps(self)
        pkg.build_context_activated = ["cmocka"]
        pkg.generate()
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # Explicit triplet: config.guess cannot identify HarmonyOS and
            # config.sub (2022-01-09) lacks the ohos OS (patched in build()).
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
                # No PAM on OHOS -> skip the auth-pam plugin
                "--disable-plugin-auth-pam",
                # No ovpn-dco kernel module on OHOS; would also pull
                # libnl-genl-3.0 >= 3.4.0 which is not needed here
                "--disable-dco",
            ])
        # 依赖包的 pc 目录也注入（conan 包自带 .pc 的路径；含 build
        # context 的 cmocka——tool 依赖不在 self.dependencies.host 里，
        # 但 conan 自带 .pc 已由 PkgConfigDeps 生成到 generators 目录）
        pcdirs = []
        for _, dep in self.dependencies.items():
            for d in dep.cpp_info.libdirs + dep.cpp_info.builddirs:
                if os.path.isdir(d):
                    pcdirs.append(d)
        # cmocka（build context）的包内原生 .pc 目录
        for _, dep in self.dependencies.build.items():
            for d in dep.cpp_info.libdirs + dep.cpp_info.builddirs:
                if os.path.isdir(d):
                    pcdirs.append(d)
        if pcdirs:
            env = Environment()
            env.prepend("PKG_CONFIG_PATH", ":".join(dict.fromkeys(pcdirs)))
            env.vars(self, scope="build").save_script("conanbuild_pkgconfig")
        tc.generate()

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)
        self._patch_config_for_ohos()
        self._fix_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        # E074: single job - parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])
        # Upstream test suite (R1):
        #  - system tests (tests/): `make check` runs t_lpback.sh +
        #    t_cltsrv.sh for real (t_client/t_server_null/t_net self-skip
        #    with exit 77: they need root + a real VPN server + tun).
        #  - unit tests (tests/unit_tests/openvpn): 17 cmocka testdrivers.
        #    Upstream configure enables them now that cmocka/2.0.2 is in
        #    build_requires, but `TESTS` execution is gated on
        #    `!CROSS_COMPILING` (configure has --host set).  The built
        #    binaries are native OHOS arm64 and DO run on this host, so
        #    after `make check` (which builds all check_PROGRAMS) each
        #    testdriver is executed individually below; failures fail the
        #    package build.
        autotools.make(args=["check", "-j1"])
        self._run_unit_tests()

    def _run_unit_tests(self):
        """Execute each upstream cmocka unit testdriver individually.

        `make check` only builds check_PROGRAMS for cross builds (TESTS is
        `if !CROSS_COMPILING`-gated in tests/unit_tests/openvpn/Makefile.am),
        so we run every testdriver one by one and record real results.
        Any non-zero rc fails the package build.

        Environment details (OHOS):
        - test_common.h:92 requires $srcdir (tests read data files relative
          to the source dir, e.g. COPYRIGHT.GPL in test_misc.c test_list,
          input/*.txt in test_user_pass.c) -> srcdir is set.
        - test_ssl.c get_tmp_dir() and test_tls_crypt.c tls_options.tmp_dir
          hardcode "/tmp"; OHOS mounts /tmp read-only (erofs, E002) and we
          have no root to bind-mount.  Instead of patching upstream test
          sources we compile a tiny LD_PRELOAD shim (open/fopen/stat/unlink
          -> $OVPN_REDIR_TMP) purely as a test harness, so the upstream
          tests run unmodified.  Without the shim ssl_testdriver fails in
          GROUP SETUP ("Could not create temporary file '/tmp/openvpn_cert_*.tmp'")
          and tls_crypt_testdriver fails 1/18 (tls_crypt_v2_unwrap_checks).
        """
        import subprocess
        from conan.tools.env import VirtualBuildEnv
        unit_dir = os.path.join(self.build_folder, "tests",
                                "unit_tests", "openvpn")
        src_unit_dir = os.path.join(self.source_folder, "tests",
                                    "unit_tests", "openvpn")
        testdrivers = [
            "argv_testdriver", "auth_token_testdriver",
            "buffer_testdriver", "crypto_testdriver",
            "dhcp_testdriver", "ncp_testdriver",
            "mbuf_testdriver", "misc_testdriver",
            "options_parse_testdriver", "packet_id_testdriver",
            "pkt_testdriver", "provider_testdriver",
            "push_update_msg_testdriver", "socket_testdriver",
            "ssl_testdriver", "user_pass_testdriver",
            "tls_crypt_testdriver",
        ]
        env = VirtualBuildEnv(self).environment()
        envvars = dict(env.vars(self, scope="build"))
        envvars["srcdir"] = src_unit_dir
        shim = self._build_tmp_redir_shim()
        redir_dir = os.path.join(self.build_folder, "tmp-redir")
        os.makedirs(redir_dir, exist_ok=True)
        if shim:
            envvars["LD_PRELOAD"] = shim
            envvars["OVPN_REDIR_TMP"] = redir_dir
        results = []
        for td in testdrivers:
            exe = os.path.join(unit_dir, td)
            if not os.path.isfile(exe):
                results.append((td, "NOT-BUILT", -1))
                continue
            try:
                r = subprocess.run([exe], cwd=unit_dir, env=envvars,
                                   capture_output=True, timeout=300)
                rc = r.returncode
                results.append((td, "PASS" if rc == 0 else "FAIL", rc))
            except subprocess.TimeoutExpired:
                results.append((td, "TIMEOUT", -2))
        summary = "; ".join(f"{n}:{s}(rc={rc})" for n, s, rc in results)
        self.output.info(f"openvpn unit tests: {summary}")
        failed = [n for n, s, _ in results if s != "PASS"]
        if failed:
            raise ConanException(
                "openvpn upstream unit tests failed: " + ", ".join(failed))

    _TMP_REDIR_SHIM = r"""
#define _GNU_SOURCE
#include <dlfcn.h>
#include <string.h>
#include <stdlib.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <sys/stat.h>
#include <unistd.h>

/* Test-harness shim for OHOS: /tmp is a read-only erofs mount; redirect
 * absolute /tmp/... paths to $OVPN_REDIR_TMP (writable).  Upstream test
 * sources stay unmodified. */
static const char *redir(const char *path)
{
    static __thread char buf[4096];
    const char *newroot;
    if (!path) return path;
    if (strncmp(path, "/tmp/", 5) != 0) return path;
    newroot = getenv("OVPN_REDIR_TMP");
    if (!newroot) return path;
    snprintf(buf, sizeof(buf), "%s/%s", newroot, path + 5);
    return buf;
}

int open(const char *path, int flags, ...)
{
    static int (*real_open)(const char *, int, ...);
    mode_t mode = 0;
    va_list ap;
    if (flags & (O_CREAT | O_TMPFILE)) {
        va_start(ap, flags);
        mode = va_arg(ap, mode_t);
        va_end(ap);
    }
    if (!real_open) real_open = dlsym(RTLD_NEXT, "open");
    return real_open(redir(path), flags, mode);
}

FILE *fopen(const char *path, const char *mode)
{
    static FILE *(*real_fopen)(const char *, const char *);
    if (!real_fopen) real_fopen = dlsym(RTLD_NEXT, "fopen");
    return real_fopen(redir(path), mode);
}

int stat(const char *path, struct stat *st)
{
    static int (*real_stat)(const char *, struct stat *);
    if (!real_stat) real_stat = dlsym(RTLD_NEXT, "stat");
    return real_stat(redir(path), st);
}

int unlink(const char *path)
{
    static int (*real_unlink)(const char *);
    if (!real_unlink) real_unlink = dlsym(RTLD_NEXT, "unlink");
    return real_unlink(redir(path));
}
"""

    def _build_tmp_redir_shim(self):
        """Compile the /tmp redirection LD_PRELOAD shim (host-runnable
        OHOS arm64 shared object) with the same CC the package was built
        with.  Returns path or None on failure (unit tests will then run
        unshimmed and report the genuine /tmp failures).

        CC resolution order (the CI worker has no clang on PATH and
        VirtualBuildEnv alone does not always carry CC):
        1. AutotoolsToolchain conf tools.build:compiler_executables["c"]
        2. the generated conanautotoolstoolchain.sh (sourced value of CC)
        3. $CC from the build environment
        4. well-known HNP SDK locations / plain "clang"
        The resolved CC may be a full command line, so shlex-split it and
        drop any -c/-o/*.c args before appending our own."""
        import shlex
        import subprocess
        from conan.tools.env import VirtualBuildEnv
        if self.settings.os != "OHOS":
            return None

        candidates = []
        # 1. toolchain conf
        try:
            ce = self.conf.get("tools.build:compiler_executables",
                               check_type=dict)
            c_exe = ce.get("c")
            if c_exe:
                candidates.append(c_exe)
        except Exception:
            pass
        # 2. generated autotools toolchain env script
        tc_script = os.path.join(self.generators_folder,
                                 "conanautotoolstoolchain.sh")
        if os.path.isfile(tc_script):
            try:
                with open(tc_script) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("export CC="):
                            candidates.append(
                                line.split("=", 1)[1].strip().strip('"\''))
                            break
            except Exception:
                pass
        # 3. build env CC
        env = VirtualBuildEnv(self).environment()
        envvars = env.vars(self, scope="build")
        cc_env = envvars.get("CC")
        if cc_env:
            candidates.append(cc_env)
        # 4. well-known locations + plain name
        candidates += [
            "/data/service/hnp/bin/clang", "clang-15", "clang",
        ]

        src = os.path.join(self.build_folder, "tmp_redir_shim.c")
        out = os.path.join(self.build_folder, "tmp_redir_shim.so")
        with open(src, "w") as f:
            f.write(self._TMP_REDIR_SHIM)
        # clang writes intermediate temp files to $TMPDIR (falls back to
        # /tmp which is read-only on OHOS) - point it at the build dir.
        shim_env = dict(envvars)
        shim_env["TMPDIR"] = self.build_folder
        last_err = ""
        for cc in candidates:
            if not cc:
                continue
            try:
                cc_cmd = shlex.split(cc)
            except ValueError:
                continue
            # strip args that would clash with our -shared -fPIC -o ..:
            # drop -c, any "-o <arg>" pair, and stray *.c inputs
            cleaned = []
            skip_next = False
            for a in cc_cmd:
                if skip_next:
                    skip_next = False
                    continue
                if a == "-o":
                    skip_next = True
                    continue
                if a == "-c" or a.endswith(".c"):
                    continue
                cleaned.append(a)
            cmd = cleaned + ["-shared", "-fPIC", "-o", out, src, "-ldl"]
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=120,
                                   env=shim_env)
                if r.returncode == 0 and os.path.isfile(out):
                    return out
                last_err = r.stderr.decode(errors="replace")[:500]
            except FileNotFoundError as e:
                last_err = str(e)
                continue
            except Exception as e:
                last_err = str(e)
                continue
        self.output.warning(
            "tmp redir shim build failed, running unit tests without "
            f"shim (candidates tried: {candidates}): {last_err}")
        return None


    def _patch_config_for_ohos(self):
        """Teach config.sub/config.guess about OHOS (patch in-tree, no
        source patch needed - build-system files only)."""
        if self.settings.os != "OHOS":
            return
        src = self.source_folder

        # ---- config.sub: accept ohos ----
        cs = os.path.join(src, "config.sub")
        replace_in_file(
            self, cs,
            "\t\t\tandroid-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tbasic_os=linux-android\n"
            "\t\t\t\t;;\n",
            "\t\t\tandroid-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tbasic_os=linux-android\n"
            "\t\t\t\t;;\n"
            "\t\t\tohos-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tbasic_os=linux-ohos\n"
            "\t\t\t\t;;\n",
        )
        replace_in_file(
            self, cs,
            "\t     | fiwix* )",
            "\t     | fiwix* | ohos* )",
        )
        replace_in_file(
            self, cs,
            "\tlinux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \\\n"
            "\t\t   | linux-musl* | linux-relibc* | linux-uclibc* )",
            "\tlinux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \\\n"
            "\t\t   | linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* )",
        )

        # ---- config.guess: recognize HarmonyOS ----
        cg = os.path.join(src, "config.guess")
        replace_in_file(
            self, cg,
            "case $UNAME_SYSTEM in\nLinux|GNU|GNU/*)",
            "case $UNAME_SYSTEM in\nLinux|GNU|GNU/*|HarmonyOS)",
        )
        replace_in_file(
            self, cg,
            "    aarch64:Linux:*:*)\n"
            "\tGUESS=$UNAME_MACHINE-unknown-linux-$LIBC\n"
            "\t;;\n",
            "    aarch64:Linux:*:*)\n"
            "\tGUESS=$UNAME_MACHINE-unknown-linux-$LIBC\n"
            "\t;;\n"
            "    aarch64:HarmonyOS:*:*)\n"
            "\tGUESS=$UNAME_MACHINE-unknown-linux-ohos\n"
            "\t;;\n",
        )

    def _fix_configure_umask(self):
        """E114: drop `umask 077` from configure's temp-dir creation.

        HMDFS forces setgid on new dirs; combined with umask 077 the
        config.status temp dir becomes drwx--S--- (unwritable even by its
        owner) and config.status aborts.  Same fix as codecrypt/openfortivpn.
        """
        conf = os.path.join(self.source_folder, "configure")
        replace_in_file(
            self, conf,
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
        replace_in_file(
            self, conf,
            '(umask 077 && mkdir "$tmp")',
            'mkdir "$tmp"')

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Standalone application: binary + plugin, no linkable library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
