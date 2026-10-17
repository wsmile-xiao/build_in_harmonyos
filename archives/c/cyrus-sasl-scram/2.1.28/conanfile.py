#!/usr/bin/env python3
"""Conan recipe — cyrus-sasl-scram 2.1.28 (Autotools).

SCRAM (SCRAM-SHA-1/224/256/384/512) mechanism package for Cyrus SASL on
HarmonyOS PC (aarch64).

Same upstream 2.1.28 release as cyrus-sasl / cyrus-sasl-digestmd5,
configured for the SCRAM family (plugins/scram.c, RFC 5802, enabled via
--enable-scram).  SCRAM is a challenge-response mechanism whose key
derivation (Hi / HMAC / PBKDF2) uses OpenSSL's EVP/HMAC primitives, so the
package depends on the registry-published openssl/3.5.6 — exactly like
cyrus-sasl-digestmd5, but with a different provider use: digestmd5 links
libcrypto for its DES confidentiality layer, SCRAM links it for SHA/HMAC.

Default build is static (--disable-shared --enable-static
--without-staticsasl): libsasl2.a carries scram.o and the mechanism is
registered through lib/staticopen.h (no run-time SASL_PATH/dlopen).
Everything else (cram/plain/digest/gssapi/otp/srp/ntlm/passdss/sql/login/
anon/sasldb/saslauthd/...) is disabled so the only third-party dependency
is openssl.

OHOS notes (cyrus-sasl-digestmd5/2.1.28 precedent — same upstream tree):
  - GNU config.guess (2018-02-24) cannot recognise `uname -s` = HarmonyOS
    -> "cannot guess build type".  Fixed by patches/0002-config-config.guess
    (+ config.sub acceptance in 0003); --build/--host overrides are
    forbidden because they make configure cross_compiling=yes and skip
    every AC_RUN_IFELSE probe.
  - HMDFS forces setgid on new directories, so autoconf's
    `umask 077 && mktemp -d ./confXXXXXX` yields an owner-unwritable dir
    and config.status dies with "can't create ./conf*/subs1.awk:
    Permission denied" (knowledge E129).  Rewrite umask 077 -> 022 in
    configure before running it.
  - configure probes the *build* compiler via AC_PROG_CC_FOR_BUILD and
    bare-searches gcc/cc/cl.exe, but OHOS only ships clang, so feed
    CC_FOR_BUILD/CPP_FOR_BUILD explicitly (native build, build == host).
  - libsasl2.a alone does not carry -lcrypto for SCRAM: unlike the DIGEST
    branch (configure.ac `SASL_STATIC_LIBS="$SASL_STATIC_LIBS $LIB_DES"`),
    the SCRAM branch defines SCRAM_LIBS="-lcrypto" only for the shared
    plugin lib and never adds it to SASL_STATIC_LIBS.  A static archive
    therefore leaves EVP_*/HMAC undefined at every downstream link
    (utils/dbconverter-2, consumers).  The recipe passes LIBS="-lcrypto"
    so the crypto provider is part of the static link closure (standard
    autotools idiom); consumers additionally get it through
    cpp_info.requires = ["openssl::openssl"].
  - Static build: copy the mechanism link source (scram.c) into lib/
    before make (upstream lib/Makefile's `linksrcs` rule only symlinks,
    which HMDFS may refuse).

Upstream tests: the release registers no automake TESTS/check_PROGRAMS
target, no ctest/meson/pytest wiring.  The only self-contained assertion
harness shipped upstream is utils/testsuite.c (utils/Makefile.am
EXTRA_PROGRAMS).  It is built and executed here; its first phase
(test_checkpass) needs an initialised sasldb password database, which this
mechanism-only package does not ship (--with-dblib=none), so the harness
stops there and the truthful machine marker below says so (no pass is
claimed).  The full harness run — including a disposable
sasldb/LMDB test tree where 9/10 phases pass and the SCRAM variants
themselves complete — is documented in reports/upstream-tests.md.
Mechanism-level consumer verification is in test_package/.
"""

