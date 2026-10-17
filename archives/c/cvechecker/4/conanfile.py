#!/usr/bin/env python3
"""Conan recipe for cvechecker 4.

cvechecker is a CLI tool (Sven Vermeulen / sjvermeu/cvechecker) that matches the
installed software on a host against a local CVE database.  This recipe adapts
the 4.0 release to HarmonyOS PC (aarch64).

Key adaptation notes:
  * The GitHub "archive" tarball is a plain git snapshot: it ships configure.ac
    and a *committed* configure script, but **no** generated Makefile.in /
    aclocal.m4 / config.h.in (automake artefacts are not in the repository).
    The committed configure cannot run (AC_CONFIG_FILES needs Makefile.in), so
    the tree must be bootstrapped with autotools (aclocal -> autoconf /
    autoheader -> automake) driven through the conan perl interpreter, because
    the HNP-run `autoreconf` crashes loading the conan Cwd.so
    (Perl_my_cxt_init symbol not found).
  * configure.ac requires the following via pkg-config / headers:
      - libbsd     (PKG_CHECK_MODULES BSD, unconditional) -> VENDORED
      - libconfig  (PKG_CHECK_MODULES CONFIG >= 1.3)
      - sqlite3    (PKG_CHECK_MODULES SQLITE3, enabled by default)
      - argp.h     (AC_CHECK_HEADERS; argp is not glibc on musl-based OHOS)
    libconfig and sqlite3 are discovered through their generated .pc
    files (PkgConfigDeps + VirtualBuildEnv's PKG_CONFIG_PATH).  argp is not
    exposed via pkg-config, so its include/lib dirs are injected explicitly.
  * libbsd is an UNCONDITIONAL pkg-config requirement in configure.ac, but it
    is not published in the ohpcd or conancenter remotes, so `self.requires`
    cannot resolve it. Auditing the 4.0 source shows cvechecker only uses the
    BSD `strlcpy` function (via <bsd/string.h>), which OHOS's musl libc does
    not provide.  build() therefore synthesises a minimal vendored libbsd:
    a correct `strlcpy` compiled into libbsd.a, a <bsd/string.h> header, and a
    libbsd.pc placed on PKG_CONFIG_PATH so configure's PKG_CHECK_MODULES(B)
    and `$BSD_LIBS` linking resolve.  This is a functional strlcpy (not a
    no-op stub) because cvechecker's string handling depends on its semantics.
  * Upstream ships no test suite: no Makefile.am defines a TESTS/check target
    and `make check` is a no-op in every subdirectory (see test_package/
    MANIFEST.yml for the audit).
"""

import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# OHOS HMFS/HMDFS: choose a getcwd-clean shell for the configure/autotools
# machinery.  The HNP bash (/data/service/hnp/bin/bash, pulled in by the
# profile's SHELL/CONFIG_SHELL) fails getcwd() on the deep conan build path,
# spamming `shell-init: ... getcwd: cannot access parent directories` and
# aborting configure with "working directory cannot be determined".  The
# vendor toybox /system/bin/sh probes clean in the same directory (cvsgraph
# 1.7.0 真机实证 on this OHOS PC family).  The ac_pwd patch in
# _patch_configure_for_ohos() still makes configure survive even if the
# launching shell's pwd cannot resolve getcwd().
OHOS_CONFIGURE_SHELL = "/system/bin/sh"


# Vendored minimal <bsd/string.h> for HarmonyOS/musl: cvechecker only uses
# BSD's strlcpy and musl's libc neither declares nor exports it.
VENDORED_BSD_STRING_H = r"""/* Vendored minimal <bsd/string.h> providing strlcpy for HarmonyOS/musl,
   where libbsd has no published conan package and the musl libc lacks strlcpy.
   cvechecker uses only strlcpy (from libbsd). */
#ifndef _VENDOR_BSD_STRING_H_
#define _VENDOR_BSD_STRING_H_

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Copy at most size-1 bytes from src into dst, always NUL-terminating dst,
   and return the total length of src (the string it tried to create). */
size_t strlcpy(char *dst, const char *src, size_t size);

#ifdef __cplusplus
}
#endif

#endif /* _VENDOR_BSD_STRING_H_ */
"""

