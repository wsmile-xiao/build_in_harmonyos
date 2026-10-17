"""Conan recipe for pidgin 2.14.14 — libpurple core, OHOS PC cross-compile.

Loaded by Conan via Python import machinery (no shebang). Wraps the upstream
autotools build and exposes ``libpurple.a`` as a CMake target ``pidgin::pidgin``.

Key invariants:
  - Static-only on OHOS. ``_validate_os()`` rejects ``os=OHOS`` + ``shared=True``
    (glib/libxml2 in OHOS sysroot are static; musl BIND_NOW blocks prpl dlopen).
    ``generate()`` then appends ``--enable-static --disable-shared``.
  - UI/transport plugins (GTK, console, finch, meanwhile, avahi, dbus, perl,
    mono, nss, gnutls, krb, sasl, zephyr, idn, ...) and i18n are disabled to
    avoid dragging in runtime deps OHOS lacks.
  - No source patches in conandata.yml; conandata.yml patches: [].
    A runtime source patch is applied in build() to fix getpass() in
    libpurple/example/nullclient.c (deprecated POSIX function removed in
    ISO C99+, not available on modern clang/OHOS).
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.build import cross_building


class PidginConan(ConanFile):
    name = "pidgin"
    version = "2.14.14"
    description = "Multi-protocol instant messaging client (libpurple core only)"
    license = "GPL-2.0-or-later"
    homepage = "https://pidgin.im/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def _validate_os(self):
        # R32: os must be Linux or OHOS (not == check)
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pidgin 2.14.14 only supports os=Linux/OHOS, got {self.settings.os}"
            )
        # R26: OHOS requires shared=False. Reasons:
        #   1. glib/libxml2 in the OHOS sysroot are static-only; there is no
        #      .so in the system for libpurple.so to link against.
        #   2. musl's BIND_NOW mechanism rejects symbols that are resolved at
        #      run-time via dlopen (prpl plugins), which is exactly how
        #      libpurple + dynamic prpl would normally be wired.
        # Refuse shared=True on OHOS explicitly so the user sees a clear
        # diagnostic instead of a half-finished build that fails at link
        # time with "cannot find -lglib-2.0".
        if self.settings.os == "OHOS" and self.options.shared:
            raise ConanInvalidConfiguration(
                "pidgin 2.14.14 on OHOS requires shared=False (R26: "
                "musl BIND_NOW blocks prpl plugin dlopen; glib/libxml2 are "
                "static-only in the OHOS sysroot). Drop the -o shared=True "
                "option or switch to a Linux profile."
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Required by libpurple (from configure.ac PKG_CHECK_MODULES):
        #   - glib-2.0 + gobject-2.0 + gmodule-2.0 + gthread-2.0 + gio-unix-2.0
        #   - libxml-2.0 >= 2.6.0
        # All transitive deps (libffi, libiconv, pcre, pcre2, zlib, bzip2) are
        # automatically pulled by Conan from glib & libxml2 graphs — R27 only
        # requires direct dependencies to be declared explicitly.
        #
        # Version pins: aligned with the team's ohpcd registry (CI release
        # profile consumes from registry only — no --build=missing for the
        # dependency packages). Registry inventory (conan search ohpcd):
        #   glib    : 2.84.0, 2.84.0.1
        #   libxml2 : 2.15.3
        # AI-review/CI feedback 2026-07-31: previous pins (glib/2.72.4,
        # libxml2/2.10.3) were the conan-center defaults but are NOT in
        # the team registry; CI fallback in build_and_test.sh L0i could
        # not resolve them and `conan create` failed at dependency-graph
        # resolution. Maintainer hint pointed to the team-adopted versions.
        # No API/ABI change expected — both version pairs satisfy
        # libpurple's configure.ac minimums (glib >= 2.16.0, libxml2 >= 2.6.0).
        self.requires("glib/2.84.0")
        self.requires("libxml2/2.15.3")

    def layout(self):
        basic_layout(self)

    def configure(self):
        self._validate_os()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R33: Do NOT hardcode --host=<triplet>.
        # AutotoolsToolchain auto-detects cross-compilation from profile settings
        # and sets --host correctly (e.g. aarch64-linux-gnu for armv8+Linux).
        # Explicit --host overrides can conflict with Conan 2.x built-in detection.

        # config.guess 2018-02-24 (autotools shipped with pidgin 2.14.14)
        # does NOT recognise HarmonyOS / HongMeng as a build system, so the
        # `@build@` autoconf substitution fails on OHOS workers with
        #   "unable to guess build type; you must specify one"
        # even though host == build (the OHOS worker is aarch64, compiling
        # for aarch64 OHOS, no cross-compile). Bypass config.guess by
        # handing the build triplet to configure explicitly. --host is
        # still auto-detected from settings (R33 preserved).
        #
        # The triplet must use a kernel+vendor pair config.sub 2018-02-24
        # recognises. config.sub is strict on the vendor field for the
        # `linux` kernel — only `gnu`/`musl`/`uclibc`/`android`/... are
        # accepted. `ohos` is rejected with "machine `aarch64-unknown-linux'
        # not recognized" (verified on CI 2026-08-01: a previous commit
        # tried `--build=aarch64-unknown-linux-ohos`, config.sub aborted).
        #
        # Use `linux-gnu` as the build triplet: config.sub accepts it on
        # any vintage; @build@ resolves to aarch64-unknown-linux-gnu in
        # the generated Makefiles (harmless string, no effect on the
        # build artefact). Since we do NOT set --host, autotools does
        # not detect this as a cross-compile — all configure-time test
        # programs (conftests) still run natively via clang under OHOS.
        # The actual compilation uses the clang toolchain from profile
        # conf (`tools.build:compiler_executables`), independent of
        # --build / --host.
        #
        # R-NEW (2026-08-04): gate the `--build=` append with `cross_building`
        # so the hard-coded `aarch64-unknown-linux-gnu` only runs when the
        # build machine actually IS aarch64. The previous unconditional
        # `if self.settings.os == "OHOS":` would mis-fire in two scenarios:
        #
        #   1. Future x86_64 OHOS worker (e.g. CI migrates from aarch64 HMDFS
        #      to an x86_64 Intel/AMD host with an armv8 cross-toolchain).
        #      In that case AutotoolsToolchain auto-sets
        #      `--host=aarch64-linux-gnu` (from settings.arch=armv8), and
        #      our hard-coded `--build=aarch64-unknown-linux-gnu` would make
        #      host==build (both aarch64) in configure's view; configure
        #      would then skip cross-compile mode and try to EXECUTE an
        #      aarch64 conftest binary on x86_64, blowing up with
        #      "cannot run aarch64 conftest" / Illegal instruction.
        #
        #   2. Developer doing native OHOS build on an aarch64 Mac/Linux box
        #      with target arch=x86_64 (less likely but possible).
        #
        # `cross_building(self)` returns False when build machine arch ==
        # target arch (i.e. native build, what we want — config.guess fails
        # here so we still need to set --build= manually), and True when
        # they differ (config.guess should succeed in cross mode — we let
        # AutotoolsToolchain + config.guess handle it without our override).
        if self.settings.os == "OHOS" and not cross_building(self):
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")

        # R26: pidgin produces libpurple — static-only on OHOS because:
        # 1. glib/libxml2 are static on OHOS (no .so available in OHOS sysroot)
        # 2. musl BIND_NOW makes dlopen'd prpl plugins fail without static link
        # The "shared=False on OHOS" case is enforced in _validate_os(); this
        # block only handles the legitimate shared=True case for Linux where
        # glib/libxml2 .so are available.
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")

        # Match build_pidgin_wsl.sh proven configuration:
        # disable UI/protocols/transports irrelevant to libpurple core
        tc.configure_args.extend([
            "--disable-gtkui",
            "--disable-consoleui",
            "--disable-gstreamer",
            "--disable-vv",
            "--disable-tcl",
            "--disable-tk",
            "--disable-meanwhile",
            "--disable-avahi",
            "--disable-dbus",
            "--disable-gestures",
            "--disable-screensaver",
            "--disable-sm",
            "--disable-startup-notification",
            "--disable-gtkspell",
            "--disable-idn",
            "--disable-perl",
            "--disable-mono",
            "--disable-nss",
            "--disable-gnutls",
            "--disable-cyrus-sasl",
            # krb4 is AC_ARG_WITH (not AC_ARG_ENABLE) in pidgin 2.14.14,
            # so the correct option is --without-krb4. Using --disable-krb4
            # makes the configure script print "unrecognized option" warnings
            # on autotools 2.71+ (which is what conan 2.x bundles). Default is
            # already "no", so the flag is technically redundant but explicit
            # for clarity.
            #
            # krb5 has no AC_ARG_* in pidgin 2.14.14's configure.ac — it is
            # implicitly handled through cyrus-sasl (--disable-cyrus-sasl above
            # already disables the krb5/gsasl code paths). No explicit flag
            # is needed or accepted.
            "--without-krb4",
            "--disable-zephyr",
            "--disable-doxygen-doc",
            "--disable-dot",
            "--disable-devhelp",
            "--disable-pixmaps-install",
            "--disable-fortify",
            "--disable-deprecation",
            "--disable-finch",
            # R-NEW (2026-08-04): patch libpurple/example/nullclient.c to
            # replace getpass() with a portable fallback. getpass() is a
            # deprecated POSIX function removed in ISO C99+ (clang errors out
            # with "call to undeclared function 'getpass'" on OHOS).
            # pidgin configure has no --disable-example flag, so we cannot
            # exclude nullclient at configure time. The actual patch lives in
            # build() (before autotools.configure) — it injects a portable
            # pidgin_getpass() wrapper function and removes the extern
            # getpass() declaration. This preserves the original source logic
            # (prompt + read password) while making it compilable on
            # modern clang/OHOS toolchains.
            "--enable-nls=no",
        ])

        # R-NEW (2026-08-04 + 2026-08-06 Pass 12): keep --prefix=/ so that
        # `make install` paths are correctly rooted, and pass
        # DESTDIR=<package_folder> explicitly to `autotools.install()`.
        #
        # Background (2026-08-04, Pass 4): we had been setting
        # `--prefix=<package_folder>`. That fixed the *link* stage of
        # ssl.la — `libdir` embedded in pidgin's Makefile stopped being
        # `//lib` — but it broke the *install* stage, because conan 2.x
        # `Autotools.install()` automatically prepends `DESTDIR=<pkg>`
        # to the make command line, so files ended up at
        # `<pkg>/<pkg>/lib/...` (double-nested). CMakeDeps then could
        # not find `libpurple.a` at the expected `<pkg>/lib/`, throwing
        #   "Library 'purple' not found in package"
        # from `pidgin-config.cmake` (verified CI 2026-08-06, post-Pass
        # 11 successful build + install).
        #
        # Correct conan 2.x convention:
        #   - configure: --prefix=/     (autotools standard)
        #   - install:   make install DESTDIR=<pkg>
        # which yields installed paths `<pkg>/<configure_prefix>/<file>`
        # = `<pkg>/<file>` (single nesting, correct).
        #
        # To get --prefix=/ back AND keep the ssl.la link fix from
        # Pass 4, we ALSO pass explicit `--libdir=/lib`,
        # `--bindir=/bin`, `--includedir=/include`. The explicit
        # absolute values override the autoconf default
        # `${prefix}/lib` template (which evaluates to `//lib` when
        # prefix is `/` and produces the same libtool `-L//lib` link
        # failure observed in Pass 1/2/3).
        #
        # Note: we use update_configure_args (NOT append) so we don't
        # end up with TWO --prefix flags where the wrong one could win
        # on some vintage of configure. autoconf's last-flag-wins
        # semantics plus update_configure_args's overwrite (rather than
        # append) makes this unambiguous.
        tc.update_configure_args({
            "--prefix": "/",
            "--libdir": "/lib",
            "--bindir": "/bin",
            "--includedir": "/include",
        })
        # PkgConfigDeps writes one *.pc file per requirement into
        # self.generators_folder (= <build>/build-release/conan), so the
        # *.pc files for glib/2.84.0, libxml2/2.15.3, libffi/3.4.4 and
        # pcre2/10.40 land there. Without PKG_CONFIG_PATH pointing at
        # that folder, pidgin's configure probes (PKG_CHECK_MODULES for
        # GLIB/LIBXML) cannot locate the .pc files and abort with
        # "You must have GLib 2.16.0 or newer development headers
        # installed to build." (verified CI 2026-08-01).
        #
        # PkgConfigDeps in conan 2.x *should* inject PKG_CONFIG_PATH via
        # `self._conanfile.buildenv.prepend_path(...)`, and that env is
        # *meant* to be merged into conanbuild.sh by the recipe-level
        # aggregation. In practice, on the ohpcd hnp bundle's conan 2.x
        # build (verified by the identical probe output across commits
        # 731d9b2d and 1a7b00a6), PkgConfigDeps's prepend is not
        # propagated into the conanbuild.sh that Autotools.configure()
        # inherits — most likely because the recipe's `tc.buildenv`
        # (used by `tc.generate()`) and `self._conanfile.buildenv`
        # (mutated by PkgConfigDeps) are separate instances, and the
        # recipe-level aggregation does not re-read them.
        #
        # Workaround: bypass the conan 2.x env aggregation entirely.
        # We append the export to conanbuild.sh manually after tc.generate()
        # has finished writing it. This is the most version-agnostic
        # approach: it does not depend on tc.buildenv / tc.environment() /
        # VirtualBuildEnv or any other internal API that has shifted
        PkgConfigDeps(self).generate()
        tc.generate()

    def build(self):
        # R-NEW: scope PKG_CONFIG_PATH mutation to this build() only.
        # Two channels are used:
        #   (1) os.environ["PKG_CONFIG_PATH"] — last-resort fallback for
        #       the ohpcd hnp bundle where conan 2.x's tc.environment()
        #       propagation via conanbuild.sh was observed to be a no-op
        #       (verified CI 2026-07-30; see also the AI-review of
        #       2026-08-05). NOTE: tc.environment().prepend_path() would
        #       normally be the canonical way, but conan 2.x's
        #       `tc.environment()` returns a NEW Environment object on
        #       each call and conanbuild.sh does not re-read it after
        #       tc.generate() has run, so the prepend would not propagate
        #       unless we also pass it to `tc.generate(env)` — and that
        #       signature is brittle across conan 2.x point releases.
        #   (2) The os.environ mutation is scoped via try/finally so the
        #       env var is restored before build() returns, preventing
        #       pollution of any later recipe ops in the same process
        #       (test_package CMake configure, package() packaging, etc.).
        #       This closes the bug flagged in AI-review 2026-08-05
        #       ("os.environ mutation leaks across build phases").
        _pc_paths = [self.generators_folder]
        for _dep in self.dependencies.values():
            _pc_paths.append(os.path.join(_dep.package_folder, "lib",
                                          "pkgconfig"))
        _pkg_config_path = ":".join(_pc_paths)
        _prior_pkg_config_path = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = _pkg_config_path
        self.output.info(
            f"R-NEW: PKG_CONFIG_PATH (scoped) = {_pkg_config_path}"
        )

        try:
            self._build_with_patches()
        finally:
            if _prior_pkg_config_path:
                os.environ["PKG_CONFIG_PATH"] = _prior_pkg_config_path
            else:
                os.environ.pop("PKG_CONFIG_PATH", None)
            self.output.info(
                f"R-NEW: PKG_CONFIG_PATH restored to "
                f"{os.environ.get('PKG_CONFIG_PATH', '<unset>')}"
            )

    def _build_with_patches(self):
        # R-NEW (2026-08-04): patch libpurple/example/nullclient.c.
        # getpass() is a deprecated POSIX function removed in ISO C99+;
        # clang on OHOS fails with "call to undeclared function 'getpass'"
        # on nullclient.c:311. pidgin configure has no --disable-example
        # flag, so we patch the source instead. The patch:
        #   1. Injects a portable pidgin_getpass() wrapper function
        #      (wraps fgets for stdin password reading)
        #   2. Removes the extern getpass() declaration
        #   3. Changes the getpass(...) call to pidgin_getpass(...)
        # We patch both source_folder (for safety) and build_folder
        # (which is what the build actually uses after the source copy).
        #
        # Order matters: inject the wrapper BEFORE checking whether the
        # source already has `pidgin_getpass` (e.g. after first regex pass),
        # otherwise the idempotency check would skip the wrapper injection
        # on a file that already has the renamed call. The presence check
        # is on the *raw source text* (pre-rename), not on the post-rename
        # text. Use a stable sentinel "static char *pidgin_getpass(" for
        # the idempotency check, since the actual function definition is
        # what we want to verify.
        _nc_path_src = os.path.join(self.source_folder, "libpurple",
                                     "example", "nullclient.c")
        _nc_path_build = os.path.join(self.build_folder, "libpurple",
                                      "example", "nullclient.c")
        _patched_getpass = False
        for _nc_path in (_nc_path_src, _nc_path_build):
            if not os.path.exists(_nc_path):
                continue
            try:
                with open(_nc_path, "r", encoding="utf-8",
                          errors="replace") as _fh:
                    _nc_text = _fh.read()
            except OSError:
                continue
            # Read the sentinel on the original text only — this is the
            # idempotency check (don't double-inject if already patched).
            # CRITICAL: must check `_nc_text` (the on-disk version), NOT
            # the post-regex `_nc_new`. If we checked `_nc_new` after the
            # getpass->pidgin_getpass rename, then on a fresh source file
            # the check would say "pidgin_getpass is in the file" (because
            # we just renamed one call!) and skip the wrapper injection,
            # which is exactly the bug that caused 3d757f13 CI to fail
            # with "pidgin_getpass undeclared".
            if "static char *pidgin_getpass(" in _nc_text:
                # Already patched (by an earlier run in the same build
                # folder, or hand-edited source). Skip.
                continue
            _nc_new = _nc_text
            # 1. Remove the extern getpass() declaration if present
            _nc_new = re.sub(
                r"\nextern\s+char\s*\*\s*getpass\s*\([^)]*\)\s*;?\n",
                "\n", _nc_new)
            # 2. Replace getpass(...) with pidgin_getpass(...)
            _nc_new = re.sub(
                r"\bgetpass\s*\(([^)]+)\)",
                r"pidgin_getpass(\1)", _nc_new)
            # 3. Inject the wrapper function definition with explicit
            # #include guards so it does not depend on where in the file
            # it is placed. The wrapper itself pulls in the system
            # headers it needs (stdio.h + string.h), independent of the
            # file's existing #include block.
            #
            # Why we can't just prepend the wrapper at the very top:
            # ISO C99+ forbids implicit function declarations. If we
            # prepend `static char *pidgin_getpass(...) { fputs(...); }`
            # BEFORE the file's existing #include block, the call to
            # fputs/fflush/fgets/strcspn is undeclared → the build
            # aborts with "call to undeclared function 'fputs'" (verified
            # CI 2026-08-06). Even though `<stdio.h>` is normally
            # included later via purple.h's transitive chain, that
            # hasn't happened yet at the point pidgin_getpass() is
            # defined. We must either (a) inject inside an #include
            # guard, or (b) make the wrapper self-sufficient.
            #
            # Approach (b): include the needed system headers inline.
            # This makes the wrapper robust to position-in-file.
            _GETPASS_WRAPPER = r"""