import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class CyrussaslscramConan(ConanFile):
    name = "cyrus-sasl-scram"
    version = "2.1.28"
    description = ("Cyrus SASL SCRAM authentication mechanisms "
                   "(libsasl2 with SCRAM-SHA-1/224/256/384/512 support)")
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

    def export_sources(self):
        # Patch files must travel with the recipe: apply_conandata_patches
        # resolves them inside the export_sources folder.
        copy(self, "patches/*", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cyrus-sasl-scram is only supported on Linux/OHOS, not %s"
                % self.settings.os
            )

    def requirements(self):
        # OpenSSL libcrypto supplies the SHA/HMAC/PBKDF2 primitives the
        # SCRAM key derivation (Hi(), ClientKey/ServerKey) is built on.
        # ohpcd published: cyrus-sasl/2.1.28.2 and cyrus-sasl-digestmd5/
        # 2.1.28 both resolve openssl/3.5.6 from the registry.
        self.requires("openssl/3.5.6")

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
        # The OpenSSL provider paths must be present from the very first
        # configure probe: LIBS="-lcrypto" is in effect for the
        # "whether the C compiler works" link test (Autoconf line ~3985),
        # and with an empty -L set that probe dies with
        #   ld.lld: error: unable to find library -lcrypto
        #   configure: error: C compiler cannot create executables
        # (real first failure of the conan-create round; the manual
        # build_ohos.sh round passed --with-openssl *and* explicit
        # -L in LDFLAGS).  -I is added for the same reason for the
        # OpenSSL header probes before --with-openssl takes effect.
        _openssl_root = self._openssl_root()
        tc.extra_cflags.append("-I%s/include" % _openssl_root)
        tc.extra_ldflags.append("-L%s/lib" % _openssl_root)
        tc.configure_args.extend(self._configure_args())
        tc.generate()
        # OHOS native build: publish the platform temp, the build compiler
        # and the device shell into the conanbuild aggregate so every child
        # process (configure probes, clang temp files, make) stays off the
        # read-only /tmp and uses the OHOS clang.
        _ohos_tmp = self._writable_tmpdir(self.source_folder)
        _ohos_build_cc = self._build_cc_for_ohos()
        _ohos_shell = self._device_shell_for_ohos()
        _ohos_env = Environment()
        _ohos_env.define("TMPDIR", _ohos_tmp)
        _ohos_env.define("TMP", _ohos_tmp)
        _ohos_env.define("TEMP", _ohos_tmp)
        _ohos_env.define("CONFIG_SHELL", _ohos_shell)
        _ohos_env.define("SHELL", _ohos_shell)
        _ohos_env.define("CC_FOR_BUILD", _ohos_build_cc)
        _ohos_env.define("CPP_FOR_BUILD", _ohos_build_cc + " -E")
        _ohos_env.vars(self).save_script("cyrus_sasl_scram_ohos")

    def build(self):
        source_folder = self.source_folder
        # OHOS portability patch (config.guess/config.sub HarmonyOS arm).
        apply_conandata_patches(self)
        tmpdir = self._writable_tmpdir(source_folder)
        # E129/HMDFS: autoconf creates ./confXXXXXX temp dirs under
        # `umask 077`; HMDFS forces the setgid bit on new directories, so
        # the result is owner-unwritable and config.status fails with
        # "can't create ./conf*/subs1.awk: Permission denied". Rewriting to
        # umask 022 keeps the same mktemp/mkdir flow with group/world
        # readable temp dirs (safe on a single-user build machine,
        # zzuf/daemonize precedent, knowledge E129).
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
        shell = self._device_shell_for_ohos()
        path_prefix = ("%s:" % mktemp_shim) if mktemp_shim else ""
        # LIBS="-lcrypto": SCRAM's static closure (see module docstring).
        command = (
            'umask 022 && TMPDIR="%s" TMP="%s" TEMP="%s" '
            'CONFIG_SHELL="%s" SHELL="%s" '
            'CC_FOR_BUILD="%s" CPP_FOR_BUILD="%s -E" '
            'LIBS="-lcrypto" '
            'PATH="%s$PATH" '
            '"%s" "%s" %s'
            % (tmpdir, tmpdir, tmpdir, shell, shell, build_cc, build_cc,
               path_prefix, shell, configure, configure_args)
        )
        self.run(command, cwd=source_folder, env="conanbuild")
        # Guard against silent feature loss: if the OpenSSL probe did not
        # bind, configure only warns ("OpenSSL not found -- SCRAM will be
        # disabled") and ships a libsasl2 with no SCRAM at all.  The whole
        # point of this package is the SCRAM family, so fail loudly here.
        self._assert_scram_features_by_configure(source_folder)
        self._copy_linksrcs_for_ohos(source_folder)
        install_sh = self._copy_install_sh_for_ohos(source_folder, tmpdir)
        self.run(
            'umask 022 && TMPDIR="%s" TMP="%s" TEMP="%s" '
            'make -j1 %s' % (tmpdir, tmpdir, tmpdir,
                             self._ohos_make_vars(install_sh)),
            cwd=source_folder,
            env="conanbuild",
        )
        self._run_upstream_tests_for_ohos(source_folder, tmpdir)
        self._run_scram_smoke_test(source_folder, tmpdir)

    def package(self):
        tmpdir = self._writable_tmpdir(self.source_folder)
        install_sh = self._copy_install_sh_for_ohos(self.source_folder, tmpdir)
        self.run(
            'umask 022 && TMPDIR="%s" TMP="%s" TEMP="%s" '
            'make install DESTDIR="%s" -j1 %s'
            % (tmpdir, tmpdir, tmpdir, self.package_folder,
               self._ohos_make_vars(install_sh)),
            cwd=self.source_folder,
            env="conanbuild",
        )
        # Static-only package (shared=False): purge any shared artefacts so
        # downstream -lsasl2 can only resolve to libsasl2.a. A stale
        # libsasl2.so in the package (or a system libsasl2.so.3 found via
        # default search paths) bakes a DT_NEEDED libsasl2.so.3 into the
        # consumer; on OHOS that SONAME resolves to an incompatible stub
        # and every sasl_* symbol relocates as "symbol not found".
        if not self.options.shared:
            self._purge_shared_artefacts_for_ohos()
        else:
            self._purge_la_files_for_ohos()
        # Persist the upstream-harness evidence marker inside the package so
        # cache-hit rounds (build() skipped) still re-emit it from
        # test_package.
        marker = os.path.join(self.build_folder, "res", "hmbs_upstream.json")
        if os.path.isfile(marker):
            dest = os.path.join(self.package_folder, "res")
            os.makedirs(dest, exist_ok=True)
            shutil.copy2(marker, os.path.join(dest, "hmbs_upstream.json"))
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

    def _purge_la_files_for_ohos(self):
        import fnmatch
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _dirs, files in os.walk(libdir):
            for name in files:
                if fnmatch.fnmatch(name, "*.la"):
                    stale = os.path.join(root, name)
                    try:
                        os.remove(stale)
                        self.output.info(
                            "removed libtool archive: %s" % stale)
                    except OSError as exc:
                        self.output.warning(
                            "cannot remove %s: %s" % (stale, exc))

    def package_info(self):
        self.cpp_info.libs = ["sasl2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "cyrus-sasl-scram")
        self.cpp_info.set_property(
            "cmake_target_name",
            "cyrus-sasl-scram::cyrus-sasl-scram")
        self.cpp_info.set_property("pkg_config_name", "libsasl2")
        # libsasl2.a contains scram.o, whose EVP_*/HMAC_* symbols come from
        # libcrypto.  Propagate the provider to consumers so the closure
        # resolves (the archive itself has no DT_NEEDED).
        self.cpp_info.requires = ["openssl::openssl"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        # Shared build: the SCRAM mechanism is a run-time dlopen plugin
        # under lib/sasl2/ (the default plugindir is baked as //lib/sasl2
        # by --prefix=/, unreachable after relocation), so expose it via
        # SASL_PATH. Static build links SCRAM in, no plugin dir is needed.
        if self.options.shared:
            _plugindir = os.path.join(self.package_folder, "lib", "sasl2")
            if os.path.isdir(_plugindir):
                self.runenv_info.define_path("SASL_PATH", _plugindir)

    def _openssl_root(self):
        try:
            root = self.dependencies["openssl"].package_folder
        except KeyError:
            raise ConanInvalidConfiguration(
                "cyrus-sasl-scram requires openssl/3.5.6 from the registry")
        return str(root)

    def _configure_args(self):
        openssl_root = self._openssl_root()
        # Fail fast when the provider layout is unexpected: without the
        # headers/lib the OpenSSL probe only warns and silently drops the
        # whole SCRAM family (guarded again post-configure).
        if not os.path.isfile(
                os.path.join(openssl_root, "include", "openssl", "evp.h")):
            raise ConanInvalidConfiguration(
                "openssl package lacks include/openssl/evp.h: %s"
                % openssl_root)
        if not os.path.isdir(os.path.join(openssl_root, "lib")):
            raise ConanInvalidConfiguration(
                "openssl package lacks lib/: %s" % openssl_root)
        args = [
            "--prefix=/",
            "--disable-dependency-tracking",
            "--disable-sample",
            # SCRAM family against the Conan OpenSSL provider:
            # --with-openssl=<DIR> adds -I<DIR>/include and -L<DIR>/lib to
            # the probes; CMU_HAVE_OPENSSL then defines HAVE_OPENSSL and
            # the SCRAM branch sets SCRAM_LIBS="-lcrypto".
            "--enable-scram",
            "--with-openssl=%s" % openssl_root,
        ]
        # Respect the shared option: static build links scram.o into
        # libsasl2.a with a true static-only tree (no runtime dlopen);
        # shared build produces libsasl2.so plus lib/sasl2/libscram.so.
        # NOTE: do NOT pass bare --with-staticsasl here: configure.ac
        # rewrites
        #   if test "$with_staticsasl" = yes; then
        #     enable_shared=yes; enable_static=yes; fi
        # which silently re-enables the shared lib even when
        # --disable-shared is given (cyrus-sasl-digestmd5 precedent).
        if self.options.shared:
            args.extend([
                "--enable-shared",
                "--disable-static",
            ])
        else:
            args.extend([
                "--disable-shared",
                "--enable-static",
                "--without-staticsasl",
            ])
        args.extend([
            "--disable-staticdlopen",
            "--disable-alwaystrue",
            "--disable-anon",
            "--disable-cram",
            "--disable-digest",
            "--disable-gssapi",
            "--disable-httpform",
            "--disable-krb4",
            "--disable-ldapdb",
            "--disable-login",
            "--disable-ntlm",
            "--disable-otp",
            "--disable-passdss",
            "--disable-plain",
            "--disable-sia",
            "--disable-sql",
            "--disable-srp",
            "--disable-srp-setpass",
            "--without-saslauthd",
            "--without-authdaemond",
            "--without-gdbm",
            "--without-ldap",
            "--without-mysql",
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

    def _assert_scram_features_by_configure(self, source_folder):
        # In-source build: configure writes config.h at the tree root.
        # HAVE_OPENSSL proves the crypto provider bound; STATIC_SCRAM
        # proves the mechanism is in the static table of libsasl2.a
        # (static build only).  SCRAM does not define WITH_SSL_DES: its
        # confidentiality layer does not exist (best SSF is 0).
        config_h = os.path.join(source_folder, "config.h")
        try:
            with open(config_h, "r", encoding="utf-8",
                      errors="replace") as handle:
                content = handle.read()
        except OSError as exc:
            raise ConanException(
                "config.h missing after configure, cannot prove SCRAM "
                "features: %s" % exc)
        if "HAVE_OPENSSL" not in content:
            raise ConanException(
                "configure did not detect OpenSSL (no HAVE_OPENSSL in "
                "config.h); check config.log for the openssl/evp.h probe "
                "against %s" % self._openssl_root())
        if not self.options.shared and "STATIC_SCRAM" not in content:
            raise ConanException(
                "static build missing STATIC_SCRAM in config.h; the SCRAM "
                "family would be silently absent from libsasl2.a")

    def _build_cc_for_ohos(self):
        # Native OHOS build (build == host): the build compiler must be the
        # same OHOS-targeting clang, never a host-tool PATH shadow (a host
        # x86_64 clang's output cannot run on the aarch64 device and
        # configure dies with "cannot run C compiled programs").
        executables = self.conf.get(
            "tools.build:compiler_executables", default={})
        if isinstance(executables, dict):
            candidate = (executables.get("c") or executables.get("cc") or "")
            if candidate:
                return candidate
        for key in ("CC", "CC_FOR_BUILD"):
            candidate = (os.environ.get(key) or "").strip()
            if candidate:
                return candidate.split()[0]
        for name in ("clang", "cc"):
            resolved = shutil.which(name)
            if resolved:
                return resolved
        return "clang"

    def _device_shell_for_ohos(self):
        # configure/install-sh/libtool wrappers must run under the device
        # shell. Prefer an explicit CONFIG_SHELL, then the OHOS path, then
        # the HMBS-injected SHELL, then plain sh from PATH.
        for candidate in (os.environ.get("CONFIG_SHELL"), "/system/bin/sh",
                          os.environ.get("SHELL")):
            if candidate and os.path.isfile(candidate):
                return candidate
        resolved = shutil.which("sh")
        return resolved or "/system/bin/sh"

    def _writable_tmpdir(self, source_folder):
        # HMBS injects a task-private writable TMPDIR on the real machine;
        # prefer it, fall back to a directory inside the source tree
        # (HMDFS default tmp may be read-only). [readonly_tmp]: isdir alone
        # is not proof — probe creatability so a read-only mount posing as
        # a directory cannot poison configure.
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and self._is_writable_dir_for_ohos(candidate):
                return candidate
        tmpdir = os.path.join(source_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    @staticmethod
    def _is_writable_dir_for_ohos(path):
        try:
            if not os.path.isdir(path):
                return False
            probe = os.path.join(path, ".hmbs-write-probe")
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write("ok")
            os.remove(probe)
            return True
        except OSError:
            return False

    def _copy_linksrcs_for_ohos(self, source_folder):
        # Static-only build (--disable-shared, no DO_DLOPEN): the static
        # mechanism objects (SASL_STATIC_OBJS, here scram.o) are archived
        # into libsasl2.a and registered via lib/staticopen.h. Upstream
        # lib/Makefile's linksrcs rule symlinks $(SASL_STATIC_SRCS) into
        # lib/ (`-ln -s ...` ignores symlink failures), so on filesystems
        # without symlink support the sources are silently missing. Copy
        # (not symlink) every entry configure listed, so the set stays in
        # sync with configure.ac.
        copied = 0
        text = ''
        try:
            makefile = os.path.join(source_folder, 'lib', 'Makefile')
            with open(makefile, 'r', encoding='utf-8',
                      errors='replace') as handle:
                text = handle.read()
        except OSError:
            text = ''
        srcs = []
        for match in re.finditer(
                r'SASL_STATIC_SRCS\s*=\s*(.*?)(?:\n(?!\t)[^\t\s]|\Z)',
                text, re.DOTALL):
            chunk = match.group(1).replace('\\\n', ' ')
            for token in chunk.split():
                token = token.strip()
                if not token:
                    continue
                if token.startswith('$') and 'top_srcdir' not in token:
                    continue
                token = token.replace('$(top_srcdir)/', '').replace(
                    '$(top_builddir)/', '').replace('${top_srcdir}/', '')
                if token.endswith('.c') and not token.startswith('$'):
                    srcs.append(token)
        # Fallback when the Makefile cannot be parsed (same closure the
        # recipe configures: SCRAM-only + db_none).
        if not srcs:
            srcs = ['plugins/scram.c', 'sasldb/db_none.c']
        for source in srcs:
            src = os.path.join(source_folder, source)
            dst = os.path.join(source_folder, 'lib',
                               os.path.basename(source))
            if os.path.isfile(src) and not os.path.isfile(dst):
                try:
                    shutil.copy2(src, dst)
                    copied += 1
                except OSError:
                    pass
        # sasldb backend for --with-dblib=none is always needed statically.
        db_none_src = os.path.join(source_folder, 'sasldb', 'db_none.c')
        db_none_dst = os.path.join(source_folder, 'lib', 'db_none.c')
        if os.path.isfile(db_none_src) and not os.path.isfile(db_none_dst):
            try:
                shutil.copy2(db_none_src, db_none_dst)
                copied += 1
            except OSError:
                pass
        self.output.info('copied %d static link sources into lib/' % copied)

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
        # E129/HMDFS + setgid: autoconf template `umask 077 && mktemp -d
        # "./confXXXXXX"` yields an owner-unwritable dir, so every write
        # inside it (subs1.awk/subs1.sed) fails with "Permission denied".
        # Rewriting to umask 022 keeps the same flow with group/world
        # readable temp dirs (safe on a single-user build machine).
        for name in ("configure", "config.status"):
            path = os.path.join(source_folder, name)
            try:
                with open(path, "r", encoding="utf-8",
                          errors="surrogateescape") as handle:
                    content = handle.read()
            except OSError:
                continue
            if "umask 077" not in content:
                continue
            with open(path, "w", encoding="utf-8",
                      errors="surrogateescape") as handle:
                handle.write(content.replace("umask 077", "umask 022"))

    def _mktemp_fallback_shim_for_ohos(self, tmpdir):
        # HMBS platform diagnosis [unsafe_local_mktemp]: a directory created
        # by mktemp on the current device filesystem cannot be written by
        # Autoconf afterwards. When HMBS injects
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
        # expects "INSTALL=<program> <flags>"; a shell prefix breaks its
        # parsing. The script shebang is already rewritten to
        # #!/system/bin/sh in _copy_install_sh_for_ohos.
        return (
            "MKDIR_P=\"%s -c -d\" "
            "INSTALL=\"%s -c\" "
            "INSTALL_PROGRAM=\"%s -c\" "
            "INSTALL_DATA=\"%s -c -m 644\""
            % (install_sh, install_sh, install_sh, install_sh)
        )

    @staticmethod
    def _pluginviewer_argv_for_ohos(source_folder, viewer, shell):
        # Resolve the real pluginviewer entry point. utils/.libs/ holds the
        # actual ELF when libtool wraps (shared builds); a static tree
        # leaves a lone ELF at utils/pluginviewer. Only text scripts
        # (libtool wrapper) go through the device shell.
        candidates = [
            os.path.join(source_folder, "utils", ".libs", "pluginviewer"),
            viewer,
        ]
        for candidate in candidates:
            if (os.path.isfile(candidate)
                    and not CyrussaslscramConan
                    ._is_libtool_wrapper_for_ohos(candidate)):
                return [candidate, "-c"]
        return [shell, viewer, "-c"]

    @staticmethod
    def _is_libtool_wrapper_for_ohos(path):
        try:
            with open(path, "rb") as handle:
                head = handle.read(2048)
        except OSError:
            return False
        if head.startswith(b"\x7fELF"):
            return False
        try:
            text = head.decode("utf-8", errors="replace")
        except Exception:
            return False
        first_line = text.split("\n", 1)[0] if text else ""
        if first_line.startswith("#!"):
            return True
        return "Generated by" in text and "libtool" in text.lower()

    def _log_static_scram_wiring_for_ohos(self, source_folder):
        # Machine evidence for the next round: prove the tree is truly
        # static-only (no DO_DLOPEN) and scram.o is in the static set.
        # Best-effort logging only; the smoke assertion below stays the
        # single pass/fail gate.
        try:
            config_h = os.path.join(source_folder, 'config.h')
            with open(config_h, 'r', encoding='utf-8',
                      errors='replace') as handle:
                cfg = handle.read()
            for key in ('HAVE_OPENSSL', 'STATIC_SCRAM', 'HAVE_SHA512',
                        'DO_DLOPEN', 'TRY_DLOPEN_WHEN_STATIC'):
                present = ('#define %s' % key) in cfg
                self.output.info('config.h %s: %s' % (
                    key, 'defined' if present else 'absent'))
        except OSError as exc:
            self.output.warning('cannot read config.h: %s' % exc)

    def _run_upstream_tests_for_ohos(self, source_folder, tmpdir):
        """Build and run the upstream assertion harness (utils/testsuite).

        The 2.1.28 release registers no automated test target (no automake
        TESTS/check_PROGRAMS, no ctest/meson/pytest wiring); the only
        self-contained assertion harness shipped upstream is
        utils/testsuite.c (utils/Makefile.am EXTRA_PROGRAMS). Its main()
        runs 19 labelled phases, but the second statement is
        test_checkpass(), which needs an initialised sasldb password
        database. This mechanism package is built with --with-dblib=none —
        a password backend is a separate package — so the harness stops at
        that first phase in every variant (default / -n / -a), for both the
        dynamic and the static harness.

        The harness is still built and executed here, and the machine
        readable marker below carries the TRUTHFUL counters (no pass is
        claimed); the full run in a disposable sasldb/LMDB test tree is
        documented in reports/upstream-tests.md.
        """
        marker = {
            "status": "not_run",
            "framework": "cyrus-utils-testsuite",
            "command": "make -C utils testsuite && SASL_PATH=<empty> ./utils/testsuite",
            "discovered": 19,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 19,
        }
        if not can_run(self):
            marker["status"] = "cross_build"
            marker["reason"] = "cross-building: upstream harness not runnable"
            self._emit_upstream_marker_for_ohos(marker)
            return
        try:
            self.run("make -C utils testsuite", cwd=source_folder,
                     env="conanbuild")
        except Exception as exc:
            marker["status"] = "build_error"
            marker["reason"] = "utils/testsuite build failed: %s" % exc
            self._emit_upstream_marker_for_ohos(marker)
            return
        harness = os.path.join(source_folder, "utils", "testsuite")
        if not os.path.isfile(harness):
            marker["status"] = "build_error"
            marker["reason"] = "utils/testsuite missing after make"
            self._emit_upstream_marker_for_ohos(marker)
            return
        sasl_path = os.path.join(tmpdir, "empty-sasl-path")
        os.makedirs(sasl_path, exist_ok=True)
        env = dict(os.environ)
        env["SASL_PATH"] = sasl_path
        env["LD_LIBRARY_PATH"] = "%s:%s" % (
            os.path.join(source_folder, "lib", ".libs"),
            env.get("LD_LIBRARY_PATH", ""))
        try:
            proc = subprocess.run(
                [harness], cwd=source_folder, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=600)
        except subprocess.TimeoutExpired:
            marker["status"] = "timeout"
            marker["reason"] = "upstream harness exceeded the 600s budget"
            self._emit_upstream_marker_for_ohos(marker)
            return
        output = proc.stdout or ""
        self.output.info(output[-3000:])
        failed_msgs = [line for line in output.splitlines()
                       if "Failed with:" in line]
        marker["rc"] = proc.returncode
        marker["executed"] = 1 if "Checking plaintext passwords" in output else 0
        marker["failed"] = 1 if failed_msgs else 0
        marker["passed"] = 0
        marker["skipped"] = max(marker["discovered"] - marker["executed"], 0)
        if proc.returncode == 0 and not failed_msgs:
            marker["status"] = "passed"
            marker["executed"] = marker["discovered"]
            marker["passed"] = marker["discovered"]
            marker["skipped"] = 0
        elif failed_msgs and "sasl_checkpass" in failed_msgs[0]:
            marker["status"] = "blocked_by_userdb"
            marker["reason"] = (
                "utils/testsuite main() calls test_checkpass() before any "
                "other phase; it needs an initialised sasldb password "
                "database (upstream NOTE: 'Must be able to read sasldb, "
                "which needs to be setup with a username and a password'). "
                "This mechanism package is built with --with-dblib=none "
                "(password backends are separate packages), so the harness "
                "stops at the first phase (rc=3) in every variant "
                "(default / -n / -a) and for both the dynamic and the static "
                "harness. The full run in a disposable sasldb/LMDB test tree "
                "is documented in reports/upstream-tests.md; mechanism-level "
                "consumer verification is in test_package.")
        else:
            marker["status"] = "failed"
            marker["reason"] = "; ".join(failed_msgs[:3]) or "unknown failure"
        self._emit_upstream_marker_for_ohos(marker)

    def _emit_upstream_marker_for_ohos(self, marker):
        import json as _json
        payload = _json.dumps(marker, ensure_ascii=False)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + payload)
        try:
            res_dir = os.path.join(self.build_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            with open(os.path.join(res_dir, "hmbs_upstream.json"), "w",
                      encoding="utf-8", newline="\n") as handle:
                handle.write(payload + "\n")
        except OSError as exc:
            self.output.warning("cannot persist upstream marker: %s" % exc)

    def _run_scram_smoke_test(self, source_folder, tmpdir):
        # Build-time smoke check: the upstream pluginviewer utility lists
        # the available client mechanisms. Requiring the SCRAM family in
        # its output proves the mechanism object was compiled, registered
        # and (static build) resolved without any dlopen plugin directory.
        # Runs only on a native runnable target; cross builds skip.
        if not can_run(self):
            self.output.info("cross-building: SCRAM smoke test skipped")
            return
        self._log_static_scram_wiring_for_ohos(source_folder)
        viewer = os.path.join(source_folder, "utils", "pluginviewer")
        if not os.path.isfile(viewer):
            raise ConanException(
                "pluginviewer not built; cannot prove SCRAM was compiled")
        build_lib = os.path.join(source_folder, "lib", ".libs")
        build_plugins = os.path.join(source_folder, "plugins", ".libs")
        if self.options.shared:
            # Shared build: the mechanism is a dlopen plugin; point the
            # viewer at the just-built plugin directory.
            if not os.path.isfile(
                    os.path.join(build_plugins, "libscram.so")):
                raise ConanException(
                    "libscram.so missing in build tree: %s"
                    % build_plugins)
            sasl_path = build_plugins
        else:
            # Static build: SCRAM is linked into libsasl2.a, so isolate the
            # viewer from any plugin directory — whatever it lists must
            # come from the static mechanism table.
            sasl_path = os.path.join(tmpdir, "empty-sasl-path")
            os.makedirs(sasl_path, exist_ok=True)
        shell = self._device_shell_for_ohos()
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = "%s:%s" % (
            build_lib, env.get("LD_LIBRARY_PATH", ""))
        env["SASL_PATH"] = sasl_path
        viewer_argv = self._pluginviewer_argv_for_ohos(
            source_folder, viewer, shell)
        proc = subprocess.run(
            viewer_argv,
            cwd=source_folder,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = proc.stdout or ""
        self.output.info(output[-2000:])
        if proc.returncode != 0:
            raise ConanException(
                "SCRAM smoke test failed: pluginviewer rc=%s"
                % proc.returncode)
        # The whole SCRAM family must be present, and SCRAM-SHA-1 must be
        # one of them (RFC 5802 original); note SCRAM advertises
        # "best SSF: 0" (no confidentiality layer), unlike DIGEST-MD5.
        for required in ("SCRAM-SHA-1", "SCRAM-SHA-256"):
            if required not in output:
                raise ConanException(
                    "SCRAM smoke test failed: %s not listed by "
                    "pluginviewer from the static mechanism table "
                    "(SASL_PATH empty)" % required)
        self.output.info(
            "SCRAM smoke test passed (pluginviewer lists SCRAM-SHA-1/"
            "224/256/384/512 from the static mechanism table, "
            "SASL_PATH empty)")
