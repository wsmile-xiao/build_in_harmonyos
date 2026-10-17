#!/usr/bin/env python3
"""Conan recipe — cyrus-sasl-gs2 2.1.28 (Autotools).

GS2 mechanism package for Cyrus SASL on HarmonyOS PC (aarch64).

Same upstream 2.1.28 source as cyrus-sasl, configured for the GS2
authentication mechanism family (plugins/gs2.c, RFC 5801 GS2 bridge to
GSS-API; concrete SASL names are GS2-KRB5 etc. derived from the GSS
mechanisms via gss_inquire_saslname_for_mech). GS2 requires a GSS-API
implementation, provided here by the krb5/1.22.1 Conan package
(MIT Kerberos, README.GS2: "To build the GS2 SASL mechanism, you need
MIT Kerberos 1.9").

Packaging is shared (libsasl2 + plugin modules under lib/sasl2,
discovered at runtime via SASL_PATH/sasl_set_path, same pattern as
the cyrus-sasl/2.1.28 package and the Fedora cyrus-sasl-gs2
subpackage). Upstream 2.1.28 cannot link GS2 statically by design:
configure.ac defines no STATIC_GS2 and lib/staticopen.h has no GS2
entry, so a static libsasl2.a enumerates GSSAPI but never GS2-*.

OHOS notes (cyrus-sasl/2.1.28 + 2.1.28.1 precedent, CI-passed):
  - configure probes the *build* compiler via AC_PROG_CC_FOR_BUILD and
    bare-searches gcc/cc/cl.exe, but OHOS only ships clang, so feed
    CC_FOR_BUILD/CPP_FOR_BUILD explicitly (native build, build == host).
  - HMDFS default TMPDIR may be unwritable; point TMPDIR at a writable
    directory (HMBS-injected TMPDIR preferred, else build-folder _tmp).
  - Drive configure/make through the Autotools helper so the Conan
    toolchain env (CC/CFLAGS/LDFLAGS with OHOS sysroot/target) is
    honoured; a hand-rolled `sh configure` bypass loses it and the
    conftest binary cannot run ("cannot run C compiled programs").
  - GS2 itself always ships as the shared plugins/libgs2.so module
    (no upstream static support, see above), found at runtime via
    SASL_PATH (package runenv) or sasl_set_path() (consumer test).
  - Upstream m4/sasl2.m4 GS2 probe bug (2.1.28): in the
    gssapi/gssapi.h branch the rfc5801 check greps a
    "#include <gssapi.h>" conftest, which cannot preprocess when only
    the gssapi/ layout exists (MIT krb5) — rfc5801 stays empty and
    gs2 stays "no" while GSSAPI is enabled. The generated configure
    is patched to include <gssapi/gssapi.h> there (same technique as
    the umask fix below; no autoreconf needed on the device).
  - GSS detection relies on krb5 headers/libs via explicit
    CPPFLAGS/LDFLAGS plus --enable-gssapi=<krb5 prefix> (same pattern
    as the cyrus-sasl/2.1.28 --with-openssl=<prefix> precedent).
    AutotoolsDeps is deliberately NOT used: it exports the whole
    dependency closure via LIBS, so autoconf's earliest AC_PROG_CC
    "whether we are cross compiling" probe links -lgssapi_krb5 et al.
    and the conftest cannot run on OHOS (E467, rc=77). Only -I/-L plus
    a private DT_RPATH view are injected, never -l into LIBS and never
    a global LD_LIBRARY_PATH (E505).
"""

