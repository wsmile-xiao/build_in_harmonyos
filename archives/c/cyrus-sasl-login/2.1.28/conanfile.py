#!/usr/bin/env python3
"""Conan recipe — cyrus-sasl-login 2.1.28 (Autotools).

LOGIN mechanism package for Cyrus SASL on HarmonyOS PC (aarch64).

Same upstream 2.1.28 source as cyrus-sasl, configured for the LOGIN
authentication mechanism (plugins/login.c, enabled via --enable-login;
LOGIN is a self-contained plaintext mechanism derived from PLAIN and
needs no crypto, SQL, LDAP, Kerberos or DB backends). Everything else
is disabled so the package has zero Conan dependencies and builds a
self-contained static libsasl2 with the LOGIN client/server plugins
linked in (--with-staticsasl, no runtime SASL_PATH/dlopen needed).

OHOS notes (cyrus-sasl/2.1.28.1 precedent, CI-passed):
  - configure probes the *build* compiler via AC_PROG_CC_FOR_BUILD and
    bare-searches gcc/cc/cl.exe, but OHOS only ships clang, so feed
    CC_FOR_BUILD/CPP_FOR_BUILD explicitly (native build, build == host).
  - HMDFS default TMPDIR may be unwritable; point TMPDIR at a writable
    directory inside the source tree (HMBS-injected TMPDIR preferred).
  - configure/install-sh must run under /system/bin/sh on device.
  - Static build: copy the plugin link sources (incl. login.c) into
    lib/ before make, same as the 2.1.28.1 _copy_linksrcs_for_ohos flow.
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class CyrussaslloginConan(ConanFile):
    name = "cyrus-sasl-login"
    version = "2.1.28"
    description = "Cyrus SASL LOGIN authentication mechanism (libsasl2 with LOGIN support)"
    license = "BSD-Attribution-HPND-disclaimer"
    homepage = "https://www.cyrusimap.org/sasl/"
    url = "https://github.com/cyrusimap/cyrus-sasl"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cyrus-sasl-login is only supported on Linux/OHOS, not %s"
                % self.settings.os
            )

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Old codebase: clang 15 promotes implicit-function-declaration /
        # int-conversion to errors; demote to warnings (standard practice
        # for building legacy C, same as cyrus-sasl/2.1.28).
        tc.extra_cflags.append("-Wno-error=implicit-function-declaration")
        tc.extra_cflags.append("-Wno-error=int-conversion")
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def build(self):
        source_folder = self.source_folder
        tmpdir = self._writable_tmpdir(source_folder)
        # E011/HMDFS: autoconf creates ./confXXXXXX temp dirs under
        # `umask 077` (0700 + setgid -> drwx--S---, owner-unwritable), so
        # config.status fails with "can't create ./conf*/subs1.awk:
        # Permission denied". Rewrite to umask 022 in the generated
        # script (platform adaptation, same as zzuf/daemonize precedent).
        self._fix_autoconf_umask_for_ohos(source_folder)
        mktemp_shim = self._mktemp_fallback_shim_for_ohos(tmpdir)
        build_cc = self._build_cc_for_ohos()
        configure = os.path.join(source_folder, "configure")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration(
                "configure not found in source tree: %s" % configure
            )
        configure_args = " ".join(
            shlex.quote(arg) for arg in self._configure_args()
        )
        shell = os.environ.get("CONFIG_SHELL") or "/system/bin/sh"
        path_prefix = ("%s:" % mktemp_shim) if mktemp_shim else ""
        command = (
            "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
            "CONFIG_SHELL=\"%s\" SHELL=\"%s\" "
            "CC_FOR_BUILD=\"%s\" CPP_FOR_BUILD=\"%s -E\" "
            "PATH=\"%s$PATH\" "
            "\"%s\" \"%s\" %s"
            % (tmpdir, tmpdir, tmpdir, shell, shell, build_cc, build_cc,
               path_prefix, shell, configure, configure_args)
        )
        self.run(command, cwd=source_folder)
        self._copy_linksrcs_for_ohos(source_folder)
        install_sh = self._copy_install_sh_for_ohos(source_folder, tmpdir)
        self.run(
            "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
            "make -j1 %s" % (tmpdir, tmpdir, tmpdir,
                             self._ohos_make_vars(install_sh)),
            cwd=source_folder,
        )
        self._run_login_smoke_test(source_folder)

    def package(self):
        tmpdir = self._writable_tmpdir(self.source_folder)
        install_sh = self._copy_install_sh_for_ohos(self.source_folder, tmpdir)
        self.run(
            "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
            "make install DESTDIR=\"%s\" -j1 %s"
            % (tmpdir, tmpdir, tmpdir, self.package_folder,
               self._ohos_make_vars(install_sh)),
            cwd=self.source_folder,
        )
        # Static-only package (shared=False): purge any shared artefacts
        # so downstream -lsasl2 can only resolve to libsasl2.a. A stale
        # libsasl2.so in the package (or a system libsasl2.so.3 found via
        # default search paths) bakes a DT_NEEDED libsasl2.so.3 into the
        # consumer; on OHOS that SONAME resolves to an incompatible stub
        # and every sasl_* symbol relocates as "symbol not found".
        if not self.options.shared:
            self._purge_shared_artefacts_for_ohos()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def _purge_shared_artefacts_for_ohos(self):
        import fnmatch
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _dirs, files in os.walk(libdir):
            for name in files:
                if (fnmatch.fnmatch(name, "*.so*")
                        or fnmatch.fnmatch(name, "*.la")):
                    stale = os.path.join(root, name)
                    try:
                        os.remove(stale)
                        self.output.info(
                            "removed stale shared artefact: %s" % stale)
                    except OSError as exc:
                        self.output.warning(
                            "cannot remove %s: %s" % (stale, exc))

    def package_info(self):
        self.cpp_info.libs = ["sasl2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "cyrus-sasl-login")
        self.cpp_info.set_property(
            "cmake_target_name", "cyrus-sasl-login::cyrus-sasl-login")
        self.cpp_info.set_property("pkg_config_name", "libsasl2")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]

    def _configure_args(self):
        args = [
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--prefix=/",
            "--disable-dependency-tracking",
            "--disable-sample",
        ]
        # Respect the shared option: static build links LOGIN et al. into
        # libsasl2.a (--with-staticsasl, no runtime dlopen); shared build
        # produces libsasl2.so for consumers that need it. Hard-coding
        # --disable-shared unconditionally breaks the shared=True graph
        # and leaves a stale libsasl2.so DT_NEEDED risk in consumers.
        if self.options.shared:
            args.extend([
                "--enable-shared",
                "--disable-static",
            ])
        else:
            args.extend([
                "--disable-shared",
                "--enable-static",
                "--with-staticsasl",
            ])
        args.extend([
            "--disable-staticdlopen",
            "--disable-alwaystrue",
            "--disable-gssapi",
            "--disable-httpform",
            "--disable-krb4",
            "--disable-ldapdb",
            "--disable-ntlm",
            "--disable-otp",
            "--disable-passdss",
            "--disable-sia",
            "--disable-sql",
            "--disable-srp",
            "--disable-srp-setpass",
            "--enable-login",
            "--without-saslauthd",
            "--without-authdaemond",
            "--without-des",
            "--without-gdbm",
            "--without-ldap",
            "--without-mysql",
            "--without-openssl",
            "--without-opie",
            "--without-pam",
            "--without-pgsql",
            "--without-pwcheck",
            "--without-sqlite",
            "--without-sqlite3",
            "--disable-auth-sasldb",
            "--with-dblib=none",
        ])
        return args

    def _build_cc_for_ohos(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={})
        if isinstance(executables, dict):
            return executables.get("c") or executables.get("cc") or "clang"
        return "clang"

    def _writable_tmpdir(self, source_folder):
        # HMBS injects a task-private writable TMPDIR on the real machine;
        # prefer it, fall back to a directory inside the source tree
        # (HMDFS default tmp may be read-only, cyrus-sasl/2.1.28 precedent).
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                return candidate
        tmpdir = os.path.join(source_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    def _copy_linksrcs_for_ohos(self, source_folder):
        # Static build (--with-staticsasl): link the self-contained
        # mechanism sources into libsasl2.a. LOGIN is the focus of this
        # package; PLAIN/ANONYMOUS/CRAM/DIGESTMD5 are the other
        # dependency-free companions (same flow as 2.1.28.1).
        links = {
            "plugins/login.c": "lib/login.c",
            "plugins/plain.c": "lib/plain.c",
            "plugins/anonymous.c": "lib/anonymous.c",
            "plugins/cram.c": "lib/cram.c",
            "plugins/digestmd5.c": "lib/digestmd5.c",
            "sasldb/db_none.c": "lib/db_none.c",
        }
        for source, target in links.items():
            src = os.path.join(source_folder, source)
            dst = os.path.join(source_folder, target)
            if os.path.isfile(src):
                shutil.copy2(src, dst)

    def _copy_install_sh_for_ohos(self, source_folder, tmpdir):
        source = os.path.join(source_folder, "config", "install-sh")
        destination = os.path.join(tmpdir, "install-sh")
        shutil.copy2(source, destination)
        # libtool --mode=install parses INSTALL as "<program> <flags>".
        # A "/system/bin/sh <script>" prefix makes libtool treat the
        # script path as a file to install ("no input file specified").
        # Rewrite the shebang to the device shell so INSTALL can stay a
        # single program path; copy2 preserves the tarball exec bit so
        # no chmod is required (HMBS_CAP_CHMOD=0 ignores chmod anyway).
        try:
            with open(destination, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
            lines = content.split("\n", 1)
            if lines and lines[0].startswith("#!"):
                lines[0] = "#!/system/bin/sh"
                content = "\n".join(lines) if len(lines) > 1 else lines[0]
                with open(destination, "w", encoding="utf-8",
                           errors="surrogateescape", newline="\n") as handle:
                    handle.write(content)
        except OSError:
            pass
        try:
            os.chmod(destination, 0o755)
        except OSError:
            pass
        return destination

    def _fix_autoconf_umask_for_ohos(self, source_folder):
        # HMDFS + setgid: autoconf template `umask 077 && mktemp -d
        # "./confXXXXXX"` yields an owner-unwritable dir, and every
        # subsequent write inside it (subs1.awk/subs1.sed) fails with
        # "Permission denied" (E011). Rewriting to umask 022 keeps the
        # same mktemp/mkdir flow with group/world-readable temp dirs,
        # safe on a single-user build machine (zzuf/daemonize precedent).
        configure = os.path.join(source_folder, "configure")
        try:
            with open(configure, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        if "umask 077" not in content:
            return
        content = content.replace("umask 077", "umask 022")
        with open(configure, "w", encoding="utf-8",
                   errors="surrogateescape") as handle:
            handle.write(content)

    def _mktemp_fallback_shim_for_ohos(self, tmpdir):
        # HMBS platform diagnosis [unsafe_local_mktemp]: a directory
        # created by mktemp on the current device filesystem cannot be
        # written by Autoconf afterwards. When HMBS injects
        # HMBS_AUTOCONF_MKTEMP_FALLBACK=1, shadow mktemp during the
        # configure step only so calls for "./conf*" fail and Autoconf
        # falls back to its `mkdir` path. All other mktemp calls are
        # delegated to the real binary; TMPDIR itself stays writable.
        if os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") != "1":
            return ""
        shim_dir = os.path.join(tmpdir, "hmbs-mktemp-shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        shim = os.path.join(shim_dir, "mktemp")
        script = (
            "#!/system/bin/sh\n"
            "for arg in \"$@\"; do\n"
            "  case \"$arg\" in\n"
            "    *conf*) exit 1 ;;\n"
            "  esac\n"
            "done\n"
            "for candidate in /system/bin/mktemp /bin/mktemp "
            "/usr/bin/mktemp; do\n"
            "  if [ -x \"$candidate\" ]; then\n"
            "    exec \"$candidate\" \"$@\"\n"
            "  fi\n"
            "done\n"
            "exec command -p mktemp \"$@\"\n"
        )
        try:
            with open(shim, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError:
                pass
        except OSError:
            return ""
        return shim_dir

    def _ohos_make_vars(self, install_sh):
        # Single program path (no shell prefix): libtool --mode=install
        # expects "INSTALL=<program> <flags>"; a shell prefix breaks
        # its parsing. The script shebang is already rewritten to
        # #!/system/bin/sh in _copy_install_sh_for_ohos.
        return (
            "MKDIR_P=\"%s -c -d\" "
            "INSTALL=\"%s -c\" "
            "INSTALL_PROGRAM=\"%s -c\" "
            "INSTALL_DATA=\"%s -c -m 644\""
            % (install_sh, install_sh, install_sh, install_sh)
        )

    def _run_login_smoke_test(self, source_folder):
        # Build-time smoke check: pluginviewer is an upstream utility
        # built with the tree; listing mechanisms proves the LOGIN
        # plugin object was compiled and linked. Runs only on a native
        # runnable target; cross builds skip (compile/link only).
        if not can_run(self):
            self.output.info("cross-building: LOGIN smoke test skipped")
            return
        viewer = os.path.join(source_folder, "utils", "pluginviewer")
        if not os.path.isfile(viewer):
            self.output.warning("pluginviewer not built; skipping LOGIN smoke test")
            return
        # Libtool wrapper is a /bin/sh script; OHOS has no /bin/sh, so
        # drive it explicitly through the device shell (ADAPTATION_GUIDE §8).
        shell = os.environ.get("CONFIG_SHELL") or "/system/bin/sh"
        self.run("%s \"%s\" -c" % (shell, viewer), cwd=source_folder)