# Correct, self-contained strlcpy(3) used to build the vendored libbsd.a.
VENDORED_STRLCPY_C = r"""/* Vendored minimal strlcpy(3) (BSD) for HarmonyOS/musl.
   Upstream cvechecker depends on libbsd purely for strlcpy; libbsd has no
   published conan package, so we provide this correct implementation.
   Musl's libc does not export strlcpy, so configure's AC_CHECK_FUNCS finds it
   missing and pulls this static archive through the generated libbsd.pc. */
#include <string.h>

size_t strlcpy(char *dst, const char *src, size_t size) {
    size_t slen = strlen(src);
    if (size == 0) {
        return slen;
    }
    size_t cp = (slen < size - 1) ? slen : (size - 1);
    if (cp != 0) {
        memcpy(dst, src, cp);
    }
    dst[cp] = '\0';
    return slen;
}
"""


class CvecheckerConan(ConanFile):
    name = "cvechecker"
    description = ("Match the installed software against a local CVE database "
                   "and report potential vulnerabilities")
    license = "GPL-3.0"
    homepage = "https://github.com/sjvermeu/cvechecker"
    url = ""  # CI fills this repository URL

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def set_version(self):
        # Conan 2.29+ rejects a single-character version ("4") at export with
        # `ERROR: Invalid package version '4'` (RecipeReference regex requires
        # a version of >= 2 chars: ^[a-z0-9_][a-z0-9_+.-]{1,100}$).  The
        # task-card directory, branch (feat/cvechecker-4) and delivery
        # whitelist keep the single-char "4" for L0m consistency, while the
        # built artifact uses the dotted upstream form "4.0" (AC_INIT
        # [cvechecker],[4.0]; upstream release tag cvechecker-4.0,
        # conandata.yml sources.url). Directory-article separation:
        # archives/c/cvechecker/4 produces `cvechecker/4.0`.
        self.version = "4.0"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # All published in the OHOSPCD registry (R36 / W0):
        self.requires("libconfig/1.7.3")
        self.requires("sqlite3/3.53.4")
        # argp.h + libargp.a are not in the musl-based OHOS libc; the repo's
        # argp-standalone recipe provides them as a static library.
        self.requires("argp-standalone/1.5.0")
        # configure.ac unconditionally runs PKG_CHECK_MODULES([BSD], [libbsd]),
        # but libbsd has NO published conan package (absent from ohpcd and
        # conancenter), so requiring it breaks graph resolution:
        #   ERROR: Package 'libbsd/0.11.7' not resolved: Unable to find
        #          'libbsd/0.11.7' in remotes.
        # cvechecker only uses libbsd's `strlcpy` (via <bsd/string.h>); OHOS
        # musl libc lacks strlcpy.  build() therefore synthesises a minimal
        # vendored libbsd providing a real strlcpy + libbsd.pc (no-op stubs are
        # wrong here because cvechecker's string handling relies on strlcpy).
        # No self.requires("libbsd/...") is declared for this reason.

    def build_requirements(self):
        # The GitHub-archive tarball has no generated autotools files; the
        # committed configure can't run without Makefile.in, so bootstrap the
        # tree (aclocal/aclocal -> autoheader/autoconf -> automake).
        # autoconf + automake (and their perl) come from conan so the XS ABI of
        # the perl interpreters and PERL5LIB are consistent on the OHOS host.
        # perl is listed explicitly so the recipe can resolve its bin/perl path
        # deterministically (HNP's /data/service/hnp/bin/perl 5.42.0 is a
        # non-i-thread build and cannot load conan's 5.42.2 Cwd.so).
        self.tool_requires("automake/1.18")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("perl/5.42.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_paths(self, pkg):
        """Absolute include/lib dirs of a requirement (cpp_info dirs are
        relative to package_folder in Conan 2)."""
        dep = self.dependencies[pkg]
        info = dep.cpp_info.aggregated_components()
        root = dep.package_folder
        return ([os.path.join(root, d) for d in info.includedirs if d],
                [os.path.join(root, d) for d in info.libdirs if d])

    def _stub_root(self):
        """Absolute root of the vendored mini-libbsd (deterministic so that
        generate() and build() agree on the include path)."""
        return os.path.join(self.build_folder, "stub_bsd")

    def _build_vendored_libbsd(self):
        """Synthesise a minimal libbsd so configure's unconditional
        PKG_CHECK_MODULES([BSD],[libbsd]) and `$BSD_LIBS` linking resolve.

        cvechecker uses only BSD's strlcpy (via <bsd/string.h>), which OHOS's
        musl libc lacks.  We build a *real* strlcpy (not a no-op stub) into
        libbsd.a, ship <bsd/string.h>, and write a libbsd.pc into the
        generators folder (already on configure's PKG_CONFIG_PATH via
        VirtualBuildEnv/PkgConfigDeps) pointing at the vendored files.
        """
        root = self._stub_root()
        inc = os.path.join(root, "include", "bsd")
        src = os.path.join(root, "src")
        lib = os.path.join(root, "lib")
        for d in (inc, src, lib, os.path.join(root, "include")):
            os.makedirs(d, exist_ok=True)

        with open(os.path.join(inc, "string.h"), "w") as fh:
            fh.write(VENDORED_BSD_STRING_H)
        srcc = os.path.join(src, "strlcpy.c")
        with open(srcc, "w") as fh:
            fh.write(VENDORED_STRLCPY_C)

        cc_exes = self.conf.get("tools.build:compiler_executables", default={})
        cc = cc_exes.get("c") or os.environ.get("CC") or "clang"
        obj = os.path.join(src, "strlcpy.o")
        self.run("%s -O2 -c %s -o %s" % (cc, srcc, obj), env="conanbuild")
        self.run("ar rcs %s %s" % (os.path.join(lib, "libbsd.a"), obj),
                 env="conanbuild")

        # libbsd.pc into the generators folder so configure's PKG_CHECK_MODULES
        # finds it (same folder as the PkgConfigDeps .pc files).
        pcfile = os.path.join(self.generators_folder, "libbsd.pc")
        with open(pcfile, "w") as fh:
            fh.write(
                "prefix=%s\n"
                "includedir=${prefix}/include\n"
                "libdir=${prefix}/lib\n"
                "\n"
                "Name: libbsd\n"
                "Description: vendored mini-libbsd (strlcpy) for HarmonyOS\n"
                "Version: 0.11.7\n"
                "Cflags: -I${includedir}\n"
                "Libs: -L${libdir} -lbsd\n" % root
            )
        self.output.info("vendored libbsd (strlcpy) ready at %s" % root)

    def generate(self):
        VirtualBuildEnv(self).generate()
        # libconfig / sqlite3 are looked up with pkg-config by configure;
        # PkgConfigDeps emits relocatable .pc files that VirtualBuildEnv puts
        # on PKG_CONFIG_PATH.  (libbsd is vendored, see _build_vendored_libbsd.)
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # sqlite3 is the default backend; configure's sqlite3.pc is provided by
        # the sqlite3/3.53.4 conan package (pkg_config_name "sqlite3").
        tc.configure_args.append("--enable-sqlite3")

        # argp is not exposed via pkg-config: make argp.h discoverable and
        # link the static libargp.a explicitly.
        argp_inc, argp_lib = self._dep_paths("argp-standalone")
        tc.extra_cflags.extend("-I%s" % d for d in argp_inc)
        tc.extra_ldflags.extend("-L%s" % d for d in argp_lib)
        tc.extra_ldflags.append("-largp")

        # The vendored mini-libbsd <bsd/string.h> header (see _build_vendored_
        # libbsd / build()): configure.ac adds `$CONFIG_CFLAGS` to CFLAGS but
        # never `$BSD_CFLAGS`, so the bsd include path must be injected here.
        # cvecheck_common.h and output/stringscmd.h `#include <bsd/string.h>`.
        tc.extra_cflags.append("-I%s" % os.path.join(self._stub_root(), "include"))

        # OHOS /tmp can be read-only and the HNP SDK holds pkg.m4 (for
        # PKG_CHECK_MODULES) in its own aclocal dirs. Point the autotools
        # bootstrap at them and keep temporary files inside this build folder.
        environment = tc.environment()
        for directory in sorted(glob.glob("/data/service/hnp/*/*/share/aclocal")):
            environment.append_path("ACLOCAL_PATH", directory)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        # Force the getcwd-clean vendor shell for configure/config.status so the
        # HMFS getcwd() failures (HNP bash) never abort the configure stage.
        environment.define("SHELL", OHOS_CONFIGURE_SHELL)
        environment.define("CONFIG_SHELL", OHOS_CONFIGURE_SHELL)
        tc.generate(env=environment)

    def _autotools_perl(self):
        # Resolve the conan perl (5.42.x, i-thread) whose XS ABI matches the
        # PERL5LIB exported by the tool requires, so XS modules like Cwd.so
        # relocate cleanly.  HNP's /data/service/hnp/bin/perl (5.42.0,
        # non-i-thread) lacks the Perl_my_cxt_init symbol and crashes when the
        # conanbuild PERL5LIB makes it load the conan Cwd.so.
        for dep in self.dependencies.build.values():
            if dep.ref.name == "perl" and dep.package_folder:
                return os.path.join(dep.package_folder, "bin", "perl")
        return shutil.which("perl") or "/data/service/hnp/bin/perl"

    def _bootstrap_autotools_for_ohos(self):
        # GitHub-archive tarballs never carry generated autotools files and the
        # committed configure can't run without Makefile.in.  The bare
        # `autoreconf` at /data/service/hnp/bin runs under the HNP perl and
        # crashes while loading the conan Cwd.so (Perl_my_cxt_init symbol not
        # found).  Instead drive each bootstrap step (aclocal -> autoconf /
        # autoheader -> automake) through the conan perl interpreter with the
        # relocatable package paths - the HMDFS-compatible strategy proven by
        # the repo's abx recipe.
        automake_root = self.dependencies.build["automake"].package_folder
        autoconf_root = self.dependencies.build["autoconf"].package_folder
        perl = self._autotools_perl()
        automake_share = os.path.join(automake_root, "share", "automake-1.18")
        common = [perl, "-I", automake_share]

        aclocal = os.path.join(automake_root, "bin", ".aclocal-real")
        self.run(
            shlex.join(
                common
                + [
                    aclocal,
                    "--automake-acdir="
                    + os.path.join(automake_root, "share", "aclocal-1.18"),
                    "--system-acdir="
                    + os.path.join(automake_root, "share", "aclocal"),
                    "--force",
                ]
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )
        # autoconf/autoheader are built with/for the conan perl, and the
        # conanbuild PERL5LIB points at the conan perl's XS module dirs.  The
        # bare `autoconf`/`autoheader` on PATH resolve to /data/service/hnp/bin
        # (HNP perl 5.42.0, non-i-thread) which crashes loading the conan
        # 5.42.2 Cwd.so (Perl_my_cxt_init symbol not found).  Drive them through
        # the conan perl interpreter using the conan autoconf package's own
        # scripts, exactly like aclocal/automake above.
        self.run(
            shlex.join(
                [perl, os.path.join(autoconf_root, "bin", "autoconf"), "--force"]
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run(
            shlex.join(
                [perl, os.path.join(autoconf_root, "bin", "autoheader"), "--force"]
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )

        automake = os.path.join(automake_root, "bin", ".automake-real")
        self.run(
            shlex.join(
                common
                + [
                    automake,
                    "--libdir=" + automake_share,
                    "--add-missing",
                    "--copy",
                    "--force-missing",
                ]
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def _patch_configure_for_ohos(self):
        """Make the freshly-bootstrapped configure survive the HMFS getcwd bug.

        In the deep conan build path (HMDFS) the shell's getcwd() fails, so
        configure's `ac_pwd=\`pwd\`` produces an empty path and configure dies
        with `error: working directory cannot be determined` (the exact stage
        that failed in preflight).  We patch the ac_pwd computation to fall
        back to configure's actual working directory (self.build_folder, which
        is where Autotools.configure() runs) when `pwd` cannot resolve getcwd().
        Also relax `umask 077` -> `umask 022` so the config.status temp
        directory (drwx--S--- under 077) is writable on HMFS (E011 family).

        Because the configure is regenerated by autoconf every build, the patch
        must run after _bootstrap_autotools_for_ohos() and immediately before
        autotools.configure().
        """
        conf = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(conf):
            self.output.warning(
                "configure not found at %s - skipping OHOS getcwd patch" % conf
            )
            return
        with open(conf, encoding="utf-8", errors="replace") as fh:
            data = fh.read()
        orig = data
        # Deterministic fallback: inject the real build directory absolute path
        # so ac_pwd is correct even when both `pwd` and `$PWD` are unusable.
        fallback = self.build_folder
        replacements = (
            (r"ac_pwd=`pwd`",
             "ac_pwd=`pwd 2>/dev/null || echo \"%s\"`" % fallback),
            (r"umask 077", r"umask 022"),
        )
        applied = []
        for old, new in replacements:
            if old in data:
                data = data.replace(old, new)
                applied.append(old)
        if data != orig:
            with open(conf, "w", encoding="utf-8", newline="") as fh:
                fh.write(data)
            self.output.info(
                "patched configure for OHOS getcwd: %s" % ("; ".join(applied))
            )
        else:
            self.output.warning(
                "configure OHOS patch: none of the expected literals "
                "(ac_pwd=`pwd`, umask 077) were found"
            )


    def build(self):
        apply_conandata_patches(self)
        # libbsd is not published anywhere, yet configure.ac unconditionally
        # PKG_CHECK_MODULES([BSD],[libbsd]). Synthesise a minimal vendored
        # libbsd (real strlcpy) + libbsd.pc before the bootstrap/configure so
        # the pkg-config check and $BSD_LIBS linking resolve.
        self._build_vendored_libbsd()
        autotools = Autotools(self)
        # GitHub archive tarballs never carry generated autotools files.  The
        # committed configure cannot run without Makefile.in, so regenerate all
        # of aclocal.m4 / config.h.in / Makefile.in first.  A manual
        # aclocal -> autoconf/autoheader -> automake bootstrap is used instead
        # of `autoreconf` because the HNP perl-run autoreconf crashes loading
        # the conan Cwd.so (Perl_my_cxt_init symbol not found).
        if not os.path.isfile(os.path.join(self.source_folder, "Makefile.in")):
            self.output.info(
                "source tree has no Makefile.in - bootstrapping autotools "
                "(aclocal -> autoheader/autoconf -> automake) on conan perl"
            )
            self._bootstrap_autotools_for_ohos()
        # The configure is regenerated above by autoconf 2.72. Patch it so the
        # HMFS getcwd bug cannot abort this stage (see helper docstring), and
        # preset PWD so any bash interpreter uses its logical-pwd path instead
        # of failing getcwd() (libuio/cvsgraph-proven approach).
        self._patch_configure_for_ohos()
        os.environ["PWD"] = str(self.build_folder)
        autotools.configure()
        # R9: -j1 for reproducibility on the OHOS worker.
        autotools.make(args=["-j1"])
        # Upstream ships no tests: `make check` is a no-op in every subdir
        # (audited in test_package/MANIFEST.yml). Build stops here.

    def _write_install_shim(self):
        # E182/E188 (adms 2.3.7 / aribb24 1.0.4 / cubelib 4.9.1 precedent): the
        # HMBS/toybox `install` shim on the OHOS HMFS only accepts the
        # single-source form; any multi-source call
        # (`install -c -m 644 f1 f2 ... dest/`) exits 64 (EX_USAGE).  The
        # install-cvecheckerDATA rule uses `$(INSTALL_DATA)` which expands to a
        # multi-source copy of the data files into share/cvechecker and dies
        # with Error 64.  Provide a cp/mkdir shim that tolerates
        # -c/-m/-d/-- and copies each source into the dest dir, and treats
        # chmod failures as non-fatal (HMBS_CAP_CHMOD=0).  Created with
        # os.open(0o755) so it is executable even where chmod is unsupported.
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
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
                    "  mkdir -p \"$dest\"\n"
                    "else\n"
                    "  mkdir -p \"$(dirname \"$dest\")\"\n"
                    "fi\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
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
        except Exception:  # noqa: BLE001 - let the build fail loudly
            try:
                os.close(fd)
            except OSError:
                pass
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass
        self.output.info("cvechecker install shim: %s" % install)
        return install

    def _redirect_install_to_shim(self, shim_install):
        # configure bakes the detected install path into every generated
        # Makefile as `INSTALL = <.../install -c` and
        # `INSTALL_DATA = <.../install -c -m 644` (absolute, not
        # `${INSTALL}`-relative), so replacing INSTALL alone can leave the
        # failing INSTALL_DATA untouched.  Rewrite all four INSTALL* variables
        # that reference an install binary to the shim (cubelib pattern).
        roots = [self.build_folder]
        patched = 0
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                if "Makefile" not in filenames:
                    continue
                mp = os.path.join(dirpath, "Makefile")
                try:
                    with open(mp, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue
                if "INSTALL" not in content or "/install" not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL_DATA = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL_DATA = %s -m 644\n" % (indent, shim_install))
                        changed = True
                    elif stripped.startswith("INSTALL_PROGRAM = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL_PROGRAM = %s\n" % (indent, shim_install))
                        changed = True
                    elif stripped.startswith("INSTALL_SCRIPT = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL_SCRIPT = %s\n" % (indent, shim_install))
                        changed = True
                    elif stripped.startswith("INSTALL = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL = %s\n" % (indent, shim_install))
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    try:
                        with open(mp, "w", encoding="utf-8", newline="\n") as f:
                            f.write("".join(lines))
                        patched += 1
                    except OSError:
                        continue
        self.output.info(
            "cvechecker: redirected INSTALL to shim in %d Makefiles" % patched
        )

    def package(self):
        # Re-assert the install shim before `make install`: the build()'s
        # Makefile rewrite persists in the build tree, but package() may run
        # without a fresh build(), so write the shim and redirect the
        # generated Makefiles' INSTALL* variables here too (E182/E188 Error 64
        # from multi-source `install -c -m 644 ... dest/` on OHOS HMFS).
        try:
            shim = self._write_install_shim()
            self._redirect_install_to_shim(shim)
        except Exception as exc:  # noqa: BLE001 - never swallow the real install
            self.output.warning("cvechecker package install shim failed: %s" % exc)
        autotools = Autotools(self)
        autotools.install()
        # The cvechecker tools output feeds a local sqlite database through the
        # installed config; all deliverable assets (bin/ conf/ share/) are left
        # as installed by upstream.

    def package_info(self):
        # Application package: consumers run the delivered tools, they do not
        # link them (R38 - the tools are also declared in commands.json).
        self.cpp_info.bindirs = ["bin"]