import glob
import os
import platform
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Cyrussaslgs2Conan(ConanFile):
    name = "cyrus-sasl-gs2"
    version = "2.1.28"
    description = "Cyrus SASL GS2 authentication mechanism (libsasl2 with GS2/GSSAPI support)"
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
        "shared": True,
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
                "cyrus-sasl-gs2 is only supported on Linux/OHOS, not %s"
                % self.settings.os
            )

    def requirements(self):
        self.requires("krb5/1.22.1")

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # E467: AutotoolsDeps exports the whole krb5 closure via LIBS, so
        # the very first AC_PROG_CC "whether we are cross compiling"
        # probe links -lgssapi_krb5/-lkrb5/... and the conftest cannot be
        # loaded on OHOS (configure rc=77 "cannot run C compiled
        # programs"). Do NOT generate AutotoolsDeps here. GSS detection
        # (SASL_GSSAPI_CHK) only needs headers + lib search paths plus
        # --enable-gssapi=<krb5 prefix>; those are link-only checks, so
        # an -I/-L-only injection keeps the early run-probe empty while
        # later probes still find krb5. Runtime loading of any linked
        # conftest/pluginviewer is covered by a private DT_RPATH view
        # (E505); never export a global LD_LIBRARY_PATH (E505 forbid_2:
        # it overrides DT_RPATH and poisons toolchain subprocesses).
        os.environ.pop("LD_LIBRARY_PATH", None)
        tc = AutotoolsToolchain(self)
        # Old codebase: clang 15 promotes implicit-function-declaration /
        # int-conversion to errors; demote to warnings (standard practice
        # for building legacy C, same as cyrus-sasl/2.1.28).
        tc.extra_cflags.append("-Wno-error=implicit-function-declaration")
        tc.extra_cflags.append("-Wno-error=int-conversion")
        tc.configure_args.extend(self._configure_args())
        # cyrus-sasl/2.1.28 precedent: OHOS only ships clang, feed the
        # build compiler explicitly as configure args (configure treats
        # VAR=value args as env assignments).
        build_cc = self._build_cc_for_ohos()
        tc.configure_args.append("CC_FOR_BUILD=%s" % build_cc)
        tc.configure_args.append("CPP_FOR_BUILD=%s -E" % build_cc)
        cppflags, ldflags = self._krb5_search_flags_for_ohos()
        if cppflags:
            tc.configure_args.append("CPPFLAGS=%s" % cppflags)
        if ldflags:
            tc.configure_args.append("LDFLAGS=%s" % ldflags)
        tc.generate()

    def build(self):
        # E505 forbid_2: never let a global LD_LIBRARY_PATH leak into
        # configure/make (it overrides DT_RPATH and poisons toolchain
        # subprocesses). Runtime search is via the DT_RPATH view baked
        # through LDFLAGS in generate().
        os.environ.pop("LD_LIBRARY_PATH", None)
        source_folder = self.source_folder
        # E011/HMDFS: autoconf creates ./confXXXXXX temp dirs under
        # `umask 077` (0700 + setgid -> drwx--S---, owner-unwritable), so
        # config.status fails with "can't create ./conf*/subs1.awk:
        # Permission denied". Rewrite to umask 022 in the generated
        # script (platform adaptation, same as zzuf/daemonize precedent).
        # Must run before autotools.configure() (it does not regenerate
        # configure here; tarball ships it).
        self._fix_autoconf_umask_for_ohos(source_folder)
        self._fix_gs2_detection_for_ohos(source_folder)
        tmpdir = self._ensure_writable_tmp_for_ohos()
        self._ensure_device_shell_for_ohos()
        self._uname_shim_for_ohos()
        configure = os.path.join(source_folder, "configure")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration(
                "configure not found in source tree: %s" % configure
            )
        autotools = Autotools(self)
        autotools.configure()
        install_sh = self._copy_install_sh_for_ohos(source_folder, tmpdir)
        autotools.make(args=["-j1"] + self._ohos_make_args(install_sh))
        self._run_gs2_smoke_test(source_folder)

    def package(self):
        tmpdir = self._ensure_writable_tmp_for_ohos()
        self._ensure_device_shell_for_ohos()
        install_sh = self._copy_install_sh_for_ohos(self.source_folder, tmpdir)
        autotools = Autotools(self)
        autotools.install(args=["-j1"] + self._ohos_make_args(install_sh))
        # Drop libtool .la files: they embed the build-machine absolute
        # paths (libdir='//lib', dependency_libs with conan cache paths)
        # and break downstream libtool linking after relocation. Link
        # info is already provided by .pc + cpp_info. The .so modules
        # under lib/sasl2 must be kept: libgs2.so is the GS2 mechanism.
        self._remove_libtool_archives_for_ohos()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def _remove_libtool_archives_for_ohos(self):
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
        self.cpp_info.set_property("cmake_file_name", "cyrus-sasl-gs2")
        self.cpp_info.set_property(
            "cmake_target_name", "cyrus-sasl-gs2::cyrus-sasl-gs2")
        self.cpp_info.set_property("pkg_config_name", "libsasl2")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "m", "pthread"]
        # Mechanism plugins are dlopen()ed at runtime. The library's
        # compiled-in default plugin path points at prefix //lib/sasl2
        # (prefix=/), which does not exist after Conan relocation, so
        # expose the package plugin dir via SASL_PATH (same pattern as
        # the cyrus-sasl/2.1.28 package). The consumer test additionally
        # pins it via sasl_set_path() with a baked-in absolute path.
        self.runenv_info.define_path(
            "SASL_PATH", os.path.join(self.package_folder, "lib", "sasl2"))

    def _krb5_prefix_for_ohos(self):
        try:
            return str(self.dependencies["krb5"].package_folder)
        except Exception:
            return ""

    def _krb5_search_flags_for_ohos(self):
        # E467/E505: -I/-L-only injection for krb5 (no LIBS, no
        # LD_LIBRARY_PATH). Returns (CPPFLAGS, LDFLAGS) strings for
        # configure args. LDFLAGS points at a private materialised
        # DT_RPATH view (regular-file copies under each soname alias)
        # so any conftest that links -lgssapi_krb5 can run without
        # LD_LIBRARY_PATH; --disable-new-dtags keeps DT_RPATH (not
        # RUNPATH) so an inherited LD_LIBRARY_PATH cannot override it.
        try:
            dep = self.dependencies["krb5"]
        except Exception:
            return "", ""
        try:
            pkg = str(dep.package_folder)
        except Exception:
            pkg = ""
        inc_dirs = []
        lib_dirs = []
        try:
            for rel in (dep.cpp_info.includedirs or []):
                cand = rel if os.path.isabs(rel) else os.path.join(pkg, rel)
                if os.path.isdir(cand) and cand not in inc_dirs:
                    inc_dirs.append(cand)
            for rel in (dep.cpp_info.libdirs or []):
                cand = rel if os.path.isabs(rel) else os.path.join(pkg, rel)
                if os.path.isdir(cand) and cand not in lib_dirs:
                    lib_dirs.append(cand)
        except Exception:
            pass
        if pkg and not inc_dirs:
            cand = os.path.join(pkg, "include")
            if os.path.isdir(cand):
                inc_dirs.append(cand)
        if pkg and not lib_dirs:
            cand = os.path.join(pkg, "lib")
            if os.path.isdir(cand):
                lib_dirs.append(cand)
        view = self._materialise_krb5_view_for_ohos(lib_dirs)
        cppflags = " ".join("-I%s" % d for d in inc_dirs)
        parts = []
        search_dirs = []
        if view:
            search_dirs.append(view)
        for d in lib_dirs:
            if d not in search_dirs:
                search_dirs.append(d)
        for d in search_dirs:
            parts.append("-L%s" % d)
        if view:
            parts.append("-Wl,--disable-new-dtags")
            parts.append("-Wl,-rpath,%s" % view)
        elif lib_dirs:
            parts.append("-Wl,--disable-new-dtags")
            parts.append("-Wl,-rpath,%s" % lib_dirs[0])
        return cppflags, " ".join(parts)

    def _materialise_krb5_view_for_ohos(self, lib_dirs):
        # E505 materialised view under the task-private build folder
        # (R49: never inject the shared SYS_PREFIX). Each .so alias
        # becomes a regular-file copy of its target so the OHOS musl
        # loader can resolve soname aliases without symlinks.
        try:
            base = self.build_folder
        except Exception:
            return ""
        if not base:
            return ""
        view = os.path.join(str(base), "ohos-runtime-libs")
        try:
            os.makedirs(view, exist_ok=True)
        except OSError:
            return ""
        for libdir in lib_dirs or []:
            try:
                names = os.listdir(libdir)
            except OSError:
                continue
            for name in names:
                if not (name.endswith(".so") or ".so." in name):
                    continue
                src = os.path.join(libdir, name)
                try:
                    real = os.path.realpath(src)
                except Exception:
                    real = src
                if not os.path.isfile(real):
                    continue
                dst = os.path.join(view, name)
                try:
                    if os.path.isfile(dst):
                        try:
                            if os.path.getsize(dst) == os.path.getsize(real):
                                continue
                        except OSError:
                            pass
                except OSError:
                    pass
                try:
                    shutil.copyfile(real, dst)
                except OSError:
                    continue
                try:
                    os.chmod(dst, 0o755)
                except OSError:
                    pass
        return view if os.path.isdir(view) else ""

    def _gnu_triplet_for_arch(self, arch):
        if arch in ("armv8", "armv8.3", "arm64", "aarch64"):
            return "aarch64-unknown-linux-gnu"
        if arch in ("x86_64", "x64", "amd64"):
            return "x86_64-unknown-linux-gnu"
        return ""

    def _build_arch_for_ohos(self):
        try:
            build_arch = self.settings_build.get_safe("arch")
        except Exception:
            build_arch = None
        if build_arch:
            return str(build_arch)
        machine = (platform.machine() or "").lower()
        if machine in ("aarch64", "arm64"):
            return "armv8"
        if machine in ("x86_64", "amd64"):
            return "x86_64"
        try:
            return str(self.settings.arch)
        except Exception:
            return "armv8"

    def _configure_args(self):
        # --build must describe the machine running configure, --host the
        # machine running the binaries. Hardcoding both to aarch64 turns a
        # real cross build (x86_64 build -> aarch64 host) into a fake
        # "native" one, and configure then fails with "cannot run C
        # compiled programs" when it tries to execute the aarch64
        # conftest on x86_64. Derive both from settings so native stays
        # native and cross stays cross (cyrus-sasl/2.1.28 precedent uses
        # the AutotoolsToolchain auto triplets for the same reason).
        try:
            host_arch = str(self.settings.arch)
        except Exception:
            host_arch = "armv8"
        build_arch = self._build_arch_for_ohos()
        host_triplet = self._gnu_triplet_for_arch(host_arch)
        build_triplet = self._gnu_triplet_for_arch(build_arch)
        args = []
        if build_triplet:
            args.append("--build=%s" % build_triplet)
        if host_triplet:
            args.append("--host=%s" % host_triplet)
        args.extend([
            "--prefix=/",
            "--disable-dependency-tracking",
            "--disable-sample",
        ])
        # GS2 ships upstream only as a shared plugin module
        # (plugins/libgs2.la): 2.1.28 defines no STATIC_GS2 and
        # lib/staticopen.h has no GS2 entry, so a static-only
        # libsasl2.a can never enumerate GS2-*. Always build the
        # shared library plus plugin modules; shared=False additionally
        # keeps the static archive (with --enable-staticdlopen so it can
        # still dlopen the GS2 plugin at runtime via SASL_PATH).
        if self.options.shared:
            args.extend([
                "--enable-shared",
                "--disable-static",
                "--disable-staticdlopen",
            ])
        else:
            args.extend([
                "--enable-shared",
                "--enable-static",
                "--enable-staticdlopen",
            ])
        args.extend([
            "--disable-krb4",
            "--disable-httpform",
            "--disable-ldapdb",
            "--disable-login",
            "--disable-ntlm",
            "--disable-otp",
            "--disable-passdss",
            "--disable-sia",
            "--disable-sql",
            "--disable-srp",
            "--disable-srp-setpass",
            "--disable-scram",
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
        # GS2 needs MIT Kerberos GSS-API (README.GS2: MIT Kerberos 1.9+).
        # Explicit prefix (cyrus-sasl/2.1.28 --with-openssl=<prefix>
        # precedent) plus CPPFLAGS/LDFLAGS -I/-L lets SASL_GSSAPI_CHK find
        # gssapi headers and -lgssapi_krb5; rfc5587+rfc5801 in krb5 1.22
        # then enables libgs2.la automatically alongside libgssapiv2.la.
        krb5_prefix = self._krb5_prefix_for_ohos()
        if krb5_prefix:
            args.append("--enable-gssapi=%s" % krb5_prefix)
        else:
            args.append("--enable-gssapi")
        args.append("--with-gss_impl=mit")
        return args

    def _build_cc_for_ohos(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={})
        if isinstance(executables, dict):
            return executables.get("c") or executables.get("cc") or "clang"
        return "clang"

    def _ensure_writable_tmp_for_ohos(self):
        # [readonly_tmp]: /tmp is read-only on the device. Prefer the
        # HMBS-injected task-private TMPDIR, else a dir under the build
        # folder (same filesystem as the build, exec allowed), else a dir
        # inside the source tree (cyrus-sasl/2.1.28 precedent). Export to
        # TMPDIR/TMP/TEMP so configure/conftest/make never touch /tmp.
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                tmpdir = candidate
                break
        else:
            tmpdir = ""
        if not tmpdir:
            try:
                tmpdir = os.path.join(self.build_folder, "_tmp")
            except Exception:
                tmpdir = ""
        if not tmpdir:
            tmpdir = os.path.join(self.source_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        return tmpdir

    def _ensure_device_shell_for_ohos(self):
        # configure/install-sh must run under the device shell. HMBS
        # injects SHELL=/bin/sh and the preflight reports
        # shell=/bin/sh; older notes used /system/bin/sh. Pick whichever
        # exists so Autotools does not fall back to a missing /bin/sh.
        for candidate in (os.environ.get("CONFIG_SHELL"),
                          os.environ.get("SHELL"),
                          "/system/bin/sh", "/bin/sh"):
            if candidate and os.path.isfile(candidate):
                os.environ["CONFIG_SHELL"] = candidate
                os.environ["SHELL"] = candidate
                return candidate
        return os.environ.get("SHELL", "/bin/sh")

    def _uname_shim_for_ohos(self):
        # cyrus-sasl/2.1.28 precedent: normalize uname for configure
        # config.guess checks on OHOS (kernel reports HongMeng).
        try:
            shim_dir = os.path.join(self.build_folder, "_uname_shim")
        except Exception:
            return
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return
        shim = os.path.join(shim_dir, "uname")
        script = (
            "#!/bin/sh\n"
            "case \"${1:-}\" in\n"
            "  -s|\"\") echo Linux ;;\n"
            "  -r) echo 6.6 ;;\n"
            "  -m) echo aarch64 ;;\n"
            "  *) exec /system/bin/uname \"$@\" 2>/dev/null"
            " || exec /bin/uname \"$@\" ;;\n"
            "esac\n"
        )
        try:
            with open(shim, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError:
                pass
        except OSError:
            return
        path = os.environ.get("PATH", "")
        if shim_dir not in path.split(os.pathsep):
            os.environ["PATH"] = shim_dir + os.pathsep + path

    def _fix_gs2_detection_for_ohos(self, source_folder):
        # Upstream m4/sasl2.m4 GS2 probe bug (2.1.28, generated configure
        # already contains it; patching the generated script avoids an
        # on-device autoreconf, same technique as the umask fix below).
        # In the gssapi/gssapi.h branch the rfc5801 conftest reads
        # "#include <gssapi.h>", which cannot preprocess when only the
        # gssapi/ header layout exists (MIT krb5): the grep then finds
        # no gss_inquire_mech_for_saslname, rfc5801 stays empty and
        # gs2 stays "no" while GSSAPI itself is enabled — exactly the
        # preflight symptom (mechlist GSSAPI present, no GS2-*).
        # The (rfc5587 ok with <gssapi/gssapi.h>, rfc5801 with
        # <gssapi.h>) two-block sequence is unique to that branch, so
        # only the buggy include is rewritten.
        patched = False
        for pattern in (os.path.join(source_folder, "configure"),
                        os.path.join(source_folder, "**", "configure")):
            for configure in glob.glob(pattern, recursive=True):
                try:
                    with open(configure, "r", encoding="utf-8",
                              errors="surrogateescape") as handle:
                        content = handle.read()
                except OSError:
                    continue
                old_block = (
                    '#include <gssapi/gssapi.h>\n'
                    '\n'
                    '_ACEOF\n'
                    'if (eval "$ac_cpp conftest.$ac_ext") 2>&5 |\n'
                    '  $EGREP "gss_inquire_attrs_for_mech" >/dev/null 2>&1; then :\n'
                    '  rfc5587=yes\n'
                    'fi\n'
                    'rm -f conftest*\n'
                    '\n'
                    '    cat confdefs.h - <<_ACEOF >conftest.$ac_ext\n'
                    '/* end confdefs.h.  */\n'
                    '#include <gssapi.h>\n'
                    '\n'
                    '_ACEOF\n'
                    'if (eval "$ac_cpp conftest.$ac_ext") 2>&5 |\n'
                    '  $EGREP "gss_inquire_mech_for_saslname" >/dev/null 2>&1; then :\n'
                    '  rfc5801=yes\n'
                    'fi\n'
                )
                if old_block not in content:
                    continue
                new_block = old_block.replace(
                    "#include <gssapi.h>",
                    "#include <gssapi/gssapi.h>", 1)
                content = content.replace(old_block, new_block, 1)
                try:
                    with open(configure, "w", encoding="utf-8",
                               errors="surrogateescape") as handle:
                        handle.write(content)
                    self.output.info(
                        "patched GS2 rfc5801 probe in %s" % configure)
                    patched = True
                except OSError:
                    pass
        if not patched:
            self.output.warning(
                "GS2 rfc5801 probe pattern not found; "
                "upstream may have fixed the gssapi.h branch")

    def _copy_install_sh_for_ohos(self, source_folder, tmpdir):
        source = os.path.join(source_folder, "config", "install-sh")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        destination = os.path.join(tmpdir, "install-sh")
        shutil.copy2(source, destination)
        # libtool --mode=install parses INSTALL as "<program> <flags>".
        # A "/system/bin/sh <script>" prefix makes libtool treat the
        # script path as a file to install ("no input file specified").
        # Rewrite the shebang to the device shell so INSTALL can stay a
        # single program path; copy2 preserves the tarball exec bit so
        # no chmod is required (HMBS_CAP_CHMOD=0 ignores chmod anyway).
        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") \
            or "/system/bin/sh"
        try:
            with open(destination, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
            lines = content.split("\n", 1)
            if lines and lines[0].startswith("#!"):
                lines[0] = "#!%s" % shell
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
        for pattern in (os.path.join(source_folder, "configure"),
                        os.path.join(source_folder, "**", "configure")):
            for configure in glob.glob(pattern, recursive=True):
                try:
                    with open(configure, "r", encoding="utf-8",
                              errors="surrogateescape") as handle:
                        content = handle.read()
                except OSError:
                    continue
                if "umask 077" not in content:
                    continue
                content = content.replace("umask 077", "umask 022")
                try:
                    with open(configure, "w", encoding="utf-8",
                               errors="surrogateescape") as handle:
                        handle.write(content)
                except OSError:
                    pass

    def _ohos_make_args(self, install_sh):
        # Single program path (no shell prefix): libtool --mode=install
        # expects "INSTALL=<program> <flags>"; a shell prefix breaks
        # its parsing. The script shebang is already rewritten to the
        # device shell in _copy_install_sh_for_ohos.
        # NOTE: Conan's Autotools.make joins args into a shell string
        # ("make " + " ".join(args)), so a VAR value containing spaces
        # must be shell-quoted as a whole. Quoting only the program path
        # yields `MKDIR_P=/path/install-sh -c -d`, which the shell splits
        # into `MKDIR_P=/path/install-sh`, `-c`, `-d`; make treats `-c`
        # as an (invalid) option, prints usage and exits 2. Quote the
        # full "program + flags" value instead.
        return [
            "MKDIR_P=%s" % shlex.quote("%s -c -d" % install_sh),
            "INSTALL=%s" % shlex.quote("%s -c" % install_sh),
            "INSTALL_PROGRAM=%s" % shlex.quote("%s -c" % install_sh),
            "INSTALL_DATA=%s" % shlex.quote("%s -c -m 644" % install_sh),
        ]

    def _run_gs2_smoke_test(self, source_folder):
        # Build-time smoke check: pluginviewer is an upstream utility
        # built with the tree; listing mechanisms proves the GS2/GSSAPI
        # plugin modules were compiled. Runs only on a native runnable
        # target; cross builds skip (compile/link only).
        if not can_run(self):
            self.output.info("cross-building: GS2 smoke test skipped")
            return
        viewer = os.path.join(source_folder, "utils", "pluginviewer")
        if not os.path.isfile(viewer):
            self.output.warning("pluginviewer not built; skipping GS2 smoke test")
            return
        # Shared plugins live in the build tree until `make install`;
        # point SASL_PATH at them so the listing reflects the freshly
        # built modules (libgs2.so) rather than the baked-in //lib/sasl2.
        # Libtool wrapper is a /bin/sh script; drive it explicitly
        # through the device shell (ADAPTATION_GUIDE section 8).
        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") \
            or "/system/bin/sh"
        for plugdir in (os.path.join(source_folder, "plugins", ".libs"),
                        os.path.join(source_folder, "plugins")):
            if os.path.isdir(plugdir):
                os.environ["SASL_PATH"] = plugdir
                break
        self.run("%s \"%s\" -c" % (shell, viewer), cwd=source_folder)
