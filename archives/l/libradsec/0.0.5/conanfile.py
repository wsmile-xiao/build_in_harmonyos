#!/usr/bin/env python3
"""Conan recipe — libradsec 0.0.5 (Autotools).

libradsec is a RADIUS protocol client library (with optional RadSec/TLS support).
It is NOT a system same-name library (R26), so dynamic linkage is allowed and
Conan manages the dependency chain.

Base adaptation (路径 A):
- --disable-tls: the TLS (RadSec) transport needs libevent's event_openssl
  component, which is not available in the published libevent/2.1.12 package
  (it disables OpenSSL). Disabling TLS keeps the full RADIUS (UDP/TCP)
  functionality and avoids the missing OpenSSL-backed event_openssl dependency.
- anti-Werror flags (E063): configure.ac' AM_CFLAGS contains -Werror, which
  promotes the many warnings of this 2014-era C codebase to errors under
  clang 15. Targeted -Wno-error=... flags are injected via extra_cflags.
- libconfuse is BUNDLED (not a Conan dependency): the ohpcd remote publishes no
  libconfuse OHOS binary, so --build=missing would build its recipe via autotools
  from *source*.  That remote configure cannot run on HMDFS — bash/HNP shell
  cannot getcwd() against the conan build folder (``configure: error: working
  directory cannot be determined``), and the failure is in the dependency whose
  recipe we cannot patch from here.  Instead this recipe fetches the public
  libconfuse 3.3 tarball and compiles it statically (non-configure) into a stage
  dir, which is exposed to libradsec's own configure via -I/-L so its
  ``AC_CHECK_LIB([confuse], [cfg_init])`` succeeds; libconfuse is then linked
  into the produced libradsec library.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# libconfuse 3.3 direct-compile config.h (see archives/c/confuse/3.3/notes.md:
# OHOS/musl has strdup/strndup/strcasecmp/setenv/unsetenv/fmemopen; reallocarray
# is missing so the bundled reallocarray.c is compiled; NLS disabled).
_LIB_CONFUSE_CONFIG_H = """\
/* Generated config.h for libconfuse HMDFS manual-compile (no configure). */
#define PACKAGE "libconfuse"
#define PACKAGE_NAME "libConfuse"
#define PACKAGE_TARNAME "confuse"
#define PACKAGE_VERSION "3.3"
#define PACKAGE_STRING "libConfuse 3.3"
#define PACKAGE_BUGREPORT "https://github.com/libconfuse/libconfuse/issues"
#define VERSION "3.3"
#define STDC_HEADERS 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_STRING_H 1
#define HAVE_STRINGS_H 1
#define HAVE_STDLIB_H 1
#define HAVE_UNISTD_H 1
#define HAVE_INTTYPES_H 1
#define HAVE_MEMORY_H 1
#define HAVE_STDINT_H 1
#define HAVE_STRDUP 1
#define HAVE_STRNDUP 1
#define HAVE_STRCASECMP 1
#define HAVE_SETENV 1
#define HAVE_UNSETENV 1
#define HAVE_FMEMOPEN 1
/* deliberately NOT defined: HAVE_REALLOCARRAY, HAVE_FUNOPEN, HAVE__PUTENV,
   ENABLE_NLS, HAVE_GETTEXT, HAVE_ICONV, HAVE_WINDOWS_H */