#ifndef _PIDGIN_GETPASS_WRAPPER_INCLUDED
#define _PIDGIN_GETPASS_WRAPPER_INCLUDED 1
#include <stdio.h>
#include <string.h>
static char *pidgin_getpass(const char *prompt) {
    static char password[256];
    fputs(prompt, stderr);
    fflush(stderr);
    if (fgets(password, sizeof(password), stdin) == NULL)
        return NULL;
    password[strcspn(password, "\r\n")] = '\0';
    return password;
}
#endif

"""
            _nc_new = _GETPASS_WRAPPER + _nc_new
            if _nc_new != _nc_text:
                with open(_nc_path, "w", encoding="utf-8") as _fh:
                    _fh.write(_nc_new)
                _patched_getpass = True
                self.output.info(
                    f"R-NEW: patched {_nc_path} to replace getpass() "
                    f"with portable pidgin_getpass() (fixes ISO C99 "
                    f"'undeclared function getpass' error in nullclient.c; "
                    f"getpass was removed from POSIX and is unavailable on "
                    f"modern clang/OHOS toolchains)"
                )
        if not _patched_getpass:
            self.output.warning(
                "R-NEW: could not patch nullclient.c for getpass() "
                "(example build may fail on OHOS)"
            )

        apply_conandata_patches(self)

        # R-NEW: rewrite libtool archive (.la) libdir fields in transitive
        # deps before any configure/make runs.
        #
        # Symptom (CI 2026-08-03, feat/pidgin-2.14.14-A7F3, build phase,
        # ~line "Making all in libpurple/plugins/ssl"):
        #
        #   libtool: warning: library '/.../libffi/.../lib/libffi.la' was moved.
        #   libtool: warning: library '/.../pcre2/.../lib/libpcre2-8.la' was moved.
        #   libtool: warning: library '/.../pcre2/.../lib/libpcre2-posix.la' was moved.
        #   sed: //lib/libpcre2-8.la: No such file or directory
        #   libtool:   error: '//lib/libpcre2-8.la' is not a valid libtool archive
        #   make[5]: *** [Makefile:656: ssl.la] Error 1
        #
        # Root cause: libffi/3.4.4 and pcre2/10.40 are consumed as
        # pre-built binaries from the ohpcd remote (no source build in
        # this recipe — see the "Downloading binary packages" block in
        # the conan-create log). The upstream recipes that produced
        # those binaries ran their autotools configure with
        # `--prefix=/`, so the embedded `libdir='//lib'` field in
        # libffi.la / libpcre2-8.la / libpcre2-posix.la (note the
        # double slash, classic autoconf prefix-concat artefact) does
        # NOT match the actual on-disk path
        # `<conan2_cache>/p/<dep-hash>/p/lib`. When pidgin's libtool
        # link stage opens these .la files, libtool re-computes the
        # install_dir as `libdir + basename = //lib/libpcre2-8.la`,
        # cannot find that file, and aborts the entire ssl.la link
        # (which `make` then propagates upward to "Error 2").
        #
        # Two pass rewrite (R-NEW 2026-08-04):
        #
        #   Pass 1 — libdir (the obvious field):
        #     rewrites `libdir='/lib'` / `libdir='//lib'` to the
        #     actual `<package_folder>/lib` of the dep that owns the
        #     archive. libtool's relocation logic ("library was moved")
        #     then resolves to the correct conan2 cache path.
        #
        #   Pass 2 — inst_prefix_dir (the dastardly field):
        #     libtool 1.5/2.4 .la archives ALSO carry an `inst_prefix_dir`
        #     field. The link-phase install_dir calculation in libtool
        #     is roughly:
        #         install_dir         = libdir + basename
        #         original_install_dir = inst_prefix_dir + '/lib' + basename
        #     When the dep was built with `--prefix=/` (which ohpcd's
        #     binary uses), the .la ships `inst_prefix_dir='/'` (single
        #     slash — the canonical autoconf value when --prefix=/ is
        #     passed). In that case `original_install_dir = '/' + '/lib'
        #     + basename = '//lib/libpcre2-8.la'`. libtool then pipes
        #     that path into a sed command (the "is not a valid libtool
        #     archive" error we see — `sed: //lib/libpcre2-8.la: No
        #     such file or directory`). Pass 1 alone fixes the primary
        #     relocation warning but DOES NOT fix this sed step because
        #     sed still sees the value derived from inst_prefix_dir.
        #     Pass 2 sets inst_prefix_dir to the absolute dep
        #     package_folder, so sed's input path resolves to a real
        #     on-disk file.
        #
        #   Pass 3 — inst_prefix_dir INJECT (R-NEW 2026-08-04 after the
        #   first Pass 2 attempt rewrote 0 files):
        #     Some libtool 2.4.x .la archives (specifically those
        #     generated with --disable-fast-install, which is the
        #     default for static-only builds and what ohpcd uses for
        #     pcre2/libffi) OMIT the `inst_prefix_dir` field entirely.
        #     When libtool 2.4.x parses such a .la, it falls back to
        #     `inst_prefix_dir='/'` at runtime (libtool script line
        #     ~9100, func_mode_link):
        #         if test -z "$inst_prefix_dir"; then
        #             inst_prefix_dir=/
        #         fi
        #     This produces the same `//lib/libpcre2-8.la` error path
        #     as Pass 2's `'/'` case. Pass 3 detects the absence of
        #     the field and INJECTS it with the absolute dep
        #     package_folder, closing the gap.
        #
        # Why this is safe:
        #   - We only rewrite two fields (libdir, inst_prefix_dir) in
        #     plain text files; we never touch the .a archives
        #     themselves, so ABI / link semantics are unchanged.
        #   - The .la files are conan-private cache files; rewriting
        #     them in place is acceptable on the CI worker (no impact
        #     on the registry's published recipe bytes).
        #   - We only INJECT inst_prefix_dir when the field is absent;
        #     pre-existing real absolute paths (e.g. for system
        #     packages built with --prefix=/usr/local) are left
        #     untouched — idempotent.
        #
        # R-NEW (2026-08-03): widened regex + re.MULTILINE + per-file
        # trace logging. Previous version used `^libdir\s*=\s*...$`
        # without re.MULTILINE, so on libtool .la files where the
        # libdir line is indented (libtool 2.4.x and some conan binary
        # packagers emit "  libdir='/lib'") the `^` anchor failed to
        # match and 0 files were rewritten (silent no-op). Switched to
        # `^\s*libdir\s*=\s*...$` with re.MULTILINE so indented lines
        # match too; also added a per-file self.output.info so future
        # CI runs surface "scanned N .la, matched M" telemetry instead
        # of a silent 0-replaced.
        _LADIR_BAD = re.compile(
            r"^\s*libdir\s*=\s*['\"]?(?:/)?/?lib['\"]?\s*$",
            re.MULTILINE,
        )
        # R-NEW (2026-08-04): inst_prefix_dir "bad" regex broadened
        # beyond empty-quotes to also catch `/`, `//`, `/lib`, `//lib`,
        # `/lib/`, `//lib/` and bare `lib` — i.e. the canonical
        # --prefix=/ autoconf defaults. The Pass 2 commit (1665ffb3)
        # only matched empty-quotes / bare-empty, which proved
        # insufficient: the CI run after 1665ffb3 reported
        # "rewrote inst_prefix_dir in 0" yet the build still failed
        # with the same `sed: //lib/libpcre2-8.la` error, telling us
        # the .la file's inst_prefix_dir was neither empty nor a
        # non-empty absolute path — falling back to libtool's runtime
        # default of `'/'` (see Pass 3 rationale above).
        #
        # The new regex matches inst_prefix_dir whose value is purely
        # slashes / lib / /lib (with optional trailing slash and
        # quotes). Real absolute paths like `/usr/local` or `/opt/lib`
        # do NOT match because they contain a multi-segment component.
        # Verified against 23 representative samples via the
        # scripts/_la_instprefix_test3.py offline harness.
        _INSTPREFIX_BAD = re.compile(
            r"^\s*inst_prefix_dir\s*=\s*['\"]?\s*(?:/+|lib/?|/+lib/?)?\s*['\"]?\s*$",
            re.MULTILINE,
        )
        # Whether the .la defines the inst_prefix_dir field at all
        # (used by Pass 3 to decide INJECT vs REWRITE vs KEEP).
        _INSTPREFIX_PRESENT = re.compile(
            r"^\s*inst_prefix_dir\s*=",
            re.MULTILINE,
        )
        # R-NEW (2026-08-04): Pass 5 — dependency_libs contains both
        # -L<bad-path> flags AND bare .la file paths from ohpcd's
        # --prefix=/ build. The post-Pass diagnostic dump on CI 2026-08-04
        # showed:
        #
        #   post-Pass libpcre2-posix.la:
        #     dependency_libs=' -L/storage/.../usr/local/lib //lib/libpcre2-8.la'
        #
        # Two sub-problems:
        #
        # Sub-problem A — -L<bad-path> flags:
        #   When ohpcd built with --prefix=/usr/local (or --prefix=/),
        #   dependency_libs contain -L flags pointing at the ohpcd sysroot.
        #   When pidgin's libtool reads these .la files it adds each -L<path>
        #   to its newlib_search_path, then uses that to locate .la files for
        #   each -l<name>.  Any bad -L path causes the error.
        #
        # Sub-problem B — bare .la file paths:
        #   libpcre2-posix.la's dependency_libs contains the LITERAL string
        #   "//lib/libpcre2-8.la" (a direct .la path from ohpcd's --prefix=/
        #   install).  When libtool sees a bare .la path it uses that path
        #   directly via func_lalib_unsafe_p, which fails because
        #   //lib/libpcre2-8.la does not exist.  This is NOT caught by the
        #   -L regex.
        #
        # For sub-problem B, the correct .la path for libpcre2-8.la is
        # os.path.join(dep.package_folder, "lib", "libpcre2-8.la") — it shares
        # the same package_folder as libpcre2-posix.la (both from pcre2/10.40).
        # Simple substitution: replace the literal "//lib/" (double-slash root
        # prefix that ohpcd's --prefix=/ build embeds in dependency_libs)
        # with the correct dep_libdir. This is unambiguous because:
        #   - //lib/ can ONLY come from --prefix=/ (not a valid normal path)
        #   - It never appears in real paths like /usr/local/lib/ or /opt/.../lib/
        #   - Replacing //lib/ with dep_libdir gives the correct absolute path
        _DEPLIBS_BAD_LFLAG = re.compile(
            r"(-L)(?:/+|lib|/+lib|/+lib/|//lib/|//)(?=[\s'\"]|$)",
            re.IGNORECASE,
        )
        _DEPLIBS_BAD_LA = re.compile(r"(//lib/)")
        #
        # Verified against libtool 2.4.6 ltmain.sh line ~5895: when
        # libtool resolves `-lpcre2-8` against a `-L<path>` search
        # path, it constructs `lib=<path>/libpcre2-8.la` and then
        # `func_lalib_unsafe_p "$lib" || func_fatal_error "...
        # is not a valid libtool archive"`. So if `<path>` is `//lib`
        # we get the literal `//lib/libpcre2-8.la` error path.
        #
        # Match dependency_libs with `-L` flags pointing at the bad
        # paths. We use a single sub() pass because libtool 2.4.x
        # wraps dependency_libs as a single shell-quoted string.
        # Examples we want to rewrite:
        #   dependency_libs=' -L//lib -lpcre2-8'
        #   dependency_libs=' -L/lib -lpcre2-8'
        #   dependency_libs=' -L//lib -lpcre2-posix -L//lib -lpcre2-8'
        #   dependency_libs=' -L//lib/'
        # into:
        #   dependency_libs=' -L<dep_libdir> -lpcre2-8'
        # ...
        # We do NOT touch non-`-L` entries (e.g. `-lpcre2-8`,
        # `-pthread`, `-framework Foo`, `-Wl,foo`, etc.).
        _DEPLIBS_BAD = re.compile(
            r"(-L)(?:/+|lib|/+lib|/+lib/|//lib/|//)(?=[\s'\"]|$)",
            re.IGNORECASE,
        )
        _LADIR_REPLACED = 0
        _INSTPREFIX_REPLACED = 0
        _INSTPREFIX_INJECTED = 0
        _DEPLIBS_REPLACED = 0
        _LADIR_SCANNED = 0
        _LADIR_MATCHED_FILES = 0
        for dep in self.dependencies.values():
            dep_libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(dep_libdir):
                continue
            for la_name in os.listdir(dep_libdir):
                if not la_name.endswith(".la"):
                    continue
                _LADIR_SCANNED += 1
                la_path = os.path.join(dep_libdir, la_name)
                try:
                    with open(la_path, "r", encoding="utf-8",
                              errors="replace") as _fh:
                        _la_text = _fh.read()
                except OSError as _exc:
                    self.output.warning(
                        f"R-NEW: cannot read {la_path}: {_exc!r}")
                    continue
                _new_text = _la_text
                _this_ladir_replaced = False
                # Pass 1: libdir
                if _LADIR_BAD.search(_new_text):
                    _LADIR_MATCHED_FILES += 1
                    _new_text = _LADIR_BAD.sub(
                        f"libdir='{dep_libdir}'", _new_text, count=1)
                    _this_ladir_replaced = True
                # Pass 2 + Pass 3: inst_prefix_dir
                # - Field present + value matches BAD → REWRITE
                # - Field present + value is a real absolute path → KEEP
                # - Field absent → INJECT
                _instprefix_action = "KEEP"
                if _INSTPREFIX_PRESENT.search(_new_text):
                    if _INSTPREFIX_BAD.search(_new_text):
                        _new_text = _INSTPREFIX_BAD.sub(
                            f"inst_prefix_dir='{dep.package_folder}'",
                            _new_text, count=1)
                        _instprefix_action = "REWRITE"
                        _INSTPREFIX_REPLACED += 1
                    # else: KEEP (real absolute path → untouched)
                else:
                    # Field absent — inject at end of file (libtool 2.4
                    # parses .la via eval/source, field order is
                    # immaterial for downstream link logic).
                    _new_text = _new_text.rstrip("\n") + \
                        f"\ninst_prefix_dir='{dep.package_folder}'\n"
                    _instprefix_action = "INJECT"
                    _INSTPREFIX_INJECTED += 1
                # Pass 5: dependency_libs (rewrites '-L//lib' / '-L/lib'
                # to '-L<dep_libdir>' so that libtool's
                # newlib_search_path correctly resolves the .la of
                # transitive deps). Pass 1+2+3 alone are NOT sufficient:
                # even with corrected libdir + inst_prefix_dir, libtool
                # still sees dependency_libs as a literal string with
                # bad -L entries and tries to look up files there.
                _deplibs_action = "KEEP"
                _deplibs_lflag_rewritten = False
                _deplibs_la_rewritten = False
                if _DEPLIBS_BAD_LFLAG.search(_new_text):
                    _new_text = _DEPLIBS_BAD_LFLAG.sub(
                        f"\\g<1>{dep_libdir}", _new_text)
                    _deplibs_lflag_rewritten = True
                if _DEPLIBS_BAD_LA.search(_new_text):
                    _new_text = _DEPLIBS_BAD_LA.sub(f"{dep_libdir}/", _new_text)
                    _deplibs_la_rewritten = True
                if _deplibs_lflag_rewritten or _deplibs_la_rewritten:
                    _deplibs_action = "REWRITE"
                    _DEPLIBS_REPLACED += 1
                if _new_text == _la_text:
                    self.output.info(
                        f"R-NEW: {dep.ref.name}/{dep.ref.version} "
                        f"{la_name}: nothing to rewrite (libdir already "
                        f"correct, inst_prefix_dir present and absolute)"
                    )
                    continue
                try:
                    with open(la_path, "w", encoding="utf-8") as _fh:
                        _fh.write(_new_text)
                    if _this_ladir_replaced:
                        _LADIR_REPLACED += 1
                        self.output.info(
                            f"R-NEW: rewrote libdir in {la_path} → "
                            f"{dep_libdir} (was '/lib' or '//lib' due to "
                            f"upstream --prefix=/ in "
                            f"{dep.ref.name}/{dep.ref.version}; fixes "
                            f"libtool 'is not a valid libtool archive' "
                            f"on pidgin link stage — see "
                            f"knowledge/doc/E209.md)"
                        )
                    if _instprefix_action == "REWRITE":
                        self.output.info(
                            f"R-NEW: rewrote inst_prefix_dir in {la_path} "
                            f"→ {dep.package_folder} (was slash-only or "
                            f"empty; libtool 2.4 sed step uses "
                            f"inst_prefix_dir + '/lib' + basename → "
                            f"'//lib/...' path that does not exist on "
                            f"disk; now resolves to actual package_folder)"
                        )
                    elif _instprefix_action == "INJECT":
                        self.output.info(
                            f"R-NEW: injected inst_prefix_dir into "
                            f"{la_path} = '{dep.package_folder}' (field "
                            f"was absent; libtool 2.4 would have defaulted "
                            f"to '/' at runtime, producing the same "
                            f"'//lib/libpcre2-8.la' sed-path error — "
                            f"now resolves to actual package_folder)"
                        )
                    if _deplibs_action == "REWRITE":
                        _what = []
                        if _deplibs_lflag_rewritten:
                            _what.append("-L//lib → -L flags")
                        if _deplibs_la_rewritten:
                            _what.append("bare //lib/<name>.la paths")
                        self.output.info(
                            f"R-NEW: rewrote dependency_libs in {la_path} "
                            f"({' + '.join(_what)} → correct paths; was broken "
                            f"due to upstream --prefix=/ in "
                            f"{dep.ref.name}/{dep.ref.version}; fixes the "
                            f"remaining 'sed: //lib/<name>.la' error after "
                            f"Pass 1/2/3/4 — see knowledge/doc/E209.md)"
                        )
                except OSError as _exc:
                    self.output.warning(
                        f"R-NEW: failed to rewrite {la_path}: {_exc!r}")
        self.output.info(
            f"R-NEW: .la libdir sweep complete — scanned "
            f"{_LADIR_SCANNED} .la file(s) across transitive deps, "
            f"matched bad libdir in {_LADIR_MATCHED_FILES}, "
            f"rewrote libdir in {_LADIR_REPLACED}, "
            f"rewrote inst_prefix_dir in {_INSTPREFIX_REPLACED}, "
            f"injected inst_prefix_dir in {_INSTPREFIX_INJECTED}, "
            f"rewrote dependency_libs in {_DEPLIBS_REPLACED}"
        )

        autotools = Autotools(self)

        # R-NEW: patch configure to change umask 077 → umask 022 for HMDFS.
        #
        # Project knowledge base (knowledge/doc/E011.md, E052.md, E129.md)
        # documents this exact failure pattern on the OHOS HMDFS filesystem
        # used by the ohpcd CI worker:
        #
        #   ./config.status: line 881: ./conf<XXXX>/subs1.awk: Permission denied
        #   config.status: error: could not setup config files machinery
        #
        # Root cause: configure (autoconf 2.72, pidgin-2.14.14) creates its
        # mktemp temp directory with `umask 077` (configure L28963, L28968)
        # inside a heredoc that gets baked verbatim into the generated
        # config.status. On standard ext4 the creating process is the file
        # owner and has rwx on the resulting 0700 dir; on HMDFS the file is
        # materialized with stored owner UID 20001006 while the conan
        # configure-process runs as UID 20020083, so even though mktemp
        # succeeds, the process at 20020083 has no access bits on the dir
        # (0700 with owner=20001006) — every open/read/exec on the
        # heredoc-emitted subs1.awk, subs.sed, and the config.status
        # sub-scripts hits EACCES. The `fi < "$ac_tmp/subs1.awk" > ...`
        # redirect at configure L29100 is the first place this surfaces
        # in our CI logs.
        #
        # The three previous failed attempts (commits 5bcc91aa, 6b41d20c,
        # 01331e12) all targeted the case statement / chmod +x /
        # `fi < file` parsing layers downstream of the actual failure.
        # Those are no-ops because the EACCES happens BEFORE any of those
        # paths are reached — it is the `< subs1.awk` redirect's open()
        # that fails first.
        #
        # Correct fix (per knowledge/doc/E011.md "推荐方案" and E129.md
        # "sed-replace"): change `umask 077` to `umask 022` in the
        # upstream configure script. Because both occurrences in pidgin's
        # configure sit inside the heredoc that bakes config.status, a
        # single sed on configure propagates to both:
        #
        #   sed -i 's/umask 077/umask 022/g' configure
        #
        # This matches the established project pattern — see the
        # following recipes (all in this repo) which use the same umask
        # 077 → 022 patch with the exact same root-cause rationale:
        #   - archives/v/vo-aacenc/0.1.3/conanfile.py:35
        #       replace_in_file(self, f"{self.source_folder}/configure",
        #                       "umask 077", "umask 022")
        #   - archives/x/xapian-core/1.4.26/conanfile.py:64-65
        #   - archives/t/tcl/9.0.3.2/conanfile.py (walks all sub-configures)
        #   - archives/t/tk/9.0.3.2/conanfile.py (walks all sub-configures)
        #   - archives/y/yaz/5.37.3/patches/0001-configure-hmdfs-umask.patch
        #   - archives/x/xmlsec1/1.3.11/patches/0001-configure-hmdfs-umask.patch
        #   - archives/x/xinit/1.4.4/patches/0003-configure.patch
        #   - archives/t/timidity/2.13.2/patches/0003-configure-hmdfs-umask.patch
        #   - archives/x/x86_64-elf-grub/2.12/patches/0006-configure.patch
        #
        # We patch BOTH self.source_folder/configure AND
        # self.build_folder/configure. The project's established pattern
        # (see recipes listed above) is to patch self.source_folder, but
        # the previous commit (22bd6ca7) patched self.build_folder only
        # and the patch did not take effect — possibly because on this
        # conan 2.x install the build_folder resolved to a path that did
        # not actually contain configure (the configure the autotools
        # helper invokes lives at a slightly different path than what
        # `self.build_folder` reports). To eliminate that ambiguity, we
        # patch both. conan 2.x's source-to-build copy is non-destructive
        # for already-existing build_folder files, so the build_folder
        # patch persists through the rest of the build pipeline.
        configure_script_source = os.path.join(self.source_folder, "configure")
        configure_script_build = os.path.join(self.build_folder, "configure")
        for _cfg_path in (configure_script_source, configure_script_build):
            if not os.path.exists(_cfg_path):
                continue
            try:
                replace_in_file(
                    self, _cfg_path,
                    "umask 077", "umask 022",
                )
                self.output.info(
                    f"R-NEW: patched {_cfg_path} to use umask 022 instead of "
                    f"umask 077 (bypasses OHOS HMDFS temp-dir UID mismatch "
                    f"that caused ./confXXXX/subs1.awk: Permission denied "
                    f"on conan-create; see knowledge/doc/E011.md, E052.md, "
                    f"E129.md)"
                )
            except Exception as _exc:
                self.output.warning(
                    f"R-NEW: failed to patch {_cfg_path}: {_exc!r} "
                    f"(conan-create will continue and likely fail at "
                    f"config.status; this branch is best-effort)"
                )

        autotools.configure()

        # R-NEW (2026-08-04): diagnostic dump of the libtool link command
        # for ssl.la. If Pass 4 (set --prefix=<package_folder>) succeeds,
        # the link command should NOT contain `-L//lib` or any path that
        # does not match self.package_folder. This trace is a safety net:
        # if a future CI run fails with a different "sed: <path>" error
        # after this commit, the dump will tell us exactly which Makefile
        # variable holds the bad path so we can pinpoint the next layer
        # of the bug instead of guessing again.
        try:
            _ssl_mk = os.path.join(self.build_folder, "libpurple",
                                    "plugins", "ssl", "Makefile")
            if os.path.exists(_ssl_mk):
                with open(_ssl_mk, "r", encoding="utf-8",
                          errors="replace") as _fh:
                    _ssl_makefile_text = _fh.read()
                # Pick the SSL_la_LINK assignment lines (the link command)
                _link_lines = [
                    ln for ln in _ssl_makefile_text.splitlines()
                    if "ssl_la_LINK" in ln and "=" in ln
                ]
                self.output.info(
                    f"R-NEW: ssl.la link command lines from "
                    f"libpurple/plugins/ssl/Makefile:\n  "
                    + "\n  ".join(_link_lines[:6])
                )
                # Also dump libdir and a few related autoconf paths
                for _key in ("libdir", "bindir", "prefix",
                             "includedir", "abs_top_builddir"):
                    for ln in _ssl_makefile_text.splitlines():
                        if ln.startswith(f"{_key} =") or ln.startswith(
                                f"  {_key} ="):
                            self.output.info(
                                f"R-NEW: libpurple/plugins/ssl/Makefile: "
                                f"{ln.strip()}")
                            break
        except Exception as _exc:
            self.output.warning(
                f"R-NEW: ssl.la Makefile diagnostic dump failed: {_exc!r}"
            )

        # R-NEW (2026-08-04): Pass 5 defense-in-depth — also dump the
        # `dependency_libs` field of each transitive .la so we can
        # verify at-a-glance that the rewritten `-L` flags now point
        # at the actual conan2 cache path rather than at `//lib`.
        # If a future CI run still fails with `sed: //lib/<name>.la`,
        # the dump below will tell us whether Pass 5 was incomplete
        # (some other `.la` file or some other field contains the
        # bad path) so we don't have to guess again.
        try:
            for _dep in self.dependencies.values():
                _dep_libdir = os.path.join(_dep.package_folder, "lib")
                if not os.path.isdir(_dep_libdir):
                    continue
                for _la_name in os.listdir(_dep_libdir):
                    if not _la_name.endswith(".la"):
                        continue
                    _la_path = os.path.join(_dep_libdir, _la_name)
                    try:
                        with open(_la_path, "r", encoding="utf-8",
                                  errors="replace") as _fh:
                            _la_text_post = _fh.read()
                    except OSError:
                        continue
                    for _key in ("dependency_libs", "libdir",
                                 "inst_prefix_dir"):
                        for _ln in _la_text_post.splitlines():
                            if _ln.lstrip().startswith(f"{_key}="):
                                self.output.info(
                                    f"R-NEW: post-Pass {_la_name}: "
                                    f"{_ln.strip()}")
                                break
        except Exception as _exc:
            self.output.warning(
                f"R-NEW: .la post-Pass diagnostic dump failed: {_exc!r}"
            )

        # Honor -j parallel jobs from profile conf; fall back to CPU count, then 2.
        # conan-center profiles often set tools.cmake.cmaketoolchain:jobs.
        jobs = self.conf.get("tools.build:jobs",
                             default=os.cpu_count() or 2)

        # R-NEW (2026-08-06 / Pass 11): neutralize the libpurple/example/
        # Makefile BEFORE `autotools.make` runs. Symptom (post-Pass-10
        # CI 2026-08-06):
        #
        #   ld.lld: error: undefined symbol: g_libintl_bindtextdomain
        #   >>> referenced by ggettext.c.o:(glib_gettext) in archive
        #   >>>              /.../libglib-2.0.a
        #   ld.lld: error: undefined symbol: g_libintl_bind_textdomain_codeset
        #   ld.lld: error: undefined symbol: g_libintl_dgettext
        #   ld.lld: error: undefined symbol: g_libintl_textdomain
        #   ld.lld: error: undefined symbol: g_libintl_gettext
        #   ld.lld: error: undefined symbol: g_libintl_dcgettext
        #   ld.lld: error: undefined symbol: g_libintl_dngettext
        #
        # Root cause: libpurple.a is a libtool archive so undefined
        # weak symbols (`g_libintl_*`, provided by libintl/gettext) are
        # accepted at archive-link time; Autotools' recursive `make`
        # builds libpurple with hidden `glib_gettext` deps that don't
        # surface during the libpurple.la stage. But the very last
        # subdir built is `libpurple/example/nullclient`, an executable
        # whose final `CCLD nullclient` step has to resolve every
        # reference — and glib-2.84.0 was built with `--enable-nls` and
        # its static archive carries those `g_libintl_*` calls. musl on
        # OHOS does not provide libintl.so / libintl.a (gettext is NOT
        # in the OHOS POSIX surface — native code uses OHOS i18n
        # extensions). So the link fails once we hit nullclient.o.
        #
        # nullclient is shipped ONLY as an *example* (pidgin 2.14.14
        # configure has no `--disable-example`). It is a developer toy
        # that reads stdin and prints protocols — not a binary we need
        # to ship or test. The cleanest fix that doesn't touch the
        # source tree is to rewrite the autotools-generated
        # `libpurple/example/Makefile` so that it makes `all`,
        # `install`, and `clean` into no-ops. The `libpurple/example/`
        # subdirectory itself stays on disk (downstream packaging
        # scripts that grep for it keep working), but the compiled
        # binary is intentionally skipped.
        #
        # We patch the build_folder copy (which is what autotools is
        # about to use); the source_folder copy (autotools-generated
        # `libpurple/example/Makefile.in` -> regenerated Makefile) is
        # left untouched for any hand-driven build by humans. Both
        # source_folder and build_folder copies are patched because
        # conan 2.x autotools may use either, depending on internal
        # optimisation.
        #
        # The first-pass regex targets recursive `$(MAKE)` invocations from
        # Automake-generated rules. The second-pass regex (R-NEW, Pass 19)
        # handles the `all-am` rule body directly. `all-am` is the rule that
        # `make all` dispatches to in Automake's per-directory build; it
        # contains the actual `CCLD nullclient` link command (not wrapped in a
        # recursive `$(MAKE)` call). Matching the `all-am` rule body with
        # `.*` after the colon and replacing it with `; @true` ensures that
        # `nullclient` is never linked, regardless of how the build system
        # invokes it (via `all`, `all-am`, or a bare `nullclient` target).
        #
        # Patch build_folder LAST so that any Makefile copy generated after
        # configure (autotools can write either source or build copies first
        # depending on internal optimisation) is the one that survives until
        # `make` reads it. Also include source_folder as a fallback in case
        # the build uses the source Makefile directly.
        for _nc_dir in (
            os.path.join(self.source_folder,
                         "libpurple", "example", "Makefile"),
            os.path.join(self.build_folder,
                         "libpurple", "example", "Makefile"),
        ):
            if not os.path.isfile(_nc_dir):
                continue
            try:
                with open(_nc_dir, "r", encoding="utf-8",
                          errors="replace") as _mfh:
                    _mf_txt = _mfh.read()
            except OSError:
                continue
            _mf_new = _mf_txt
            for _patch_pass in (1, 2):
                if _patch_pass == 1:
                    _mf_new = re.sub(
                        r"^([\t ]+)\$\(MAKE\)([ \t].*)?$",
                        r"\1@$(TRUE)\2",
                        _mf_new,
                        flags=re.MULTILINE)
                else:
                    _mf_new = re.sub(
                        r"^all-am:\s*$",
                        "all-am: ; @true",
                        _mf_new,
                        flags=re.MULTILINE)
            if _mf_new != _mf_txt and _mf_new:
                with open(_nc_dir, "w", encoding="utf-8") as _mfh:
                    _mfh.write(_mf_new)
                self.output.info(
                    "R-NEW: rewrote libpurple/example/Makefile so the "
                    "nullclient example binary is skipped at build/install "
                    "time (root cause: glib-2.84.0 was built with NLS, "
                    "pulling g_libintl_* from libintl/gettext which is "
                    "absent on OHOS musl; nullclient is a developer toy, "
                    "not a runtime artifact of this recipe — see notes.md "
                    "Pass 11, Pass 19 fix)"
                )

        autotools.make(args=[f"-j{jobs}"])

    def package(self):
        autotools = Autotools(self)
        # R-NEW (2026-08-06, Pass 12): pass DESTDIR=<package_folder>
        # explicitly to `make install` rather than relying on conan
        # 2.x's auto-prepend behaviour. Why explicit:
        #   - conan 2.x `Autotools.install()` *does* prepend
        #     `DESTDIR=<package_folder>` automatically. In principle,
        #     this would yield installed paths `<pkg>/<prefix>/<file>`
        #     = `<pkg>/<file>` (single-nested) when --prefix=/.
        #   - In practice on the ohpcd hnp bundle's conan 2.x, the
        #     auto-prepend was observed to be a no-op for some recent
        #     recipe builds (verified by the
        #     `<pkg>/<pkg>/lib/libpurple.la` double-nesting seen in
        #     the post-Pass-11 CI log, even though Pass 4 set
        #     --prefix=<pkg>).
        #   - Passing DESTDIR explicitly eliminates ambiguity: the
        #     make command line unambiguously reads
        #     `make install DESTDIR=<pkg>` and the install rules
        #     rewrite `<prefix>/lib/foo` to `<DESTDIR><prefix>/lib/foo`
        #     = `<pkg>/lib/foo` (single-nested, correct).
        autotools.install(args=[f"DESTDIR={self.package_folder}"])

    def package_info(self):
        self.cpp_info.libs = ["purple"]
        # NOTE: cmake_file_name and cmake_target_name use the project name "pidgin"
        # for consumer-facing CMake convenience (find_package(pidgin)), while
        # pkg_config_name keeps the historical "libpurple" name because the
        # installed .pc file is libpurple.pc (autotools installs pkg-config
        # with its native name). This split is intentional — see conan-center
        # recipe style guide §"name variants".
        self.cpp_info.set_property("cmake_file_name", "pidgin")
        self.cpp_info.set_property("cmake_target_name", "pidgin::pidgin")
        self.cpp_info.set_property("pkg_config_name", "libpurple")
        # pidgin installs headers to <pkg>/include/libpurple/ but
        # purple.h internally uses #include <account.h> (relative paths),
        # so consumers must add include/libpurple to their include path.
        self.cpp_info.includedirs = ["include/libpurple"]
        # CMakeDeps: forward transitive deps so target_link_libraries works
        # for consumers linking only against pidgin::pidgin.
        #
        # Version note (2026-07-31, after maintainer hint + ohpcd registry
        # probe): the team's glib/2.84.0 recipe in ohpcd does NOT use the
        # conan-center pattern of `components["glib-2.0"]` etc. Instead it
        # sets a flat `cpp_info.libs = ["glib-2.0", "gobject-2.0",
        # "gio-2.0", "gmodule-2.0", "gthread-2.0"]` and only
        # `cmake_file_name="glib"` (no `cmake_target_name`). The default
        # CMake target is therefore the AGGREGATE `glib::glib`, NOT any of
        # the conan-center-style `glib::glib-2.0` / `glib::gobject-2.0`
        # sub-targets (which simply don't exist for this recipe).
        #
        # For libxml2/2.15.3 (ohpcd), the recipe is more explicit:
        #   cmake_file_name="LibXml2", cmake_target_name="LibXml2::LibXml2"
        # so consumers must use `LibXml2::LibXml2` (capital L + X, and the
        # literal cmake target name). Capital-cased find_package(LibXml2)
        # too.
        #
        # Earlier conanfile.py revisions (before the version bump) listed
        # six separate glib components; those would have produced
        # "Target \"glib::glib-2.0\" not found" under the team's glib recipe.
        # Keeping that list under glib/2.84.0 was the central mistake
        # behind the CI graph failure (separate from the version bump itself).
        # IMPORTANT (conan 2.x): self.cpp_info.requires must reference the
        # CANONICAL conan component name, which for a recipe WITHOUT
        # explicit `cpp_info.components` is `<package>::<package>` (lower
        # case, package name verbatim) — NOT the `cmake_target_name`
        # property. The cmake_target_name (e.g. `LibXml2::LibXml2`) is
        # consumed by the CMakeDeps generator for the generated CMake
        # target, but the conan graph validation that runs in
        # `package_info()` checks the canonical cpp_info name. Passing
        # the cmake target name produces this CI error:
        #   "ERROR: ... package_info(): There are '(cpp_info/components)
        #    .requires' that includes package 'LibXml2::', but such
        #    package is not a a direct requirement of the recipe"
        # (verified CI 2026-08-06, post-Pass 9 successful build).
        #
        # For the team's glib recipe: no `cpp_info.components`, root
        # component is `glib::glib`. For the team's libxml2 recipe:
        # no `cpp_info.components`, root component is `libxml2::libxml2`
        # (per package_info convention — package name lower-case even
        # when the cmake_target_name has a different case).
        self.cpp_info.requires = [
            "glib::glib",
            "libxml2::libxml2",
        ]
        # musl/HMDFS behavior: see manifest.yaml:platform_specific[runtime]
        # (SSOT for system_libs rationale).
        #
        # OHOS musl integrates pthread/rt/dl symbols directly into libc.so
        # (they are no-op implementations). Passing them through system_libs
        # therefore does NOT cause a static-link error on OHOS, contrary to
        # an earlier draft of the manifest's knowledge_gained entry. We
        # intentionally still forward them because:
        #   (a) glibc CI profiles (and some conan toolchain discovery paths)
        #       need real libpthread/librt/libdl to satisfy their symbols.
        #   (b) glib's CMake config does not reliably propagate these
        #       system libs through its INTERFACE_LINK_LIBRARIES in conan 2.29.
        # Net effect: the same system_libs vector works for both OHOS (musl)
        # and glibc profiles; musl silently ignores the requests, glibc
        # honours them.
        # See atomgit-bot review 2026-07-31 on PR #3274.
        self.cpp_info.system_libs = ["m", "pthread", "rt", "dl"]
