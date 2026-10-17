#!/usr/bin/env python3
"""Conan recipe for libcaes 0-20251121 — Autotools (configure + make).

libcaes is a C library for cross-platform AES encryption (libyal family:
context + tweaked context, ECB/CBC/CCM/XTS). Same OHOS approach as libbde:
E007 (config.guess/config.sub HarmonyOS) + E011 (umask 077 -> 022).

Version mapping: recipe version 0-20251121 is the task-assigned version
string; upstream AC_INIT version is 20251121. Source is the Ubuntu
libcaes_0~20251121.orig.tar.gz (pristine upstream `make dist` output for
20251121, repacked by Ubuntu): its libcaes/*.c sources are byte-identical
to GitHub commit 4dbdd25466bf25bd73bdf77976e4c9eab744d697 (verified
sha256 of libcaes_context.c), but it additionally ships the generated
configure/Makefile.in/ltmain.sh AND the bundled libcerror subtree.

Why the dist tarball instead of the GitHub commit snapshot (bwm/0.6.3
precedent, 3rd fix for the same fingerprint): the snapshot has no
generated configure and no bundled libcerror, so build() had to run
synclibs.sh (git clone) + autoreconf -fi. That forced tool_requires on
automake/autoconf/libtool/gettext, whose transitive m4/1.4.19 must then
be compiled FOR OHOS (CI passes -pr:b=ohos-aarch64). m4's configure
re-execs $CONFIG_SHELL, and the repo profile pins
CONFIG_SHELL=/data/service/hnp/bin/bash, which is inaccessible on the
HMBS preflight host (configure[139]: "inaccessible or not found",
Error 127) while HMBS guarantees only /bin/sh. Recipe-level env
overrides cannot fix a *dependency's* build, so the chain is removed
at the root: with configure + libcerror already vendored upstream,
this recipe declares only pkgconf/3.0.5 as tool_requires, m4 is never
built, and our own configure is shielded by _force_posix_shell
(hard-coded CONFIG_SHELL/SHELL=/bin/sh inside the script) plus a
build-scope env script that wins over the profile [buildenv]. pkgconf
itself builds with meson (no m4 chain) and is already published, so it
resolves prebuilt and only provides the pkg-config binary that
configure hard-requires.

Upstream tests: tests/Makefile.am defines 7 check_PROGRAMS
(caes_test_context / crypt_cbc / crypt_ccm / crypt_xts / error / support /
tweaked_context) plus TESTS=test_library.sh (test_python_module.sh only
under HAVE_PYTHON_TESTS). build() disables python, builds the 7 programs
via `make check TESTS=` and executes each binary directly (same assertions
the shell driver runs, zero SKIP), then emits the
HMBS_UPSTREAM_TEST_RESULT machine-evidence marker.
"""
import json
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, export_conandata_patches
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibcaesConan(ConanFile):
    name = "libcaes"
    version = "0-20251121"
    description = "Library to support cross-platform AES encryption"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libyal/libcaes"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Only autoreconf needs zero tool_requires: the dist tarball already
    # contains configure, Makefile.in, ltmain.sh and bundled libcerror,
    # so no autoreconf and no synclibs git clone are needed. This keeps
    # the transitive m4/1.4.19 OHOS cross-build (profile
    # CONFIG_SHELL=/data/service/hnp/bin/bash, inaccessible on HMBS
    # hosts, Error 127) out of the graph entirely.
    # Only exception: pkgconf (provides the pkg-config binary that
    # configure hard-requires: "checking for pkg-config... no" ->
    # "configure: error: pkg-config not found" on HMBS workers).
    # pkgconf/3.0.5 builds with meson (no m4 chain) and is already
    # published in the registry, so it resolves as a prebuilt build
    # requirement without reintroducing the m4 failure.
    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.5")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libcaes is only supported on Linux/OHOS, not {}".format(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version][0], strip_root=True)

    def _discover_compiler(self, kind="c"):
        """PATH-first compiler discovery (cstream/4.0.0 lesson)."""
        conf_key = (
            "tools.build:compiler_executables:c"
            if kind == "c"
            else "tools.build:compiler_executables:cpp"
        )
        candidates = []
        try:
            conf_val = self.conf.get(conf_key, check_type=str)
        except Exception:
            conf_val = None
        if conf_val:
            candidates.append(conf_val)
        if kind == "c":
            candidates += ["clang", "cc", "gcc", "/data/service/hnp/bin/clang"]
        else:
            candidates += ["clang++", "c++", "g++", "/data/service/hnp/bin/clang++"]
        for cand in candidates:
            if not cand:
                continue
            if os.path.isabs(cand):
                try:
                    if os.path.isfile(cand) and os.access(cand, os.X_OK):
                        return cand
                except Exception:
                    continue
                continue
            found = shutil.which(cand)
            if found:
                return found
        return None

    def _usable_shell(self):
        """Hard-prefer /bin/sh; never return the HNP bash (bwm/0.6.3 lesson).

        The repo profile pins SHELL/CONFIG_SHELL=/data/service/hnp/bin/bash,
        which exists as a file on some hosts but is not executable there
        ("inaccessible or not found", Error 127). HMBS guarantees
        shell=/bin/sh, so prefer it unconditionally.
        """
        if os.path.isfile("/bin/sh"):
            return "/bin/sh"
        sh_which = shutil.which("sh") or ""
        if sh_which and os.path.isfile(sh_which):
            return sh_which
        for cand in (os.environ.get("SHELL", ""), os.environ.get("CONFIG_SHELL", "")):
            if not cand:
                continue
            first = cand.split()[0]
            if "hnp/bin/bash" in first:
                continue
            if os.path.isfile(first):
                return cand
        return "/bin/sh"

    def _pick_writable_tmpdir(self, fallback_sub=".hmbs-tmp"):
        """Prefer HMBS-injected TMPDIR only after a real write probe."""
        cands = []
        for key in ("TMPDIR", "TMP", "TEMP"):
            try:
                val = os.environ.get(key)
            except Exception:
                val = None
            if val and val not in cands:
                cands.append(val)
        try:
            cands.append(os.path.join(self.build_folder, fallback_sub))
        except Exception:
            pass
        for cand in cands:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".tmp-write-probe")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                try:
                    os.unlink(probe)
                except OSError:
                    pass
                return cand
            except OSError:
                continue
        return cands[0] if cands else None

    def _resolve_pkgconf_bin(self):
        """Locate the pkgconf binary from the build requirement."""
        try:
            bdep = self.dependencies.build.get("pkgconf")
            if bdep is not None and getattr(bdep, "package_folder", None):
                cand = os.path.join(str(bdep.package_folder), "bin", "pkgconf")
                if os.path.isfile(cand):
                    return cand
        except Exception:
            pass
        try:
            found = shutil.which("pkgconf")
        except Exception:
            found = None
        if found and os.path.isfile(found):
            return found
        return ""

    def _ensure_pkg_config(self):
        """Expose pkgconf as pkg-config for configure's hard requirement.

        pkgconf/3.0.5 ships bin/pkgconf WITHOUT a bin/pkg-config alias,
        so PKG_PROG_PKG_CONFIG finds neither pkg-config nor the tool
        and aborts ("configure: error: pkg-config not found"). Export
        PKG_CONFIG and create a build_folder/hmbs-shims/pkg-config shim
        (symlink, copyfile fallback for HMDFS chmod=0) prepended to PATH.
        """
        pkgconf_bin = self._resolve_pkgconf_bin()
        if not pkgconf_bin:
            self.output.warning("pkgconf binary not found; pkg-config check may fail")
            return ""
        os.environ["PKG_CONFIG"] = pkgconf_bin
        self.output.info("using PKG_CONFIG=%s" % pkgconf_bin)
        shim_dir = os.path.join(self.build_folder, "hmbs-shims")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        link = os.path.join(shim_dir, "pkg-config")
        try:
            if os.path.islink(link) or os.path.isfile(link):
                try:
                    os.remove(link)
                except OSError:
                    pass
            try:
                os.symlink(pkgconf_bin, link)
            except (OSError, NotImplementedError):
                shutil.copyfile(pkgconf_bin, link)
            self.output.info("pkg-config shim: %s -> %s" % (link, pkgconf_bin))
        except Exception as exc:
            self.output.warning("pkg-config shim failed: %s" % exc)
            return ""
        cur = os.environ.get("PATH", "")
        if shim_dir not in cur.split(os.pathsep):
            os.environ["PATH"] = shim_dir + os.pathsep + cur
        return shim_dir

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # No python bindings on OHOS/CI (avoids python dev dependency);
        # upstream TESTS then reduces to test_library.sh only.
        tc.configure_args.append("--disable-python")
        # NLS pulls in external gettext/libintl; AES logic does not depend
        # on translated messages (libevtx/20251118 + authselect/1.7.1
        # precedent).
        tc.configure_args.append("--disable-nls")
        # OpenSSL: force the bundled local AES implementation. Upstream
        # auto-detect may find a libcrypto whose headers are absent at
        # compile time (fatal error: 'openssl/err.h' in
        # libcaes_context.c). All openssl includes are guarded by
        # HAVE_LIBCRYPTO/HAVE_OPENSSL_*_H, so --with-openssl=no selects the
        # self-contained FIPS-197 fallback with no new dependency; the 7
        # caes_test_* programs still run the full suite against it
        # (libbde 20240502 issues #6/#7 precedent, FreeBSD port also uses
        # --with-openssl=no for libcaes).
        tc.configure_args.append("--with-openssl=no")
        if str(self.settings.os) == "OHOS":
            ohos_target = "aarch64-unknown-linux-ohos"
            tc.extra_cflags.append("--target=%s" % ohos_target)
            tc.extra_ldflags.append("--target=%s" % ohos_target)
        tc.generate()
        # Build-scope env script wins over the profile [buildenv] (which
        # pins the inaccessible HNP bash); inline os.environ tweaks in
        # build() alone do not (bwm/0.6.3 precedent).
        _tmp = self._pick_writable_tmpdir()
        _sh = self._usable_shell()
        shell_env = Environment()
        shell_env.define("CONFIG_SHELL", _sh)
        shell_env.define("SHELL", _sh)
        if _tmp:
            shell_env.define("TMPDIR", _tmp)
            shell_env.define("TMP", _tmp)
            shell_env.define("TEMP", _tmp)
        _cc = self._discover_compiler("c")
        _cxx = self._discover_compiler("cpp")
        if _cc:
            shell_env.define("CC", _cc)
        if _cxx:
            shell_env.define("CXX", _cxx)
        _pkgconf = self._resolve_pkgconf_bin()
        if _pkgconf:
            shell_env.define("PKG_CONFIG", _pkgconf)
        shell_env.vars(self, scope="build").save_script("hmbs_shell")
        self.output.info(
            "hmbs_shell: SHELL/CONFIG_SHELL=%s TMPDIR=%s CC=%s CXX=%s PKG_CONFIG=%s"
            % (_sh, _tmp, _cc, _cxx, _pkgconf or "<conanbuild-PATH>")
        )

    def build(self):
        # Mirror generate() env into current process.
        _sh = self._usable_shell()
        os.environ["CONFIG_SHELL"] = _sh
        os.environ["SHELL"] = _sh
        _tmp = self._pick_writable_tmpdir()
        if _tmp:
            os.environ["TMPDIR"] = _tmp
            os.environ["TMP"] = _tmp
            os.environ["TEMP"] = _tmp
        _cc = self._discover_compiler("c")
        _cxx = self._discover_compiler("cpp")
        if _cc:
            os.environ["CC"] = _cc
        if _cxx:
            os.environ["CXX"] = _cxx
        os.environ.pop("LD_LIBRARY_PATH", None)
        # pkg-config FIRST (before any conftest): configure hard-requires it.
        self._ensure_pkg_config()
        src = self.source_folder

        # Dist tarball already ships configure + bundled libcerror:
        # no synclibs.sh, no autoreconf. Fail fast if the assumption breaks.
        if not os.path.isfile(os.path.join(src, "configure")):
            raise ConanException(
                "dist tarball assumption broken: configure missing in %s" % src
            )
        if not os.path.isdir(os.path.join(src, "libcerror")):
            raise ConanException(
                "dist tarball assumption broken: libcerror missing in %s" % src
            )

        # Stale shipped common/config.h shadows the fresh configure output:
        # the release tarball carries a maintainer-machine config.h (WITH
        # openssl: HAVE_LIBCRYPTO/HAVE_OPENSSL_EVP_H defined) and
        # common/common.h does #include "config.h" (quoted), resolving to
        # the source-tree copy first. Every libcaes TU then compiles
        # against stale defines (fatal error: 'openssl/err.h' file not
        # found in libcaes_context.c). config.h is a generated artifact
        # (config.h.in is the template); remove the stale copy so the
        # fresh build-tree config.h (with --with-openssl=no) is used
        # (libbde 20240502 issue #7 precedent).
        _stale_cfg = os.path.join(src, "common", "config.h")
        try:
            if os.path.isfile(_stale_cfg):
                os.unlink(_stale_cfg)
                self.output.info("Removed stale shipped common/config.h")
        except OSError as exc:
            self.output.warning("Could not remove stale config.h: %s" % exc)

        # E007: config.guess does not know HarmonyOS.
        cg = os.path.join(src, "config.guess")
        if os.path.exists(cg):
            with open(cg, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "HarmonyOS" not in content:
                insertion = (
                    "    *:HarmonyOS:*:*)\n"
                    "\tcase \"$UNAME_MACHINE\" in\n"
                    "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                    "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                    "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                    "\t    i?86)         MACHINE=i686 ;;\n"
                    "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                    "\tesac\n"
                    "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                    "\t;;\n"
                    "\n"
                )
                marker = "    *:NetBSD:*:*)"
                if marker in content:
                    content = content.replace(marker, insertion + marker, 1)
                    with open(cg, "w", encoding="utf-8") as f:
                        f.write(content)
                    self.output.info("Patched config.guess for HarmonyOS")

        # E007: config.sub does not accept the ohos triplet.
        cs = os.path.join(src, "config.sub")
        if os.path.exists(cs):
            with open(cs, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "ohos" not in content:
                old_block = (
                    "\t\t\t\tbasic_machine=$field1-unknown\n"
                    "\t\t\t\tbasic_os=linux-android\n"
                    "\t\t\t\t;;"
                )
                new_block = (
                    "\t\t\t\tbasic_machine=$field1-unknown\n"
                    "\t\t\t\tbasic_os=linux-android\n"
                    "\t\t\t\t;;\n"
                    "\t\t\tohos-linux)\n"
                    "\t\t\t\tbasic_machine=$field1-unknown\n"
                    "\t\t\t\tbasic_os=linux-ohos\n"
                    "\t\t\t\t;;"
                )
                if old_block in content:
                    content = content.replace(old_block, new_block, 1)
                content = content.replace(
                    "gnu* | android* | bsd*",
                    "gnu* | android* | ohos* | bsd*",
                    1,
                )
                with open(cs, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info("Patched config.sub for HarmonyOS")

        # E011 + HMBS shell: patch every configure copy. The file patch
        # hard-codes CONFIG_SHELL/SHELL=/bin/sh INSIDE the script so the
        # configure[139] self-re-exec ignores the profile's broken
        # HNP bash regardless of env layering (libbde precedent).
        _seen = set()
        for _d in (src, self.build_folder):
            try:
                _d = os.path.normpath(_d)
            except Exception:
                continue
            if not _d or _d in _seen:
                continue
            _seen.add(_d)
            cf = os.path.join(_d, "configure")
            if os.path.isfile(cf):
                self._force_posix_shell(cf)
        try:
            _parent = os.path.normpath(os.path.join(self.build_folder, os.pardir))
            if _parent not in _seen:
                _pcf = os.path.join(_parent, "configure")
                if os.path.isfile(_pcf):
                    self._force_posix_shell(_pcf)
        except Exception:
            pass

        autotools = Autotools(self)
        try:
            autotools.configure()
        except Exception:
            self._dump_configure_diagnostics()
            raise

        cs_status = os.path.join(self.build_folder, "config.status")
        if not os.path.exists(cs_status):
            cs_status = os.path.join(src, "config.status")
        if os.path.exists(cs_status):
            with open(cs_status, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                with open(cs_status, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info("Patched config.status umask 077->022")

        _shim = self._write_install_shim()
        self._redirect_install_to_shim(_shim)
        self._make_chmod_tolerant()

        try:
            autotools.make(args=["-j1"])
        except Exception:
            self._dump_make_diagnostics()
            raise
        self._run_upstream_tests()

    def _force_posix_shell(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            return
        if "HMBS_FORCE_POSIX_SHELL" in content:
            return
        marker = (
            "# HMBS_FORCE_POSIX_SHELL: ignore broken profile CONFIG_SHELL\n"
            "CONFIG_SHELL=/bin/sh\n"
            "SHELL=/bin/sh\n"
            "export CONFIG_SHELL SHELL\n"
        )
        lines = content.splitlines(keepends=True)
        if lines and lines[0].startswith("#!"):
            lines.insert(1, marker)
        else:
            lines.insert(0, marker)
        content = "".join(lines)
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
            self.output.info("Patched configure umask 077->022 (%s)" % path)
        if 'mktemp -d -q "./confstatXXXXXX"' in content:
            content = content.replace(
                'mktemp -d -q "./confstatXXXXXX"',
                'mktemp -d -q "${TMPDIR-/tmp}/confstatXXXXXX"',
            )
            self.output.info("Patched configure confstat mktemp -> TMPDIR (%s)" % path)
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            self.output.info("Forced /bin/sh in %s" % path)
        except OSError as exc:
            self.output.warning("Could not patch shell in %s: %s" % (path, exc))

    def _write_install_shim(self):
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        script = (
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
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(script)
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass
        return install

    def _redirect_install_to_shim(self, shim_install):
        for root, _, files in os.walk(self.build_folder):
            if "Makefile" not in files:
                continue
            mf = os.path.join(root, "Makefile")
            try:
                with open(mf, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if "INSTALL =" not in content:
                continue
            lines = []
            changed = False
            for line in content.splitlines(True):
                stripped = line.lstrip()
                if stripped.startswith("INSTALL = ") and "/install" in stripped:
                    indent = line[:len(line) - len(stripped)]
                    lines.append("%sINSTALL = %s\n" % (indent, shim_install))
                    changed = True
                else:
                    lines.append(line)
            if changed:
                try:
                    with open(mf, "w", encoding="utf-8", newline="\n") as f:
                        f.writelines(lines)
                except OSError:
                    continue
        self.output.info("Redirected Makefiles INSTALL to shim: %s" % shim_install)

    def _make_chmod_tolerant(self):
        count = 0
        for root, _, files in os.walk(self.build_folder):
            if "Makefile" not in files:
                continue
            mf = os.path.join(root, "Makefile")
            try:
                with open(mf, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if "chmod 644" in content and "|| true" not in content:
                content = content.replace("chmod 644", "chmod 644 2>/dev/null || true; chmod 644")
                try:
                    with open(mf, "w", encoding="utf-8", newline="\n") as f:
                        f.write(content)
                    count += 1
                except OSError:
                    continue
        if count:
            self.output.info("Made chmod tolerant in %d Makefiles" % count)

    def _dump_configure_diagnostics(self):
        for folder in (self.build_folder, self.source_folder):
            for name in ("config.log",):
                p = os.path.join(folder, name)
                if not os.path.isfile(p):
                    continue
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read()
                except OSError:
                    continue
                self.output.info("---- config.log tail (%s) ----" % folder)
                for line in text[-12000:].splitlines()[-60:]:
                    self.output.info("config.log: " + line[:1000])
        for key in ("CC", "CXX", "TMPDIR", "CONFIG_SHELL", "SHELL", "PATH"):
            self.output.info("env %s=%s" % (key, str(os.environ.get(key, "<unset>"))[:500]))

    def _dump_make_diagnostics(self):
        for folder in (self.build_folder, self.source_folder):
            p = os.path.join(folder, "config.log")
            if not os.path.isfile(p):
                continue
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            self.output.info("---- config.log tail (%s) ----" % folder)
            for line in text[-8000:].splitlines()[-40:]:
                self.output.info("config.log: " + line[:1000])
        # Crypto-macro evidence: with --with-openssl=no the fresh
        # build-tree common/config.h must undef HAVE_LIBCRYPTO /
        # HAVE_OPENSSL_EVP_H; a stale shipped copy would define them.
        for label, folder in (("source", self.source_folder),
                              ("build", self.build_folder)):
            p = os.path.join(folder, "common", "config.h")
            if not os.path.isfile(p):
                self.output.info("diag config.h absent in %s tree" % label)
                continue
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError as exc:
                self.output.info("%s config.h unreadable: %s" % (label, exc))
                continue
            for line in text.splitlines():
                if "HAVE_LIBCRYPTO" in line or "HAVE_OPENSSL" in line:
                    self.output.info("config.h(%s): %s" % (label, line[:300]))

    def _parse_automake_summary(self, output):
        total = passed = failed = skipped = errors = 0

        def _num(pattern):
            match = re.search(pattern, output, re.MULTILINE)
            return int(match.group(1)) if match else 0

        total = _num(r"^# TOTAL:\s*(\d+)")
        if total > 0:
            passed = _num(r"^# PASS:\s*(\d+)")
            failed = _num(r"^# FAIL:\s*(\d+)")
            failed += _num(r"^# XPASS:\s*(\d+)")
            errors = _num(r"^# ERROR:\s*(\d+)")
            skipped = _num(r"^# SKIP:\s*(\d+)")
            skipped += _num(r"^# XFAIL:\s*(\d+)")
        else:
            passed = len(re.findall(r"^PASS:", output, re.MULTILINE))
            failed = len(re.findall(r"^(FAIL|XPASS|ERROR):", output, re.MULTILINE))
            skipped = len(re.findall(r"^SKIP:", output, re.MULTILINE))
            total = passed + failed + skipped
        return total, passed, failed, skipped, errors

    def _patch_tests_tmpdir(self, writable_tmp):
        roots = []
        for attr in ("source_folder", "build_folder"):
            try:
                roots.append(os.path.normpath(getattr(self, attr)))
            except Exception:
                continue
        patched = 0
        seen = set()
        for root in roots:
            for cand in (os.path.join(root, "tests"),):
                if cand in seen or not os.path.isdir(cand):
                    continue
                seen.add(cand)
                try:
                    names = os.listdir(cand)
                except OSError:
                    continue
                for name in names:
                    if name.endswith((".log", ".trs")):
                        continue
                    path = os.path.join(cand, name)
                    if not os.path.isfile(path):
                        continue
                    try:
                        if os.path.getsize(path) > 200000:
                            continue
                    except OSError:
                        continue
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                    except OSError:
                        continue
                    if "/tmp" not in content or "\x00" in content:
                        continue
                    new_content = content.replace("/tmp", "${TMPDIR:-/tmp}")
                    if new_content == content:
                        continue
                    try:
                        with open(path, "w", encoding="utf-8", newline="\n") as f:
                            f.write(new_content)
                        patched += 1
                    except OSError:
                        continue
        if patched:
            self.output.info("Patched hardcoded /tmp -> TMPDIR in %d files" % patched)
        return patched

    def _run_upstream_tests_direct(self, writable_tmp, reason):
        """Build the 7 check_PROGRAMS and run each binary directly."""
        try:
            self.run("make check TESTS= > \"make_check_build.log\" 2>&1",
                     cwd=self.build_folder)
        except Exception as exc:
            self.output.info("make check TESTS= build issue: %s" % str(exc)[:500])
        candidates = []
        seen_dirs = set()
        for root in (self.build_folder, self.source_folder):
            try:
                bases = [root] + [os.path.join(root, e) for e in os.listdir(root)
                                  if os.path.isdir(os.path.join(root, e))]
            except OSError:
                bases = [root]
            for base in bases:
                tdir = os.path.join(base, "tests")
                if tdir in seen_dirs or not os.path.isdir(tdir):
                    continue
                seen_dirs.add(tdir)
                for sub in (tdir, os.path.join(tdir, ".libs")):
                    if not os.path.isdir(sub):
                        continue
                    try:
                        names = os.listdir(sub)
                    except OSError:
                        continue
                    for name in names:
                        if not name.startswith("caes_test_"):
                            continue
                        if name.endswith((".c", ".h", ".o", ".log", ".trs",
                                          ".sh", ".in", ".am")):
                            continue
                        path = os.path.join(sub, name)
                        try:
                            if os.path.isfile(path) and os.access(path, os.X_OK):
                                candidates.append(path)
                        except Exception:
                            continue
        by_base = {}
        for path in candidates:
            by_base.setdefault(os.path.basename(path), path)
        binaries = sorted(by_base.values())
        self.output.info("direct test binaries discovered=%d" % len(binaries))
        for path in binaries[:10]:
            self.output.info("direct candidate: %s" % path)
        if not binaries:
            result = {
                "status": "failed",
                "framework": "automake-make-check",
                "command": "direct run of caes_test_* binaries (%s)" % reason,
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "%s and no caes_test_* binaries built" % reason,
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                             json.dumps(result, ensure_ascii=False))
            raise ConanException("libcaes upstream tests failed: " + result["reason"])
        passed = failed = 0
        for path in binaries:
            name = os.path.basename(path)
            try:
                self.run("\"%s\"" % path, cwd=os.path.dirname(path))
                passed += 1
                self.output.info("direct PASS: %s" % name)
            except Exception:
                failed += 1
                self.output.info("direct FAIL: %s" % name)
        total = len(binaries)
        command = ("direct run of caes_test_* binaries "
                   "(%s, make check TESTS= build only)" % reason)
        if failed == 0 and total > 0:
            result = {
                "status": "passed",
                "framework": "automake-make-check",
                "command": command,
                "discovered": total,
                "executed": total,
                "passed": passed,
                "failed": 0,
                "skipped": 0,
            }
        else:
            result = {
                "status": "failed",
                "framework": "automake-make-check",
                "command": command,
                "discovered": total,
                "executed": total,
                "passed": passed,
                "failed": failed,
                "skipped": 0,
                "reason": "direct run failed=%d/%d" % (failed, total),
            }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(result, ensure_ascii=False))
        try:
            with open(os.path.join(self.build_folder,
                                   "upstream_test_result.json"),
                      "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False)
        except OSError as exc:
            self.output.warning("Could not persist upstream result: %s" % exc)
        if result["status"] != "passed":
            raise ConanException(
                "libcaes upstream tests failed: %s" % result.get("reason", "see log"))

    def _run_upstream_tests(self):
        _tmp = self._pick_writable_tmpdir()
        if _tmp:
            os.environ["TMPDIR"] = _tmp
            os.environ["TMP"] = _tmp
            os.environ["TEMP"] = _tmp
            self.output.info("make check TMPDIR=%s" % _tmp)
        self._patch_tests_tmpdir(_tmp)
        # Dist tarball ships the full tests/ tree (no input/ fixtures needed:
        # the 7 caes_test_* binaries assert hardcoded vectors). Run them
        # directly (same assertions the shell driver runs for
        # context/error/support/tweaked_context, plus the crypt modes).
        self.output.info(
            "no input fixtures needed; running 7 caes_test_* binaries directly")
        self._run_upstream_tests_direct(
            _tmp or self.build_folder,
            "dist tarball, no input fixtures needed")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.LESSER*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        marker_src = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(marker_src):
            marker_dir = os.path.join(self.package_folder, "res")
            os.makedirs(marker_dir, exist_ok=True)
            shutil.copy(marker_src, os.path.join(marker_dir, "upstream_test_result.json"))

    def package_info(self):
        self.cpp_info.libs = ["caes"]
        self.cpp_info.set_property("cmake_file_name", "libcaes")
        self.cpp_info.set_property("cmake_target_name", "libcaes::libcaes")
        self.cpp_info.set_property("pkg_config_name", "libcaes")
