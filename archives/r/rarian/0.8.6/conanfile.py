#!/usr/bin/env python3
"""Conan recipe — rarian 0.8.6 (Autotools).

Documentation metadata library (Scrollkeeper replacement).
Upstream: https://gitlab.freedesktop.org/rarian/rarian
Build: autotools (configure + make). Core C library + C++ OMF reader.
tinyxml2 is built privately from the same-version upstream sources
(see conandata.yml `tinyxml2`): configure probes `-ltinyxml2` and
rarian-omf.cpp plus three util tools include tinyxml2.h, but resolving
tinyxml2/11.0.0 from the remotes makes preflight fetch the conancenter
recipe first and build it from source, which fails on OHOS. The private
static lib (always -fPIC) is shipped as libtinyxml2.a for static
consumers; it stays out of the public headers.
xsltproc is an optional runtime helper for one compat script
(configure degrades gracefully when absent, so no libxslt requires).
Tests: libcheck-based `make check` (TESTS=check_rarian, 29 START_TEST cases).
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class RarianConan(ConanFile):
    name = "rarian"
    version = "0.8.6"
    description = "Documentation metadata library based on the Freedesktop spec (Scrollkeeper replacement)"
    license = "LGPL-2.1-only"
    homepage = "https://rarian.freedesktop.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "rarian supports Linux and OHOS, not %s" % self.settings.os
            )

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.5")
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(self, **self.conan_data["tinyxml2"],
            destination=os.path.join(self.source_folder, "deps", "tinyxml2"),
            strip_root=True)

    def _tinyxml2_dirs(self):
        """(sources, include dir, lib dir) of the private tinyxml2 build."""
        src = os.path.join(self.source_folder, "deps", "tinyxml2")
        prefix = os.path.join(self.build_folder, "tinyxml2")
        return src, os.path.join(prefix, "include"), os.path.join(prefix, "lib")

    def _dep_folder(self, name, *parts):
        """Find a dependency package dir fragment across test/host/build contexts."""
        for ctx in (self.dependencies.test, self.dependencies.host, self.dependencies.build):
            try:
                dep = ctx[name]
            except KeyError:
                continue
            return os.path.join(dep.package_folder, *parts)
        return None

    def _check_lib_preload(self, check_lib):
        """Locate libcheck.so absolute path for LD_PRELOAD (OHOS loader fallback)."""
        if not check_lib or not os.path.isdir(check_lib):
            return None
        direct = os.path.join(check_lib, "libcheck.so")
        if os.path.isfile(direct):
            return direct
        try:
            for _name in sorted(os.listdir(check_lib)):
                if _name == "libcheck.so" or _name.startswith("libcheck.so."):
                    _cand = os.path.join(check_lib, _name)
                    if os.path.isfile(_cand):
                        return _cand
        except OSError:
            return None
        return None

    def _resolve_shell(self):
        # Never trust CONFIG_SHELL: the shared profile exports
        # CONFIG_SHELL=/data/service/hnp/bin/bash which is inaccessible on
        # the migrated true device (preflight: configure[137] re-exec dies
        # with "inaccessible or not found", Error 127). HMBS guarantees
        # shell=/bin/sh and injects SHELL=/bin/sh, so prefer that (light
        # existence check only, no subprocess probing); bare "sh" via
        # HMBS-prepended PATH is the fallback. Adapted from zurl/1.12.0
        # _resolve_shell (notes #30, libdatovka precedent).
        for _cand in ("/bin/sh", os.environ.get("SHELL"), "sh"):
            if not _cand:
                continue
            # Never return the migrated HNP path even if it exists in some
            # environment (preflight evidence: /data/service/hnp/bin/bash
            # is inaccessible on the true device, Error 127).
            if _cand.startswith("/data/service/hnp/"):
                continue
            if _cand == "sh" or (os.path.isfile(_cand)
                                 and os.access(_cand, os.X_OK)):
                return _cand
        _which_sh = shutil.which("sh")
        if _which_sh:
            return _which_sh
        _which_bash = shutil.which("bash")
        if _which_bash:
            return _which_bash
        return "/bin/sh"

    def _scrub_poisoned_shell(self, root):
        # Replace poisoned-shell literals in configure-generated scripts.
        # Even with a clean env, an already-generated config.status/libtool/
        # Makefile can carry the bad absolute shell literally. Replace every
        # occurrence of the evidence-based bad values with the good shell,
        # in the well-known file names only; other files are never touched.
        # Idempotent (no-op when absent). Adapted from zurl/1.12.0.
        try:
            good = self._resolve_shell()
        except Exception:
            good = "/bin/sh"
        bad = set()
        inherited = os.environ.get("CONFIG_SHELL")
        if inherited and inherited != good:
            bad.add(inherited)
        # Evidence this round (preflight log): rarian configure[137]
        # re-exec hit exactly this profile [buildenv] path; the profile
        # value may not be visible in os.environ, so keep the log-evidenced
        # literal as well.
        if "/data/service/hnp/bin/bash" != good:
            bad.add("/data/service/hnp/bin/bash")
        if not bad or not root or not os.path.isdir(root):
            return
        names = {"configure", "config.status", "libtool", "Makefile"}
        for _dir, _dirs, _files in os.walk(root):
            for _name in _files:
                if _name not in names:
                    continue
                _path = os.path.join(_dir, _name)
                try:
                    with open(_path, "r", encoding="utf-8", errors="replace") as _f:
                        _content = _f.read()
                except (OSError, UnicodeDecodeError):
                    continue
                _fixed = _content
                for _b in bad:
                    _fixed = _fixed.replace(_b, good)
                if _fixed != _content:
                    try:
                        with open(_path, "w", encoding="utf-8", newline="\n") as _f:
                            _f.write(_fixed)
                        self.output.info("HMBS diag scrubbed poisoned shell in %s" % _path)
                    except (OSError, UnicodeDecodeError):
                        continue

    def _harden_configure_shell(self, configure_path, good):
        # Hardcode CONFIG_SHELL/SHELL inside the configure script itself so
        # the autoconf re-exec (`exec $CONFIG_SHELL ...` around line 137)
        # uses the good shell even when the outer conanbuild.sh (sourced by
        # Autotools helper / self.run env=conanbuild) still re-exports the
        # poisoned profile value AFTER our Environment define (zurl #30
        # evidence). Idempotent: marker block refreshed, never duplicated.
        try:
            _path = os.fspath(configure_path)
        except Exception:
            return
        if not os.path.isfile(_path):
            return
        try:
            with open(_path, "r", encoding="utf-8", errors="replace") as _f:
                _cur = _f.read()
        except (OSError, UnicodeDecodeError):
            return
        for _b in ("/data/service/hnp/bin/bash",):
            if _b != good:
                _cur = _cur.replace(_b, good)
        _marker = "HMBS_SHELL_HARDEN"
        _block = ("# %s: force usable shell on migrated device\n"
                  "CONFIG_SHELL='%s'; export CONFIG_SHELL\n"
                  "SHELL='%s'; export SHELL\n" % (_marker, good, good))
        if _marker in _cur:
            _new = re.sub(
                r"# HMBS_SHELL_HARDEN.*?\nCONFIG_SHELL='.*?'; export CONFIG_SHELL\nSHELL='.*?'; export SHELL\n",
                _block, _cur, flags=re.DOTALL)
        else:
            _lines = _cur.splitlines(keepends=True)
            if _lines and _lines[0].startswith("#!"):
                _new = _lines[0] + _block + "".join(_lines[1:])
            else:
                _new = _block + _cur
        if _new != _cur:
            try:
                with open(_path, "w", encoding="utf-8", newline="\n") as _f:
                    _f.write(_new)
                self.output.info("HMBS diag hardened shell in %s -> %s" % (_path, good))
            except (OSError, UnicodeDecodeError) as e:
                self.output.warning("HMBS diag harden write failed %s: %s" % (_path, e))

    def _resolve_compiler(self, configured, names):
        # Tool-specific candidates only: never fall back from C to C++
        # names or vice versa. Prefer the profile's configured absolute
        # path when it exists and is executable (CI workers); otherwise
        # resolve via PATH (true device migrated clang from
        # /data/service/hnp/bin to ~/usr/local/bin) or the
        # ~/usr/local/bin fallback. Adapted from zydis/4.1.1.
        if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local", "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.isfile(cand):
                return cand
        return configured or names[0]

    def _usable_compilers(self):
        try:
            compilers = self.conf.get("tools.build:compiler_executables", default={})
        except Exception:
            compilers = {}
        if not isinstance(compilers, dict):
            compilers = {}
        cxx = self._resolve_compiler(compilers.get("cpp"), ("clang++", "c++"))
        cc = self._resolve_compiler(compilers.get("c"), ("clang", "cc"))
        ar = self._resolve_compiler(compilers.get("ar"), ("llvm-ar", "ar"))
        return cc, cxx, ar, compilers

    def _fix_generated_autotools_compiler(self, configured_map, cc, cxx):
        # The shared profile still points at /data/service/hnp/bin/clang
        # which is inaccessible on the migrated true device; AutotoolsToolchain
        # embeds that dead path into conanautotools.sh. Rewrite the generated
        # artifacts in place (only when the configured path is missing and
        # the resolved one exists; CI workers untouched). Same intent as
        # zydis/4.1.1 _fix_generated_toolchain_compiler but for autotools.
        if not isinstance(configured_map, dict):
            configured_map = {}
        pairs = []
        for key, resolved in (("c", cc), ("cpp", cxx)):
            old = configured_map.get(key)
            if old and resolved and old != resolved and not (
                    os.path.isfile(old) and os.access(old, os.X_OK)):
                try:
                    if os.path.isfile(resolved) or shutil.which(resolved):
                        pairs.append((old, resolved))
                except Exception:
                    continue
        if not pairs:
            return
        try:
            gf = getattr(self, "generators_folder", None)
            if gf and os.path.isdir(gf):
                for root, _ds, files in os.walk(gf):
                    for fn in files:
                        p = os.path.join(root, fn)
                        try:
                            with open(p, "r", encoding="utf-8", errors="replace") as f:
                                text = f.read()
                        except Exception:
                            continue
                        orig = text
                        for old_p, new_p in pairs:
                            text = text.replace(old_p, new_p)
                        if text != orig:
                            try:
                                with open(p, "w", encoding="utf-8") as f:
                                    f.write(text)
                                self.output.info("HMBS diag fixed generated file %s" % p)
                            except Exception as e:
                                self.output.warning("HMBS diag fix write failed %s: %s" % (p, e))
        except Exception as e:
            self.output.warning("HMBS diag autotools toolchain fix failed: %s" % e)
        try:
            comp_env = Environment()
            for old_p, new_p in pairs:
                if new_p == cc:
                    comp_env.define("CC", new_p)
                if new_p == cxx:
                    comp_env.define("CXX", new_p)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as e:
            self.output.warning("HMBS diag compiler env export failed: %s" % e)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        _, inc, lib = self._tinyxml2_dirs()
        # Expose the privately built tinyxml2 to configure compile/link
        # probes (`-ltinyxml2` + `#include <tinyxml2.h>`) and to the
        # librarian/util/tools builds. RARIAN_LIBS itself is hardcoded
        # by upstream configure.ac, so only the search paths are ours.
        tc.cflags.append("-I%s" % inc)
        tc.cxxflags.append("-I%s" % inc)
        tc.ldflags.append("-L%s" % lib)
        # librarian.a + vendored libtinyxml2.a both contain C++ objects
        # (rarian-omf.cpp, tinyxml2.cpp), but the util tools
        # (rarian-example, rarian-sk-*) are C sources so libtool links
        # them with --tag=CC (clang). The C driver does not pull the C++
        # runtime, hence __gxx_personality_v0 / operator new/delete /
        # __cxxabiv1 undefined symbols at util link (this round's
        # preflight evidence). Link the runtime explicitly: libc++ on
        # OHOS (profile compiler.libcxx=libc++, freeimage precedent
        # uses -lc++ on device), libstdc++ on Linux.
        tc.ldflags.append("-lc++" if self.settings.os == "OHOS" else "-lstdc++")
        # HMBS OOM mitigation (true-device `rm: Out of memory` in compile
        # phase): additively lower optimization and strip debug info on OHOS
        # only. Appended last so -O1/-g0 win over profile -O2/-g without
        # overwriting profile flags; keeps --with-check and all assertions.
        if self.settings.os == "OHOS":
            for _flag in ("-O1", "-g0"):
                if _flag not in tc.cflags:
                    tc.cflags.append(_flag)
                if _flag not in tc.cxxflags:
                    tc.cxxflags.append(_flag)
        tc.configure_args.extend([
            "--disable-skdb-update",
            "--disable-dependency-tracking",
            "--with-check",
            "--localstatedir=${prefix}/var",
        ])
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()
        try:
            _cc, _cxx, _ar, _confmap = self._usable_compilers()
            self.output.info("HMBS diag compilers cc=%s cxx=%s ar=%s" % (_cc, _cxx, _ar))
            self._fix_generated_autotools_compiler(_confmap, _cc, _cxx)
        except Exception as e:
            self.output.warning("HMBS diag compiler resolve failed: %s" % e)
        try:
            # Build-scope shell override: the shared profile bakes
            # CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash into conanbuild.sh,
            # which is inaccessible on the migrated device (this round:
            # configure[137] re-exec Error 127). A build-scope save_sh lands
            # in the conanbuild aggregation and overwrites the profile value
            # for every build() subprocess (zurl #30 pattern); the configure
            # file itself is additionally hardened in build().
            _shell = self._resolve_shell()
            self.output.info("HMBS diag shell=%s" % _shell)
            _shell_env = Environment()
            _shell_env.define("CONFIG_SHELL", _shell)
            _shell_env.define("SHELL", _shell)
            _shell_env.vars(self, scope="build").save_sh("hmbs_shell")
            # Belt-and-braces: scrub any poisoned literal already baked into
            # generated files (conanautotools.sh carries compiler paths; the
            # shell literal can appear there via profile expansion).
            self._scrub_poisoned_shell(getattr(self, "generators_folder", None))
        except Exception as e:
            self.output.warning("HMBS diag shell env export failed: %s" % e)
        try:
            # HMBS OOM mitigation, build-scope part: additively append
            # -O1 -g0 to CFLAGS/CXXFLAGS for OHOS only. Uses append (never
            # define) so profile flags are kept and ours win by position.
            if self.settings.os == "OHOS":
                _oom_env = Environment()
                _oom_env.append("CFLAGS", " -O1 -g0")
                _oom_env.append("CXXFLAGS", " -O1 -g0")
                _oom_env.vars(self, scope="build").save_sh("hmbs_oom")
                self.output.info("HMBS diag saved hmbs_oom CFLAGS/CXXFLAGS -O1 -g0")
        except Exception as e:
            self.output.warning("HMBS diag oom env export failed: %s" % e)

    def _build_environment(self):
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.define("PKG_CONFIG", "pkgconf")
        # Private vendored tinyxml2 (see _build_vendored_tinyxml2): expose
        # it through every probe mechanism upstream configure may use.
        # The -I/-L pair is already baked into conanautotools.sh at
        # generate() time, but a PKG_CHECK_MODULES-style probe only honors
        # pkg-config files / TINYXML2_CFLAGS+LIBS overrides, and an
        # AC_CHECK_HEADERS probe only honors CPPFLAGS. Belt-and-braces on
        # all of them; the .pc file itself is written by
        # _build_vendored_tinyxml2 into generators_folder (already on
        # PKG_CONFIG_PATH above) before configure runs.
        try:
            _, _tinc, _tlib = self._tinyxml2_dirs()
            env.append("CPPFLAGS", " -I%s" % _tinc)
            env.append("CFLAGS", " -I%s" % _tinc)
            env.append("CXXFLAGS", " -I%s" % _tinc)
            env.append("LDFLAGS", " -L%s" % _tlib)
            env.define("TINYXML2_CFLAGS", "-I%s" % _tinc)
            env.define("TINYXML2_LIBS", "-L%s -ltinyxml2" % _tlib)
        except Exception:
            pass
        # Same C++ runtime as generate()'s toolchain ldflags, but via env
        # so it also covers the configure probes and any direct
        # libtool --tag=CC link. LIBS is appended after objects by
        # automake (LINK = ... objects LIBS), which guarantees correct
        # static-archive order (runtime after -ltinyxml2); LDFLAGS alone
        # would sort before objects.
        try:
            _cxx_rt = "-lc++" if str(self.settings.os) == "OHOS" else "-lstdc++"
            env.append("LDFLAGS", " %s" % _cxx_rt)
            env.append("LIBS", " %s" % _cxx_rt)
        except Exception:
            pass
        # Never reuse the poisoned profile shell: resolve the HMBS-guaranteed
        # usable shell (/bin/sh preferred) and overwrite both variables so
        # the transient build() env is clean (the persistent conanbuild
        # override lives in generate()'s hmbs_shell.sh; the configure file
        # itself is hardened in build() for the inline-wins case).
        try:
            _good_shell = self._resolve_shell()
        except Exception:
            _good_shell = "/bin/sh"
        env.define("SHELL", _good_shell)
        env.define("CONFIG_SHELL", _good_shell)
        try:
            _cc, _cxx, _ar, _confmap = self._usable_compilers()
            old_c = _confmap.get("c") if isinstance(_confmap, dict) else None
            old_cxx = _confmap.get("cpp") if isinstance(_confmap, dict) else None
            if _cc and old_c and _cc != old_c:
                env.define("CC", _cc)
            if _cxx and old_cxx and _cxx != old_cxx:
                env.define("CXX", _cxx)
        except Exception:
            pass
        # Reuse the HMBS-injected writable tmp when present (task-independent
        # TMPDIR/TMP/TEMP plus the official autoconf mktemp fallback); only
        # fall back to a build-local tmp. Never invent /tmp (readonly on
        # device) and never borrow HMBS_INSTALL (install staging, not temp).
        tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
               or os.environ.get("TEMP") or "")
        try:
            _mktemp_fb = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        except Exception:
            _mktemp_fb = None
        if _mktemp_fb and _mktemp_fb not in ("0", "1") and os.path.isdir(_mktemp_fb):
            tmp = _mktemp_fb
        if not tmp or not os.path.isdir(tmp):
            tmp = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmp, exist_ok=True)
        except OSError:
            tmp = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmp, exist_ok=True)
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        return env

    @staticmethod
    def _patch_configure_umask(configure_path):
        configure_path = os.fspath(configure_path)
        with open(configure_path, "r", encoding="utf-8", newline="") as handle:
            content = handle.read()
        content = content.replace("umask 077", "umask 022")
        with open(configure_path, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)

    def _patch_config_guess_sub_for_ohos(self, root):
        # E007/E072: rarian 0.8.6 ships GNU config.guess 2023-06-23 which
        # has no HarmonyOS branch; `uname -s` = HarmonyOS falls through to
        # "unable to guess system type" and configure aborts with
        # "cannot guess build type; you must specify one" (this round's
        # preflight evidence). Portability fix, no --build/--host bypass
        # (iron-rules R1/E007 forbid it: bypass misdetects cross-build and
        # skips AC_RUN_IFELSE, producing a wrong config.h). Mirrors
        # scripts/patch-autotools-ohos.pl (5 edits) in tolerant Python so
        # it applies to this tarball's exact script vintage. Idempotent:
        # each edit checks for its marker before touching the file.
        if not root or not os.path.isdir(root):
            return
        guess_files, sub_files = [], []
        for _dir, _dirs, _files in os.walk(root):
            for _name in _files:
                if _name == "config.guess":
                    guess_files.append(os.path.join(_dir, _name))
                elif _name == "config.sub":
                    sub_files.append(os.path.join(_dir, _name))
        for _path in guess_files:
            try:
                with open(_path, "r", encoding="utf-8", errors="replace") as _f:
                    _c = _f.read()
            except OSError:
                continue
            _orig = _c
            if "__OHOS__" not in _c:
                _c = re.sub(
                    r"(#\s*if\s+defined\s*\(\s*__ANDROID__\s*\)[^\n]*\n\s*LIBC=android)",
                    r"\1\n#elif defined(__OHOS__)\n    LIBC=ohos",
                    _c, count=1)
            if "HarmonyOS" not in _c:
                _block = (
                    "    *:HarmonyOS:*:*)\n"
                    "\tcase \"$UNAME_MACHINE\" in\n"
                    "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                    "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                    "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                    "\t    i?86)         MACHINE=i686 ;;\n"
                    "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                    "\tesac\n"
                    "\techo \"${MACHINE}-unknown-linux-ohos\"\n"
                    "\texit ;;\n"
                )
                _c, _n = re.subn(
                    r"(^[ \t]*\*+:NetBSD:\*:\*\)[ \t]*\n)",
                    _block + r"\1", _c, count=1, flags=re.MULTILINE)
                if not _n:
                    self.output.warning(
                        "HMBS diag config.guess HarmonyOS insert point not found in %s" % _path)
            if _c != _orig:
                try:
                    with open(_path, "w", encoding="utf-8", newline="\n") as _f:
                        _f.write(_c)
                    self.output.info("HMBS diag patched config.guess HarmonyOS in %s" % _path)
                except OSError as e:
                    self.output.warning("HMBS diag config.guess write failed %s: %s" % (_path, e))
        for _path in sub_files:
            try:
                with open(_path, "r", encoding="utf-8", errors="replace") as _f:
                    _c = _f.read()
            except OSError:
                continue
            _orig = _c
            if "ohos-linux" not in _c:
                _m = re.search(
                    r"android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n\s*basic_os=linux-android\s*\n\s*;;",
                    _c)
                if _m:
                    _ins = (_m.group(0)
                            + "\n\t\tohos-linux)\n"
                            + "\t\t\tbasic_machine=$field1-unknown\n"
                            + "\t\t\tbasic_os=linux-ohos\n"
                            + "\t\t\t;;")
                    _c = _c[:_m.start()] + _ins + _c[_m.end():]
                else:
                    self.output.warning(
                        "HMBS diag config.sub ohos-linux insert point not found in %s" % _path)
            if not re.search(r"gnu\*\s*\|\s*android\*\s*\|\s*ohos\*", _c):
                _c = re.sub(r"(gnu\*\s*\|\s*android\*)", r"\1 | ohos*", _c, count=1)
            if not re.search(r"linux-ohos\*", _c):
                _c2, _n = re.subn(
                    r"linux-uclibc\*-\s*\)", "linux-uclibc*- | linux-ohos*- )", _c, count=1)
                if _n:
                    _c = _c2
                else:
                    _c2, _n = re.subn(
                        r"(linux-uclibc\*/?)\s*\)", r"\1 | linux-ohos*)", _c, count=1)
                    if _n:
                        _c = _c2
                    else:
                        self.output.warning(
                            "HMBS diag config.sub linux-ohos kernel insert point not found in %s" % _path)
            if _c != _orig:
                try:
                    with open(_path, "w", encoding="utf-8", newline="\n") as _f:
                        _f.write(_c)
                    self.output.info("HMBS diag patched config.sub ohos in %s" % _path)
                except OSError as e:
                    self.output.warning("HMBS diag config.sub write failed %s: %s" % (_path, e))

    def _build_vendored_tinyxml2(self):
        """Compile upstream tinyxml2 sources to a private static lib.

        Same 11.0.0 tarball the repo's tinyxml2 recipe uses (URL + sha256
        in conandata.yml). Two-file library, built with the Conan
        configured C++ compiler (R33: from conf, never ${CXX}); always
        -fPIC so the objects also link into a shared librarian.
        """
        src, inc, lib = self._tinyxml2_dirs()
        os.makedirs(inc, exist_ok=True)
        os.makedirs(lib, exist_ok=True)
        cpp = os.path.join(src, "tinyxml2.cpp")
        header = os.path.join(src, "tinyxml2.h")
        if not os.path.isfile(cpp) or not os.path.isfile(header):
            raise ConanInvalidConfiguration(
                "vendored tinyxml2 sources missing in %s" % src)
        # Dict-first access (fzy/1.1 merged pattern): the ":cpp" subkey
        # form raises "[conf] ... does not exist" on the preflight conan
        # when the conf is absent instead of falling back to default.
        # Validate executability: the shared profile still points at
        # /data/service/hnp/bin/clang++ which is inaccessible on the
        # migrated true device (preflight: "inaccessible or not found").
        # _resolve_compiler prefers the conf path when usable, else PATH.
        _cc, cxx, ar, _confmap = self._usable_compilers()
        self.output.info("HMBS diag tinyxml2 cxx=%s ar=%s" % (cxx, ar))
        obj = os.path.join(lib, "tinyxml2.o")
        archive = os.path.join(lib, "libtinyxml2.a")
        # HMBS OOM mitigation: build vendored tinyxml2 with reduced
        # optimization and no debug info (-O1 -g0) instead of -O2. Keeps
        # -fPIC so objects still link into shared librarian.
        self.run('"%s" -O1 -g0 -fPIC -std=c++11 -c "%s" -o "%s"' % (cxx, cpp, obj))
        self.run('"%s" rcs "%s" "%s"' % (ar, archive, obj))
        copy(self, "tinyxml2.h", src=src, dst=inc, keep_path=False)
        # Upstream 0.8.3+ links the *system* tinyxml2, so configure probes
        # for it (preflight 2026-09-28: `checking for tinyxml2... no`). The
        # -I/-L toolchain flags alone cannot satisfy a PKG_CHECK_MODULES
        # probe, and this private lib is not a Conan requirement, so no
        # PkgConfigDeps .pc exists for it. Write a minimal tinyxml2.pc
        # into generators_folder (already on PKG_CONFIG_PATH via
        # _build_environment) before configure runs. Version matches the
        # vendored 11.0.0 tarball (see conandata.yml).
        try:
            _gf = getattr(self, "generators_folder", None)
            if _gf and os.path.isdir(_gf):
                _pc = os.path.join(_gf, "tinyxml2.pc")
                _prefix = os.path.join(self.build_folder, "tinyxml2")
                with open(_pc, "w", encoding="utf-8", newline="\n") as _f:
                    _f.write(
                        "prefix=%s\n"
                        "libdir=${prefix}/lib\n"
                        "includedir=${prefix}/include\n"
                        "\n"
                        "Name: tinyxml2\n"
                        "Description: Private vendored tinyxml2 for rarian (not a system package)\n"
                        "Version: 11.0.0\n"
                        "Libs: -L${libdir} -ltinyxml2\n"
                        "Cflags: -I${includedir}\n" % _prefix)
                self.output.info("HMBS diag wrote tinyxml2.pc to %s" % _pc)
        except OSError as e:
            self.output.warning("HMBS diag tinyxml2.pc write failed: %s" % e)
        self.output.info("HMBS diag tinyxml2 lib=%s inc=%s exists=%s,%s"
                         % (archive, os.path.join(inc, "tinyxml2.h"),
                            os.path.isfile(archive),
                            os.path.isfile(os.path.join(inc, "tinyxml2.h"))))

    def _emit_upstream_marker(self, discovered, executed, passed, failed, skipped, command, reason="", gaps=None):
        payload = {
            "status": "passed" if (failed == 0 and executed > 0) else ("failed" if failed > 0 else "skipped"),
            "framework": "automake",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if reason:
            payload["reason"] = reason
        if gaps:
            payload["gaps"] = gaps
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(payload, separators=(",", ":")))

    def _parse_check_log(self, path):
        """Parse the libcheck summary line: `Checks: N, Failures: F, Errors: E`.

        Single deterministic source for case-level counts. Returns
        (checks, failures, errors) or (None, None, None) when absent.
        """
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        matches = re.findall(
            r"Checks:\s*(\d+)\s*,\s*Failures:\s*(\d+)\s*,\s*Errors:\s*(\d+)",
            content,
        )
        if not matches:
            return None, None, None
        checks, failures, errors = (int(v) for v in matches[-1])
        return checks, failures, errors

    def _collect_failure_evidence(self, path, limit=20):
        """Extract failing-case lines from a libcheck log (deterministic).

        Single source: the check_rarian.log file itself. Collects lines
        carrying libcheck failure markers (`:F:` / `:E:` verdict lines and
        `Failure` detail lines) in file order, truncated to `limit`.
        No counting, no arithmetic fixups — pure evidence excerpt.
        """
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                lines = handle.read().splitlines()
        except OSError:
            return []
        evidence = []
        for line in lines:
            stripped = line.strip()
            if ":F:" in line or ":E:" in line:
                evidence.append(stripped[:500])
            elif stripped.startswith("Failure") or "Assertion" in stripped:
                evidence.append(stripped[:500])
            if len(evidence) >= limit:
                break
        return evidence

    def _run_upstream_tests(self, autotools):
        command = "make -j1 check"
        if not can_run(self):
            self._emit_upstream_marker(
                29, 0, 0, 0, 29, command,
                reason="cross-building: built check_rarian but skipped execution",
            )
            self.output.warning("Built upstream test program but skipped execution while cross-building")
            return
        # make check exits non-zero when any automake TEST fails (this
        # round: FAIL 1). Must not abort before emitting the deterministic
        # marker: catch the error, keep the real logs, parse counts from
        # check_rarian.log, and report gaps explicitly.
        # Runtime env for the libcheck test program: check/0.15.2 is a
        # test_requires whose lib dir is not on the loader path by default,
        # so ./check_rarian dies with "Error loading shared library
        # libcheck.so" + relocation failures (exit 127) before printing the
        # libcheck summary (this round's preflight evidence). Expose it only
        # for the check invocation (radvd/2.20 precedent): LD_LIBRARY_PATH
        # for Linux, plus LD_PRELOAD to the absolute libcheck.so when the
        # OHOS loader ignores LD_LIBRARY_PATH (HMBS stale_runtime_library
        # diagnosis). Scoped to make check, never to configure/compile.
        _check_error = None
        _check_env = Environment()
        try:
            _check_lib = self._dep_folder("check", "lib")
            if _check_lib and os.path.isdir(_check_lib):
                _check_env.prepend_path("LD_LIBRARY_PATH", _check_lib)
                self.output.info("HMBS diag check lib dir=%s" % _check_lib)
                try:
                    _preload = self._check_lib_preload(_check_lib)
                except Exception:
                    _preload = None
                if _preload and str(self.settings.os) == "OHOS":
                    _check_env.define("LD_PRELOAD", _preload)
                    self.output.info("HMBS diag LD_PRELOAD=%s" % _preload)
        except Exception as _e:
            self.output.warning("HMBS diag check runenv setup failed: %s" % _e)
        try:
            with _check_env.vars(self).apply():
                autotools.make(target="check", args=["-j1"])
        except Exception as e:
            _check_error = e
            self.output.warning("HMBS diag make check failed (keeping logs): %s" % e)
        candidates = [
            os.path.join(self.build_folder, "tests", "check_rarian.log"),
            os.path.join(self.source_folder, "tests", "check_rarian.log"),
            os.path.join(self.build_folder, "check_rarian.log"),
        ]
        check_log = next((p for p in candidates if os.path.isfile(p)), None)
        if check_log is None:
            # Recursive fallback: automake out-of-source layouts may place
            # the log one level deeper. Walk build/source trees once.
            for _root in (getattr(self, "build_folder", ""), getattr(self, "source_folder", "")):
                if not _root or not os.path.isdir(_root):
                    continue
                for _dir, _dirs, _files in os.walk(_root):
                    if "check_rarian.log" in _files:
                        check_log = os.path.join(_dir, "check_rarian.log")
                        break
                if check_log is not None:
                    break
        # Always dump the automake program-level summary for evidence,
        # even when make check itself failed.
        try:
            for _root in (getattr(self, "build_folder", ""), getattr(self, "source_folder", "")):
                if not _root or not os.path.isdir(_root):
                    continue
                _suite = os.path.join(_root, "tests", "test-suite.log")
                if os.path.isfile(_suite):
                    with open(_suite, "r", encoding="utf-8", errors="replace") as _f:
                        _content = _f.read()
                    self.output.info("HMBS diag test-suite.log (%s):\n%s" % (_suite, _content[-4000:]))
                    break
        except Exception as e:
            self.output.warning("HMBS diag test-suite.log dump failed: %s" % e)
        if check_log is None:
            self._emit_upstream_marker(
                29, 0, 0, 0, 29, command,
                reason="check_rarian.log not found; searched %s" % ", ".join(candidates),
            )
            raise ConanInvalidConfiguration("upstream check_rarian.log not found after make check")
        checks, failures, errors = self._parse_check_log(check_log)
        if checks is None:
            self._emit_upstream_marker(
                29, 0, 0, 0, 29, command,
                reason="could not parse 'Checks/Failures/Errors' from %s" % check_log,
            )
            raise ConanInvalidConfiguration("could not parse %s" % check_log)
        # Single source: libcheck summary line. discovered=29 is the audited
        # START_TEST total (see test_package/MANIFEST.yml); executed/passed/
        # failed all derive from this one line, no string counting or fixups.
        executed = checks
        failed = failures + errors
        passed = executed - failed
        skipped = 29 - executed
        if skipped < 0:
            self._emit_upstream_marker(
                29, executed, passed, failed, 0, command,
                reason="check log reports %d checks but audit total is 29: %s" % (executed, check_log),
            )
            raise ConanInvalidConfiguration("check count exceeds audited total")
        gaps = None
        if failed > 0 or skipped > 0:
            _evidence = self._collect_failure_evidence(check_log)
            self.output.info("HMBS diag check_rarian.log (%s) failures=%d errors=%d evidence=%s"
                             % (check_log, failures, errors, json.dumps(_evidence[:8], ensure_ascii=False)))
            if failed > 0:
                _detail = "; ".join(_evidence[:4]) if _evidence else "libcheck reports %d failure(s)+%d error(s); see %s" % (failures, errors, check_log)
                gaps = [{
                    "count": failed,
                    "category": "test_failure",
                    "detail": "make check FAIL 1: %s" % _detail[:800],
                    "evidence": "tests/check_rarian.log Checks:%d Failures:%d Errors:%d in %s" % (checks, failures, errors, check_log),
                }]
        self._emit_upstream_marker(29, executed, passed, failed, skipped, command, gaps=gaps)

    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_umask(os.path.join(self.source_folder, "configure"))
        self._patch_config_guess_sub_for_ohos(self.source_folder)
        try:
            _good = self._resolve_shell()
        except Exception:
            _good = "/bin/sh"
        # Scrub poisoned literals carried in the release tarball, then
        # hardcode the good shell inside configure so its re-exec survives
        # a poisoned outer conanbuild.sh (zurl #30 inline-wins pattern).
        # Also clean this process env so any child inheriting os.environ
        # (not only the transient Environment context) sees the good shell.
        os.environ["CONFIG_SHELL"] = _good
        os.environ["SHELL"] = _good
        self._scrub_poisoned_shell(self.source_folder)
        self._harden_configure_shell(os.path.join(self.source_folder, "configure"), _good)
        self.output.info("HMBS diag configure shell=%s" % _good)
        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), self._build_environment().vars(self).apply():
            self._build_vendored_tinyxml2()
            autotools.configure()
            # Generated config.status/libtool/Makefile must not carry the
            # poisoned shell into make/check/install.
            self._scrub_poisoned_shell(self.build_folder)
            self._scrub_poisoned_shell(self.source_folder)
            autotools.make(args=["-j1"])
            self._run_upstream_tests(autotools)

    def package(self):
        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), self._build_environment().vars(self).apply():
            # HMDFS toybox install multi-file Error 64 (E596/libnih precedent):
            # configure probes INSTALL to the HMBS runtime shim binary, whose
            # multi-source `install -c -m 644 h1 h2 ... dest` fails with
            # Error 64 (this round: install-pkgincludeHEADERS). Override with
            # the tarball's own install-sh via /bin/sh (libnih: multi-header
            # install succeeds this way); INSTALL_DATA/INSTALL_PROGRAM derive
            # from ${INSTALL} so they follow automatically. Scoped to
            # install only; configure/compile/test env untouched.
            _install_sh = None
            for _cand in (os.path.join(self.source_folder, "install-sh"),
                          os.path.join(self.build_folder, "install-sh")):
                try:
                    if _cand and os.path.isfile(_cand):
                        _install_sh = _cand
                        break
                except Exception:
                    continue
            if _install_sh:
                self.output.info("HMBS diag install-sh override=%s" % _install_sh)
                self.run('make -j1 install DESTDIR="%s" INSTALL="/bin/sh %s -c"'
                         % (self.package_folder, _install_sh))
            else:
                self.output.warning("HMBS diag install-sh not found; using default install")
                autotools.install(args=["-j1"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # Static consumers link librarian.a, whose OMF objects reference
        # tinyxml2 symbols; ship the private static archive with it.
        # (Shared librarian.so already contains the -fPIC objects.)
        _, _, lib = self._tinyxml2_dirs()
        copy(self, "libtinyxml2.a", src=lib,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["rarian", "tinyxml2"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "rarian")]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "rarian")
        self.cpp_info.set_property("cmake_file_name", "rarian")
        self.cpp_info.set_property("cmake_target_name", "rarian::rarian")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
            # Static consumers link librarian.a + libtinyxml2.a (both hold
            # C++ objects) from a pure-C link; propagate the C++ runtime
            # so C consumers (incl. test_package `project(... C)`) link.
            # Matches the build-time runtime above: libc++ on OHOS,
            # libstdc++ on Linux.
            self.cpp_info.system_libs.append(
                "c++" if str(self.settings.os) == "OHOS" else "stdc++")
