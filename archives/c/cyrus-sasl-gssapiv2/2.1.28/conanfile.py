#!/usr/bin/env python3
"""Conan recipe — cyrus-sasl-gssapiv2 2.1.28 (Autotools).

GSSAPI mechanism package for Cyrus SASL on HarmonyOS PC (aarch64).

Same upstream 2.1.28 source as cyrus-sasl, configured for the GSSAPI
authentication mechanism (plugins/gssapi.c, enabled via
--enable-gssapi=<krb5> --with-gss_impl=mit; the plugin links the MIT
Kerberos GSSAPI libraries -lgssapi_krb5 -lkrb5 -lk5crypto -lcom_err).
Everything else is disabled so the package only needs krb5/1.22.1
(ohpcd published: consumed by merged canl-c/3.0.0 and
python-gssapi/1.8.3) plus the standard C library.

Default static build (--with-staticsasl) links gssapi.o into libsasl2.a
(gssapiv2_client/server_plug_init live in gssapi.c itself, and there is
no STATIC_GS2 wiring anywhere upstream, so no run-time SASL_PATH/dlopen
is needed); shared build produces libsasl2.so plus the
lib/sasl2/libgssapiv2.so dlopen plugin.

OHOS notes (cyrus-sasl/2.1.28.1 + cyrus-sasl-login/2.1.28 precedent):
  - configure probes the *build* compiler via AC_PROG_CC_FOR_BUILD and
    bare-searches gcc/cc/cl.exe, but OHOS only ships clang, so feed
    CC_FOR_BUILD/CPP_FOR_BUILD explicitly (native build, build == host).
  - HMDFS default TMPDIR may be unwritable; point TMPDIR at a writable
    directory (HMBS-injected TMPDIR preferred, else source-tree tmp/).
  - configure/install-sh must run under /system/bin/sh on device.
  - Static build: copy the plugin link source (gssapi.c) into lib/
    before make, same as the 2.1.28.1 _copy_linksrcs_for_ohos flow.
"""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class Cyrussaslgssapiv2Conan(ConanFile):
    name = "cyrus-sasl-gssapiv2"
    version = "2.1.28"
    description = "Cyrus SASL GSSAPI authentication mechanism (libsasl2 with GSSAPI support)"
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
                "cyrus-sasl-gssapiv2 is only supported on Linux/OHOS, not %s"
                % self.settings.os
            )

    def requirements(self):
        # MIT Kerberos GSSAPI provider (headers + -lgssapi_krb5 -lkrb5
        # -lk5crypto -lcom_err). ohpcd published: merged canl-c/3.0.0 and
        # python-gssapi/1.8.3 both resolve krb5/1.22.1 from the registry.
        self.requires("krb5/1.22.1")

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
        # OHOS native build (ADAPTATION_GUIDE section 2): the recipe drives
        # configure/make via explicit self.run() instead of the Autotools
        # helper, so the toolchain CC/sysroot environment is only visible
        # when callers pass env="conanbuild". Publish the platform temp
        # ([readonly_tmp]: /tmp is read-only, HMBS injects a writable
        # task-private TMPDIR) plus the build-compiler and device shell
        # into the conanbuild aggregate as well, so every child process
        # (configure probes, clang temp files, make) stays off /tmp even
        # if an inline VAR=val prefix is ever dropped by a shell wrapper.
        # The krb5 provider ships shared libraries, so its lib directory
        # is prepended to LD_LIBRARY_PATH here as well: configure links
        # every conftest with the GSSAPI probe libraries and must be able
        # to execute those binaries (otherwise "cannot run C compiled
        # programs"); make-time links need the same lookup path.
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
        try:
            _krb5_libdir = os.path.join(self._krb5_root(), "lib")
            if os.path.isdir(_krb5_libdir):
                _ohos_env.prepend_path("LD_LIBRARY_PATH", _krb5_libdir)
        except ConanInvalidConfiguration:
            pass
        _ohos_env.vars(self).save_script("cyrus_sasl_gssapiv2_ohos")

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
        shell = self._device_shell_for_ohos()
        path_prefix = ("%s:" % mktemp_shim) if mktemp_shim else ""
        # krb5 ships shared libraries: every configure conftest links the
        # GSSAPI probe libraries (via --enable-gssapi=<krb5>), so the
        # loader must resolve <krb5>/lib at conftest *execution* time,
        # otherwise configure dies with "cannot run C compiled programs"
        # at the "whether we are cross compiling" check (E467/E505).
        krb5_libdir = os.path.join(self._krb5_root(), "lib")
        command = (
            "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
            "CONFIG_SHELL=\"%s\" SHELL=\"%s\" "
            "CC_FOR_BUILD=\"%s\" CPP_FOR_BUILD=\"%s -E\" "
            "LD_LIBRARY_PATH=\"%s:$LD_LIBRARY_PATH\" "
            "PATH=\"%s$PATH\" "
            "\"%s\" \"%s\" %s"
            % (tmpdir, tmpdir, tmpdir, shell, shell, build_cc, build_cc,
               krb5_libdir, path_prefix, shell, configure, configure_args)
        )
        self.run(command, cwd=source_folder, env="conanbuild")
        # Guard against silent feature loss: SASL_GSSAPI_CHK degrades to
        # gssapi="no" with just a warning when the MIT link probe fails.
        # The whole point of this package is the GSSAPI mechanism, so a
        # configure that silently dropped it must fail loudly here.
        self._assert_gssapi_enabled_by_configure(source_folder)
        self._copy_linksrcs_for_ohos(source_folder)
        install_sh = self._copy_install_sh_for_ohos(source_folder, tmpdir)
        self.run(
            "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
            "LD_LIBRARY_PATH=\"%s:$LD_LIBRARY_PATH\" "
            "make -j1 %s" % (tmpdir, tmpdir, tmpdir, krb5_libdir,
                             self._ohos_make_vars(install_sh)),
            cwd=source_folder,
            env="conanbuild",
        )
        self._run_gssapi_smoke_test(source_folder, tmpdir)

    def package(self):
        tmpdir = self._writable_tmpdir(self.source_folder)
        install_sh = self._copy_install_sh_for_ohos(self.source_folder, tmpdir)
        self.run(
            "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
            "make install DESTDIR=\"%s\" -j1 %s"
            % (tmpdir, tmpdir, tmpdir, self.package_folder,
               self._ohos_make_vars(install_sh)),
            cwd=self.source_folder,
            env="conanbuild",
        )
        # Static-only package (shared=False): purge any shared artefacts
        # so downstream -lsasl2 can only resolve to libsasl2.a. A stale
        # libsasl2.so in the package (or a system libsasl2.so.3 found via
        # default search paths) bakes a DT_NEEDED libsasl2.so.3 into the
        # consumer; on OHOS that SONAME resolves to an incompatible stub
        # and every sasl_* symbol relocates as "symbol not found".
        if not self.options.shared:
            self._purge_shared_artefacts_for_ohos()
        else:
            # Shared package: drop libtool .la files (their libdir and
            # dependency_libs bake in build-machine absolute paths).
            # Keep the .so plugin set under lib/sasl2/ for dlopen.
            self._purge_la_files_for_ohos()
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
        self.cpp_info.set_property("cmake_file_name", "cyrus-sasl-gssapiv2")
        self.cpp_info.set_property(
            "cmake_target_name", "cyrus-sasl-gssapiv2::cyrus-sasl-gssapiv2")
        self.cpp_info.set_property("pkg_config_name", "libsasl2")
        # The GSSAPI plugin (and static libsasl2.a's gssapi.o) leaves
        # gss_* symbols to the final link; propagate the MIT Kerberos
        # provider to consumers (same pattern as canl-c/3.0.0).
        self.cpp_info.requires = ["krb5::krb5"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        # Shared build: the GSSAPIV2 mechanism is a run-time dlopen
        # plugin under lib/sasl2/ (default plugindir is baked as
        # //lib/sasl2 by --prefix=/, unreachable after relocation), so
        # expose it via SASL_PATH like cyrus-sasl/2.1.28 does. Static
        # build links GSSAPI in, no plugin directory exists or is needed.
        if self.options.shared:
            import os as _os
            _plugindir = _os.path.join(self.package_folder, "lib", "sasl2")
            if _os.path.isdir(_plugindir):
                self.runenv_info.define_path("SASL_PATH", _plugindir)

    def _krb5_root(self):
        try:
            root = self.dependencies["krb5"].package_folder
        except KeyError:
            raise ConanInvalidConfiguration(
                "cyrus-sasl-gssapiv2 requires krb5/1.22.1 from the registry")
        return str(root)

    def _gssapi_libs(self):
        # MIT Kerberos link line (--with-gss_impl=mit selects this same
        # set inside SASL_GSSAPI_CHK). Used only as a make-time LIBS
        # override (see _configure_args NOTE), never as a configure arg.
        return ("-L%s/lib -lgssapi_krb5 -lkrb5 -lk5crypto -lcom_err"
                % self._krb5_root())

    def _configure_args(self):
        krb5_root = self._krb5_root()
        # Fail fast when the provider layout is unexpected: without the
        # headers/libs, SASL_GSSAPI_CHK would only warn and silently
        # build a GSSAPI-less tree (guarded again post-configure).
        if not os.path.isfile(
                os.path.join(krb5_root, "include", "gssapi", "gssapi.h")):
            raise ConanInvalidConfiguration(
                "krb5 package lacks include/gssapi/gssapi.h: %s" % krb5_root)
        if not os.path.isdir(os.path.join(krb5_root, "lib")):
            raise ConanInvalidConfiguration(
                "krb5 package lacks lib/: %s" % krb5_root)
        args = [
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--prefix=/",
            "--disable-dependency-tracking",
            "--disable-sample",
            # GSSAPI against the Conan MIT Kerberos provider:
            # --enable-gssapi=<DIR> adds -I<DIR>/include and -L<DIR>/lib
            # to the probes; --with-gss_impl=mit selects the
            # -lgssapi_krb5 -lkrb5 -lk5crypto -lcom_err link line instead
            # of probing heimdal/cybersafe/seam first (m4/sasl2.m4
            # SASL_GSSAPI_CHK).
            "--enable-gssapi=%s" % krb5_root,
            "--with-gss_impl=mit",
            # NOTE: the MIT link line (-lgssapi_krb5 -lkrb5 -lk5crypto
            # -lcom_err) is deliberately NOT passed as a global
            # LIBS=<...> configure argument here. LIBS is a precious
            # variable: autoconf appends it to *every* link test, including
            # the initial AC_PROG_CC "whether we are cross compiling"
            # conftest. With krb5 shipping shared libraries and no
            # LD_LIBRARY_PATH at that point, that first conftest links
            # but cannot execute, and configure dies with "cannot run C
            # compiled programs" before any GSSAPI probe runs (true-machine
            # evidence 2026-09-12). The static link closure for utils/*
            # (dbconverter-2, pluginviewer link ../lib/.libs/libsasl2.a
            # directly) is instead supplied as a make-time LIBS override
            # in _ohos_make_vars(), which propagates to all sub-makes but
            # never poisons configure checks. The GSSAPI configure probes
            # themselves need no global LIBS: SASL_GSSAPI_CHK builds its
            # own -lgssapi_krb5 link line from --with-gss_impl=mit plus
            # -L<DIR>/lib from --enable-gssapi=<DIR>.
        ]
        # Respect the shared option: static build links gssapi.o into
        # libsasl2.a with a true static-only tree (no runtime dlopen);
        # shared build produces libsasl2.so plus lib/sasl2/libgssapiv2.so
        # for consumers that need the plugin model. NOTE: do NOT pass
        # bare --with-staticsasl here: configure.ac rewrites
        #   if test "$with_staticsasl" = yes; then
        #     enable_shared=yes; enable_static=yes; fi
        # which silently re-enables the shared lib even when
        # --disable-shared is given. pluginviewer then links the shared
        # libsasl2.so (DO_DLOPEN, PIC: static table skipped) and the
        # static-only smoke check (empty SASL_PATH, expect GSSAPI from
        # the static table) fails with rc=0/GSSAPI-listed=False.
        # --without-staticsasl keeps --disable-shared effective.
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
            "--disable-scram",
            "--disable-plain",
            "--disable-httpform",
            "--disable-krb4",
            "--disable-ldapdb",
            "--disable-login",
            "--disable-ntlm",
            "--disable-otp",
            "--disable-passdss",
            "--disable-sia",
            "--disable-sql",
            "--disable-srp",
            "--disable-srp-setpass",
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

    def _assert_gssapi_enabled_by_configure(self, source_folder):
        # In-source build: configure writes config.h at the tree root.
        # HAVE_GSSAPI must be defined — otherwise the mechanism this
        # package exists for was silently dropped (SASL_GSSAPI_CHK only
        # warns on probe failure).
        config_h = os.path.join(source_folder, "config.h")
        try:
            with open(config_h, "r", encoding="utf-8",
                      errors="replace") as handle:
                content = handle.read()
        except OSError as exc:
            raise ConanException(
                "config.h missing after configure, cannot prove GSSAPI "
                "was enabled: %s" % exc)
        if "HAVE_GSSAPI" not in content:
            raise ConanException(
                "configure silently disabled GSSAPI (no HAVE_GSSAPI in "
                "config.h); check config.log for the gssapi_krb5 link "
                "probe against krb5: %s" % self._krb5_root())
        # Static-only build must also wire the mechanism into the static
        # table (configure.ac defines STATIC_GSSAPIV2 whenever gssapi
        # is enabled). Without it pluginviewer/test_package enumeration
        # cannot see GSSAPI even though HAVE_GSSAPI is present.
        if not self.options.shared and "STATIC_GSSAPIV2" not in content:
            raise ConanException(
                "static build missing STATIC_GSSAPIV2 in config.h; "
                "GSSAPI would be silently absent from libsasl2.a")

    def _build_cc_for_ohos(self):
        # Native OHOS build (build == host): the build compiler must be the
        # same OHOS-targeting clang, never a host-tool PATH shadow (a host
        # x86_64 clang's output cannot run on the aarch64 device and
        # configure dies with "cannot run C compiled programs"). Prefer the
        # profile conf, then the toolchain CC from the build environment,
        # then an absolute PATH lookup; bare "clang" is the last resort.
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
        # (HMDFS default tmp may be read-only, cyrus-sasl/2.1.28 precedent).
        # [readonly_tmp]: isdir alone is not proof — probe creatability so
        # a read-only mount posing as a directory cannot poison configure
        # (clang temp files) and the "cannot run C compiled programs"
        # cascade that follows a broken conftest link.
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
        # mechanism objects (SASL_STATIC_OBJS, e.g. gssapi.o) are archived
        # into libsasl2.a and registered via lib/staticopen.h. Upstream
        # lib/Makefile linksrcs rule symlinks $(SASL_STATIC_SRCS) into
        # lib/ (`-ln -s ...` ignores symlink failures), so on filesystems
        # without symlink support the sources are silently missing. Copy
        # (not symlink) every entry configure listed, so the set stays in
        # sync when SASL_GSSAPI_CHK auto-enables gs2.c or dblib changes
        # (2.1.28.1 precedent used a hardcoded subset and missed gs2).
        import re as _re
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
        for match in _re.finditer(
                r'SASL_STATIC_SRCS\s*=\s*(.*?)(?:\n(?!\t)[^\t\s]|\Z)',
                text, _re.DOTALL):
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
        # recipe configures: GSSAPI-only + db_none; gs2.c is auto-added by
        # SASL_GSSAPI_CHK when the krb5 headers provide RFC5587/5801).
        if not srcs:
            srcs = ['plugins/gssapi.c', 'plugins/gs2.c',
                    'sasldb/db_none.c']
        for source in srcs:
            src = os.path.join(source_folder, source)
            dst = os.path.join(source_folder, 'lib',
                               os.path.basename(source))
            if os.path.isfile(src):
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
        # LIBS override (make-time only): utils/* link the static
        # libsasl2.a directly, so the MIT Kerberos closure must resolve
        # at that final link. Passed here — never as a configure argument
        # (see _configure_args NOTE) — so configure conftests stay clean
        # while every sub-make inherits the closure via command-line
        # variable propagation.
        return (
            "MKDIR_P=\"%s -c -d\" "
            "INSTALL=\"%s -c\" "
            "INSTALL_PROGRAM=\"%s -c\" "
            "INSTALL_DATA=\"%s -c -m 644\" "
            "LIBS=\"%s\""
            % (install_sh, install_sh, install_sh, install_sh,
               self._gssapi_libs())
        )

    def _log_static_gssapi_wiring_for_ohos(self, source_folder):
        # Machine evidence for the next round: prove the tree is truly
        # static-only (no DO_DLOPEN) and gssapi.o is in the static set.
        # Keep it best-effort logging only; the smoke assertion below
        # remains the single pass/fail gate.
        try:
            config_h = os.path.join(source_folder, 'config.h')
            with open(config_h, 'r', encoding='utf-8',
                      errors='replace') as handle:
                cfg = handle.read()
            for key in ('HAVE_GSSAPI', 'STATIC_GSSAPIV2', 'DO_DLOPEN',
                        'TRY_DLOPEN_WHEN_STATIC'):
                present = ('#define %s' % key) in cfg
                self.output.info('config.h %s: %s' % (
                    key, 'defined' if present else 'absent'))
        except OSError as exc:
            self.output.warning('cannot read config.h: %s' % exc)
        try:
            makefile = os.path.join(source_folder, 'lib', 'Makefile')
            with open(makefile, 'r', encoding='utf-8',
                      errors='replace') as handle:
                lines = [ln.rstrip() for ln in handle.readlines()
                         if 'SASL_STATIC' in ln or 'SASL_MECHS' in ln]
            for ln in lines[:10]:
                self.output.info('lib/Makefile: %s' % ln.strip())
        except OSError as exc:
            self.output.warning('cannot read lib/Makefile: %s' % exc)
        try:
            libdir = os.path.join(source_folder, 'lib')
            names = sorted(os.listdir(libdir))
            statics = [n for n in names if n.endswith('.c') or n == '.libs']
            self.output.info('lib/ entries: %s' % ', '.join(statics[:20]))
            dotlibs = os.path.join(libdir, '.libs')
            if os.path.isdir(dotlibs):
                artifacts = sorted(os.listdir(dotlibs))
                sasl_libs = [n for n in artifacts if 'sasl' in n.lower()]
                self.output.info('.libs sasl artifacts: %s'
                                 % ', '.join(sasl_libs[:20]))
        except OSError as exc:
            self.output.warning('cannot list lib/: %s' % exc)

    @staticmethod
    def _pluginviewer_argv_for_ohos(source_folder, viewer, shell):
        # Resolve the real pluginviewer entry point. utils/.libs/ holds
        # the actual ELF when libtool wraps (shared builds); a static
        # tree leaves a lone ELF at utils/pluginviewer. Only text
        # scripts (libtool wrapper, `Generated by ... libtool`) go
        # through the device shell; ELF binaries execute directly.
        candidates = [
            os.path.join(source_folder, "utils", ".libs", "pluginviewer"),
            viewer,
        ]
        for candidate in candidates:
            if (os.path.isfile(candidate)
                    and not Cyrussaslgssapiv2Conan
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

    def _run_gssapi_smoke_test(self, source_folder, tmpdir):
        # Build-time smoke check: the upstream pluginviewer utility lists
        # the available client mechanisms. Requiring "GSSAPI" in its
        # output proves the mechanism object was compiled and registered
        # (exit-0-alone is not proof). Runs only on a native runnable
        # target; cross builds skip (compile/link only). No KDC or
        # credentials are needed for mechanism enumeration.
        if not can_run(self):
            self.output.info("cross-building: GSSAPI smoke test skipped")
            return
        self._log_static_gssapi_wiring_for_ohos(source_folder)
        viewer = os.path.join(source_folder, "utils", "pluginviewer")
        if not os.path.isfile(viewer):
            raise ConanException(
                "pluginviewer not built; cannot prove GSSAPI was compiled")
        krb5_lib = os.path.join(self._krb5_root(), "lib")
        build_lib = os.path.join(source_folder, "lib", ".libs")
        build_plugins = os.path.join(source_folder, "plugins", ".libs")
        if self.options.shared:
            # Shared build: the mechanism is a dlopen plugin; point the
            # viewer at the just-built plugin directory.
            if not os.path.isfile(
                    os.path.join(build_plugins, "libgssapiv2.so")):
                raise ConanException(
                    "libgssapiv2.so missing in build tree: %s" % build_plugins)
            sasl_path = build_plugins
        else:
            # Static build: GSSAPI is linked into libsasl2.a, so isolate
            # the viewer from any plugin directory — whatever it lists
            # must come from the static mechanism table.
            sasl_path = os.path.join(tmpdir, "empty-sasl-path")
            os.makedirs(sasl_path, exist_ok=True)
        shell = self._device_shell_for_ohos()
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = (
            "%s:%s:%s" % (build_lib, krb5_lib,
                          env.get("LD_LIBRARY_PATH", "")))
        env["SASL_PATH"] = sasl_path
        # pluginviewer invocation depends on what libtool produced:
        # shared builds emit a libtool wrapper (text shell script that
        # must run through the device shell); static-only builds link a
        # real ELF binary, and feeding an ELF to `sh` fails with
        # "syntax error: unexpected ')'" (true-machine evidence
        # 2026-09-12: static tree lists only libsasl2.a in .libs yet the
        # smoke step ran `[sh, viewer, -c]` -> rc=1/GSSAPI-listed=False).
        # Prefer the real binary under utils/.libs when present,
        # otherwise sniff the file magic instead of assuming a wrapper.
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
        if proc.returncode != 0 or "GSSAPI" not in output:
            raise ConanException(
                "GSSAPI smoke test failed: rc=%s, GSSAPI listed=%s"
                % (proc.returncode, "GSSAPI" in output))
        self.output.info("GSSAPI smoke test passed (pluginviewer lists GSSAPI)")