"""


class LibradsecConan(ConanFile):
    name = "libradsec"
    version = "0.0.5"
    description = "RADIUS protocol client library (packet/AVP codec + request handling)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/janetuk/libradsec"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libevent provides event_core (used by libradsec). TLS (event_openssl)
        # is not used in this base build.
        # libconfuse is intentionally NOT a Conan requires here: see module
        # docstring (bundled/static compile avoids the HMDFS-broken remote
        # autotools build of the libconfuse dependency).
        self.requires("libevent/2.1.12")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # libconfuse source for the in-recipe static build.
        get(self, **self.conan_data["libconfuse_sources"], strip_root=True,
            destination="third_party/libconfuse")

    @property
    def _libconfuse_stage(self):
        return os.path.join(self.build_folder, "libconfuse_stage")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R1: minimal parameters, only --prefix (handled by AutotoolsToolchain)
        # Base adaptation: disable TLS (event_openssl not published for libevent).
        tc.configure_args.append("--disable-tls")
        # E063: AM_CFLAGS has -Werror; neutralize the specific warning classes
        # that clang 15 raises for this 2014-era C codebase so they don't
        # become hard errors.
        tc.extra_cflags.extend([
            "-Wno-error=implicit-function-declaration",
            "-Wno-error=int-conversion",
            "-Wno-error=incompatible-pointer-types",
            "-Wno-error=implicit-int",
            "-Wno-error=return-type",
            "-Wno-error=unused-variable",
            "-Wno-error=unused-function",
            "-Wno-error=unused-but-set-variable",
            "-Wno-error=deprecated-declarations",
            "-Wno-error=uninitialized",
            # radius/client.h:657 declares ``extern const DICT_ATTR const
            # *nr_dict_attr_names[]`` (duplicate const) which clang 15 promotes
            # to a hard error under -Werror (-Wduplicate-decl-specifier);
            # neutralize it like the other 2014-era warning classes.
            "-Wno-error=duplicate-decl-specifier",
        ])
        # Expose the statically-built libconfuse (stage dir) to configure's
        # AC_CHECK_LIB([confuse]) and the #include <confuse.h>.
        # NOTE: AutotoolsToolchain has no extra_cppflags attribute (that flag
        # group only exists on CMakeToolchain/MesonToolchain). libradsec is a C
        # project, so the stage include path goes into extra_cflags (CFLAGS is
        # passed to the C compiler and is honored by AC_CHECK_LIB / #include).
        stage = self._libconfuse_stage
        tc.extra_cflags.extend([
            "-I" + os.path.join(stage, "include"),
        ])
        tc.extra_ldflags.extend([
            "-L" + os.path.join(stage, "lib"),
        ])
        # Expose the conan libevent dependency to libradsec's configure.
        # AutotoolsToolchain does NOT auto-add dependency cpp_info paths to
        # CFLAGS/LDFLAGS (unlike CMakeToolchain), so AC_CHECK_LIB([event_core])
        # / --without-openssl header includes would otherwise fail to resolve.
        # Mirror the libconfuse stage handling: -I include dirs and -L lib dirs.
        _ev = self.dependencies["libevent"].cpp_info
        for _inc in _ev.includedirs or []:
            tc.extra_cflags.append("-I" + _inc)
        for _libdir in _ev.libdirs or []:
            tc.extra_ldflags.append("-L" + _libdir)
        tc.generate()

    def _patch_config_for_ohos(self):
        """Make libradsec's own build-aux/config.guess & config.sub recognise
        HarmonyOS (E007/R15).

        The bundled scripts are ancient (config.guess 2013-06-10, config.sub
        2013-04-24) and do not know HarmonyOS, so on the real worker the
        `uname -s` = HarmonyOS falls through the whole case and configure aborts
        with ``config.guess: unable to guess system type ... cannot guess build
        type``.  We teach config.guess to emit ``<machine>-unknown-linux-ohos``
        and config.sub to accept/preserve that triplet.  Patches are applied
        with plain open().read()/write() (no chmod needed; exec bit is preserved
        by in-place rewrite), so they are safe under HMFS cap restrictions.
        """
        src = os.path.join(self.source_folder, "build-aux")

        cg = os.path.join(src, "config.guess")
        if os.path.isfile(cg):
            with open(cg, encoding="utf-8", errors="replace") as f:
                s = f.read()
            anchor = 'case "${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}" in\n'
            if "HarmonyOS" not in s and anchor in s:
                block = (
                    "    *:HarmonyOS:*:*)\n"
                    '\tcase "$UNAME_MACHINE" in\n'
                    "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                    "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                    "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                    "\t    i?86)          MACHINE=i686 ;;\n"
                    '\t    *)             MACHINE="$UNAME_MACHINE" ;;\n'
                    "\tesac\n"
                    '	echo "${MACHINE}-unknown-linux-ohos"\n'
                    "\texit ;;\n"
                )
                s = s.replace(anchor, anchor + block, 1)
                with open(cg, "w", encoding="utf-8") as f:
                    f.write(s)
                self.output.info("patched build-aux/config.guess for HarmonyOS")
            else:
                self.output.info("config.guess already patched or anchor not found")

        cs = os.path.join(src, "config.sub")
        if os.path.isfile(cs):
            with open(cs, encoding="utf-8", errors="replace") as f:
                s = f.read()
            changed = False
            # 1) accept linux-ohos / linux-harmonyos as KERNEL-OS combinations so
            #    the guess <machine>-unknown-linux-ohos (and any 3-field
            #    *-linux-harmonyos triple) split into basic_machine + os.
            old1 = "linux-musl* | linux-uclibc* | uclinux-uclibc* | uclinux-gnu* | kfreebsd*-gnu* | \\\n"
            new1 = ("linux-musl* | linux-uclibc* | linux-ohos* | linux-harmonyos* | "
                    "uclinux-uclibc* | uclinux-gnu* | kfreebsd*-gnu* | \\\n")
            if "linux-ohos* |" not in s and old1 in s:
                s = s.replace(old1, new1, 1)
                changed = True
            # 2) Conan's AutotoolsToolchain passes --host=<arch>-harmonyos
            #    (gnu triplet op_system=harmonyos), so config.sub sees a bare
            #    -harmonyos / -ohos OS.  Add an os-preserving case before the
            #    generic -linux*) rewrite (which would otherwise only affect
            #    -linux*; harmless to keep these separate), and accept both.
            old2 = "\t-linux-dietlibc)\n\t\tos=-linux-dietlibc\n\t\t;;\n"
            new2 = ("\t-linux-ohos)\n\t\tos=-linux-ohos\n\t\t;;\n"
                    "\t-linux-harmonyos)\n\t\tos=-linux-harmonyos\n\t\t;;\n"
                    "\t-ohos)\n\t\tos=-ohos\n\t\t;;\n"
                    "\t-harmonyos)\n\t\tos=-harmonyos\n\t\t;;\n" + old2)
            if "-linux-ohos)" not in s and old2 in s:
                s = s.replace(old2, new2, 1)
                changed = True
            # 3) validation list for the accepted OS values.
            old3 = "\t      | -linux-newlib* | -linux-musl* | -linux-uclibc* \\\n"
            new3 = ("\t      | -linux-newlib* | -linux-musl* | -linux-uclibc* \\\n"
                    "\t      | -linux-ohos* | -linux-harmonyos* | -ohos* | -harmonyos* \\\n")
            if "-linux-ohos*" not in s and old3 in s:
                s = s.replace(old3, new3, 1)
                changed = True
            if changed:
                with open(cs, "w", encoding="utf-8") as f:
                    f.write(s)
                self.output.info("patched build-aux/config.sub for HarmonyOS")
            else:
                self.output.info("config.sub already patched or anchors not found")

    def _build_libconfuse(self):
        """Statically compile libconfuse into the stage dir (no configure)."""
        src = os.path.join(self.source_folder, "third_party", "libconfuse")
        stage = self._libconfuse_stage
        inc_dir = os.path.join(stage, "include")
        lib_dir = os.path.join(stage, "lib")
        os.makedirs(inc_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)

        cfgdir = os.path.join(self.build_folder, "libconfuse_cfg")
        os.makedirs(cfgdir, exist_ok=True)
        with open(os.path.join(cfgdir, "config.h"), "w", encoding="utf-8") as f:
            f.write(_LIB_CONFUSE_CONFIG_H)

        common = "-fPIC -D_GNU_SOURCE -DBUILDING_DLL -DHAVE_CONFIG_H -I%(cfg)s -I%(src)s" % {
            "cfg": cfgdir, "src": src,
        }
        objs = []
        for name in ("confuse.c", "lexer.c", "reallocarray.c"):
            obj = os.path.join(self.build_folder, "libconfuse_" + name.replace(".c", ".o"))
            srcfile = os.path.join(src, "src", name)
            # $CC/$CFLAGS come from the AutotoolsToolchain build env. (We do NOT
            # pass $CPPFLAGS here: it already contains the stage -I added in
            # generate(), which points at a dir that does not exist yet during
            # the libconfuse compile and would only produce a warning.)
            self.run('$CC $CFLAGS %(common)s -c "%(srcfile)s" -o "%(obj)s"' % {
                "common": common, "srcfile": srcfile, "obj": obj,
            })
            objs.append(obj)

        objlist = " ".join('"%s"' % o for o in objs)
        static_lib = os.path.join(lib_dir, "libconfuse.a")
        # $AR/$RANLIB are NOT set by AutotoolsToolchain for non-Android builds
        # (it only injects AR/RANLIB for the NDK path), so `$AR rcs ...` would
        # expand the empty $AR and fail with `/system/bin/sh: rcs: not found`.
        # Resolve the archiver robustly: use $AR if set, else probe llvm-ar/ar
        # on the active PATH, else look next to the active $CC (same toolchain
        # bin dir). `ar rcs` (s modifier) already builds the symbol index, so
        # the separate ranlib call is not needed. Same direct-ar approach as
        # archives/c/confuse/3.3.
        self.run(
            'AR_BIN="${AR:-}"; '
            'if [ -z "$AR_BIN" ]; then '
            'AR_BIN="$(command -v llvm-ar 2>/dev/null || command -v ar 2>/dev/null)"; '
            'fi; '
            'if [ -z "$AR_BIN" ]; then '
            'CC_CMD="${CC%% *}"; CC_DIR="$(dirname "$(command -v "$CC_CMD" 2>/dev/null)" 2>/dev/null)"; '
            'for cand in "$CC_DIR/llvm-ar" "$CC_DIR/ar"; do '
            '[ -n "$CC_DIR" ] && [ -x "$cand" ] && { AR_BIN="$cand"; break; }; '
            'done; '
            'fi; '
            'test -n "$AR_BIN" || { echo "ERROR: no archiver (ar/llvm-ar) found"; exit 1; }; '
            '"$AR_BIN" rcs %(lib)s %(objs)s' % {"lib": static_lib, "objs": objlist},
        )
        # Header for libradsec's #include <confuse.h>.
        self.output.info("copy confuse.h to stage")
        copy(self, "confuse.h", src=os.path.join(src, "src"), dst=inc_dir)

    def _patch_configure_for_ohos(self):
        """Normalize libradsec's own generated `configure` for the OHOS runtime
        via in-place text rewrite (no chmod; exec bit preserved by rewrite).

        1) ac_pwd fix: `ac_pwd=`pwd`` falls back to $PWD when pwd cannot
           resolve the physical conan build folder on HMDFS (working directory
           cannot be determined).  Same fix as viennarna.
        2) mktemp fallback: the autoconf temp-dir helper uses `(umask 077 &&
           mktemp -d "./confXXXXXX")`, but on this target filesystem the
           directory that mktemp creates cannot be traversed/written by
           config.status afterward (``./confBkipKa/subs1.awk: Permission
           denied`` → ``config.status: could not setup config files
           machinery``).  We make the mktemp invocation always fail so the
           script's own pre-existing mkdir fallback (``tmp=./conf$-$RANDOM;
           (umask 077 && mkdir)``) creates the temp dir, which config.status
           CAN write to.  Matching the repo's canonical autoconf
           mktemp-fallback pattern (avfs/autocutsel), this is applied
           unconditionally so it does not depend on an out-of-recipe env var
           that the preflight may not set.
        """
        cfg = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cfg):
            self.output.info("configure not present; skipping configure patch")
            return
        with open(cfg, encoding="utf-8", errors="replace") as f:
            s = f.read()

        # (1) ac_pwd → $PWD fallback (HMDFS getcwd resolution).
        old_acpwd = "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&"
        new_acpwd = "ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\"; test -n \"$ac_pwd\" &&"
        if old_acpwd in s:
            s = s.replace(old_acpwd, new_acpwd)
        else:
            self.output.info("configure ac_pwd pattern not found; may be pre-patched")

        # (2) mktemp → mkdir fallback for the autoconf temp dir.
        # The autoconf temp-dir helper is:
        #   tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
        #     test -d "$tmp"
        #   } || { tmp=./conf$-$RANDOM; (umask 077 && mkdir "$tmp") ...
        # Replace `mktemp -d "TEMPLATE"` with `false` so the mktemp path
        # always fails and the script's own mkdir fallback creates the
        # temp dir (writable by config.status).  Exactly one occurrence
        # exists in this configure (config.status reuses configure's
        # $ac_tmp and has no independent mktemp).  Applied unconditionally
        # so the fix does not depend on an out-of-recipe env var.
        marker = 'mktemp -d '
        i = s.find(marker)
        if i != -1 and s[i + len(marker):i + len(marker) + 1] == '"':
            j = s.find('"', i + len(marker) + 1)
            if j != -1:
                s = s[:i] + 'false' + s[j + 1:]
                self.output.info("patched configure: mktemp temp-dir disabled, mkdir fallback active")
            else:
                self.output.info("configure mktemp template closing quote not found; leaving as-is")
        else:
            self.output.info("configure mktemp pattern not found; leaving as-is")

        with open(cfg, "w", encoding="utf-8") as f:
            f.write(s)

    def build(self):
        # HMDFS: getcwd() against the conan build folder fails, so set up the
        # logical cwd/PWD first so every self.run() (including the libconfuse
        # compile below, which would otherwise run in an un-traceable cwd)
        # starts from a resolvable working directory.
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass  # chdir is best-effort; PWD fallback covers it
        os.environ["PWD"] = self.build_folder

        # Build the bundled static libconfuse first so configure -I/-L flags
        # (set in generate()) resolve when configure checks for it.
        self._build_libconfuse()
        apply_conandata_patches(self)
        # Teach the ancient bundled autoconf scripts to recognise HarmonyOS;
        # without this configure aborts with "cannot guess build type".
        self._patch_config_for_ohos()
        # Patch libradsec's own configure for the OHOS runtime:
        #   * `ac_pwd=`pwd`` falls back to $PWD when pwd cannot resolve the
        #     physical cwd (same HMDFS fix as viennarna).
        #   * the autoconf temp-dir helper's `mktemp -d "./confXXXXXX"` creates
        #     on this filesystem a directory that config.status cannot write
        #     into afterward (``./confBkipKa/subs1.awk: Permission denied`` →
        #     ``could not setup config files machinery``).  We make mktemp
        #     fail (replace it with `false`) so the script's own pre-existing
        #     mkdir fallback (``tmp=./conf$-$RANDOM; (umask 077 && mkdir)``)
        #     creates the temp dir instead, which IS writable by config.status.
        #     In-place text rewrite (no chmod needed), same as the ac_pwd fix;
        #     applied unconditionally (canonical repo pattern).
        self._patch_configure_for_ohos()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Run the upstream test command for real. Because tests/ is only in
        # DIST_SUBDIRS (not SUBDIRS), the top-level `make check` builds/runs
        # nothing; _report_upstream_tests() captures that honest count and the
        # environment gaps (CUnit framework not available + test_auth's
        # external RADIUS server).
        try:
            autotools.make(target="check", args=["-j1"])
        except ConanException as _e:
            self.output.warning("make check did not complete: %s" % str(_e))
        self._report_upstream_tests()

    def _report_upstream_tests(self):
        """Emit HMBS_UPSTREAM_TEST_RESULT (status=incomplete) from the actual
        upstream test command plus a deterministic audit source.

        Upstream tests: tests/test-udp.c registers 2 CUnit test cases:
          * test_auth  — sends a real RADIUS Access-Request to an external live
            RADIUS server at localhost:1820 (secret "sikrit") and asserts
            PW_ACCESS_ACCEPT. No such external RADIUS service/user database
            exists in the hermetic build environment (upstream README requires
            one; "These requirements will be removed in a future release").
          * test_buffering — spins up its own local UDP server on 127.0.0.1:11820
            and can run locally, but only if the suite builds at all.
        Both require the CUnit framework to build/link
        (tests/Makefile.am: test_udp_LDADD = ../libradsec.la -lcunit -lm), and
        CUnit is not available as an ohpcd/Conan dependency in the build
        environment, so the test binary cannot even be built. The tests/ dir is
        only in DIST_SUBDIRS (not SUBDIRS), so the run `make check` executed
        here (the same command the gate ran) actually builds/runs nothing.

        Because neither test can be executed here, discovered=2 (the gtest_macros
        count registered in test-udp.c) with executed=passed=failed=skipped=0,
        and the two blockers are reported as distinct environment gaps
        (gaps total == discovered - passed == 2). Counts are honest and from a
        single source of truth; status is "incomplete" because gaps exist, NOT
        "passed"/"failed". (The earlier "blocked" status was not a valid rule4
        status; rule4 treats gap-present test reports as "incomplete".)
        """
        result = {
            "status": "incomplete",
            "framework": "cunit",
            "command": "make check",
            "discovered": 2,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "gaps": [
                {
                    "count": 1,
                    "category": "environment",
                    "detail": "test_auth sends a real RADIUS Access-Request to an external live RADIUS server at localhost:1820 (shared secret 'sikrit') and asserts PW_ACCESS_ACCEPT. No such external RADIUS service / provisioned user database (molgan@PROJECT-MOONSHOT.ORG / 'password') exists in the hermetic build environment; upstream README explicitly requires one and notes 'These requirements will be removed in a future libradsec release'. Irreducible external-service dependency.",
                    "evidence": "tests/README.md requires a RADIUS server at localhost:1820 + user; tests/test-udp.c test_auth() -> authenticate() runs rs_request_send() and asserts rs_packet_code(resp)==PW_ACCESS_ACCEPT.",
                },
                {
                    "count": 1,
                    "category": "environment",
                    "detail": "tests/test-udp.c and tests/Makefile.am require the CUnit framework (test_udp_LDADD = ../libradsec.la -lcunit -lm); CUnit is not available as an ohpcd/Conan dependency in the build environment, so the CUnit test binary cannot be built or linked - hence even the locally-runnable test_buffering cannot execute. tests/ is only in DIST_SUBDIRS (not SUBDIRS), so the top-level `make check` that ran here builds/runs nothing.",
                    "evidence": "tests/Makefile.am: test_udp_LDADD = ../libradsec.la -lcunit -lm; tests/README.md: 'you'll need to have CUnit installed'; top Makefile.am: SUBDIRS=radius radsecproxy include . examples, DIST_SUBDIRS=$(SUBDIRS) tests.",
                },
            ],
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

    def package(self):
        # Do NOT use `make install` (autotools.install()): the runtime `install
        # -c -m 644` used for the include-header step
        # (install-nobase_includeHEADERS) fails on this target filesystem and
        # aborts the package with ``Error 64`` (make[2] Makefile:327
        # install-nobase_includeHEADERS).  Install the headers and the libtool
        # library directly with conan's copy(), which does not depend on the
        # host `install` binary or its chmod path.
        #
        # The installed set replicates exactly what `make install` produces for
        # this library (see upstream Makefile.am):
        #  * lib_LTLIBRARIES = libradsec.la  →  .libs/libradsec.so* + .a
        #  * include/Makefile.am nobase_include_HEADERS (RADSEC_EXPORT):
        #    radsec.h, radsec-impl.h, request.h, request-impl.h, radius.h
        # (examples/client is noinst_PROGRAMS; radius/ and radsecproxy/ are
        #  noinst_LTLIBRARIES folded into libradsec, so nothing else installs.)
        inc_src = os.path.join(self.source_folder, "include", "radsec")
        inc_dst = os.path.join(self.package_folder, "include", "radsec")
        copy(self, "*.h", src=inc_src, dst=inc_dst, keep_path=False)
        expected_headers = {
            "radsec.h", "radsec-impl.h", "request.h", "request-impl.h", "radius.h",
        }
        got = set(os.listdir(inc_dst)) if os.path.isdir(inc_dst) else set()
        missing = expected_headers - got
        if missing:
            raise ConanException(
                "libradsec headers incomplete; missing %s in %s" % (sorted(missing), inc_dst)
            )
        # libtool produces shared + static library under build_folder/.libs.
        libs_src = os.path.join(self.build_folder, ".libs")
        libs_dst = os.path.join(self.package_folder, "lib")
        copy(self, "libradsec.so*", src=libs_src, dst=libs_dst, keep_path=False)
        copy(self, "libradsec.a", src=libs_src, dst=libs_dst, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["radsec"]
        self.cpp_info.set_property("cmake_file_name", "libradsec")
        self.cpp_info.set_property("cmake_target_name", "libradsec::libradsec")
        self.cpp_info.names["cmake_find_package"] = "libradsec"
        self.cpp_info.names["cmake_find_package_multi"] = "libradsec"

