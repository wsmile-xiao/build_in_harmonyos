#!/usr/bin/env python3
"""Conan recipe — gnubatch 1.11 (Autotools).

GNU batch job scheduling and printing system: scheduler (btsched), user
front-ends (gbch-* curses tools), network services and CGI helpers.
Upstream: https://www.gnu.org/software/gnubatch/
Build: autotools (configure + make). configure.ac ships no test suite
(no tests/ dir, no TESTS/check targets anywhere), so build() runs
configure + make only; functional coverage lives in test_package.

OHOS adaptation notes (details in notes.md):
- X/Motif GUI (batchwin) disabled via --without-x: platform has no Motif
  toolchain requirement on the consumer side; core scheduler + curses
  front-ends are the preserved feature set.
- CC rides "-std=gnu89 -fcommon": 2009-vintage K&R sources (implicit int
  main, tentative global definitions) fail clang-15 default gnu17.
- LEXLIB is pinned to the flex tool_require's libfl.a: the shipped
  configure's ancient AC_PROG_LEX probe cannot link -lfl from a conan
  build_context package, but util/msglex.l needs yywrap().
- install chown/chmod-suid (USERMODES -o gnubatch -g root -m 4755) is
  routed through a tolerant shim: device/CI users are unprivileged.
- configure's three SysV IPC runtime probes (shm/msgq/sema) are given
  compiled-in defaults: OHOS seccomp kills msgget (SIGSYS) and denies
  shmget for unprivileged users, and the probed values only size
  btsched runtime defaults (scheduler runtime IPC limitation is a
  declared degradation boundary in notes.md).
Helper machinery (compiler/shell resolution, config.guess/sub OHOS patch,
umask scrub) adapted from the merged rrep/1.3.7 recipe.
"""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class GnubatchConan(ConanFile):
    name = "gnubatch"
    version = "1.11"
    description = "GNU batch job scheduling and printing system"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gnubatch/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("gnubatch", "batch", "scheduler", "curses", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # curses front-ends (gbch-q etc.) link -lncurses via LIBCURSES
        self.requires("ncurses/6.6")
        # password checking (btpwchk/btuser) uses crypt(); configure's
        # AC_CHECK_LIB(crypt, crypt, ...) resolves against libxcrypt
        self.requires("libxcrypt/4.5.2")

    def build_requirements(self):
        # util/msglex.l + util/msgparse.y are regenerated at build time
        # (no pre-generated lex.yy.c/y.tab.c in the tarball)
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")
        # src/lib/Makefile.in + src/Makefile.in invoke bare `libtool
        # --mode=compile/link`. The only libtool on PATH would be the
        # configure-generated ./libtool at the source root, which make
        # cannot see when it runs inside build/ (gb_createA device
        # evidence 2026-10-09 06:11 CST: `libtool: No such file or
        # directory` Error 127 on altlen.o). The conan tool_require
        # puts a real libtool on the conanbuild PATH — repo precedent
        # wolfmqtt/whitedb/wolfssl all merged with libtool/2.5.4.
        self.tool_requires("libtool/2.5.4")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "gnubatch is supported only on Linux/OHOS, not %s" % self.settings.os
            )

    def layout(self):
        # gnubatch 1.11 does NOT support out-of-source (VPATH) builds,
        # proven on device (job gb_create3, 2026-10-09 03:25 CST):
        # - configure.ac:728 AC_CONFIG_COMMANDS hooks invoke
        #   `./Makefiles_h.sh` / `./Makegnubatch.conf.sh` relative to the
        #   build dir; out-of-source both are absent there
        #   ("inaccessible or not found") so src/hdrs/files.h (sed'd from
        #   infiles.h) is never generated;
        # - util/Makefile.in:52 declares `helpparse.o ...: hdefs.h` with
        #   no VPATH rule, so make in build-release/util dies with
        #   "No rule to make target 'hdefs.h'".
        # Build in-source (ripmime/recode/redis precedent).
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-x",      # batchwin Motif GUI: no Motif on OHOS (see header)
            "MAKEINFO=true",    # no texinfo on device; docs shipped prebuilt
            # Conan's AutotoolsToolchain defaults --sbindir to
            # ${prefix}/bin, collapsing sbin into bin, so the SUID admin
            # helpers (gbch-passwd/gbch-hostedit, ins/Makefile PROGS ->
            # SBINDIR) landed in bin/ and test_package's sbin/gbch-passwd
            # probe failed (job gnubatch-1.11-verify-20261010-14). The
            # package layout (test_package + package_info PATH) expects
            # sbin/, so override the default; our arg is appended after
            # Conan's, and autoconf last-wins.
            "--sbindir=${prefix}/sbin",
        ])
        # Ancient AC_PROG_LEX probe tries -lfl/-ll against system libs and
        # ends with LEXLIB empty (no system flex); util/Makefile links
        # helpparse with $(LEXLIB) and msglex.c calls yywrap(). Pin LEXLIB
        # to the flex tool_require's libfl.a (absolute path, skips probe).
        try:
            fl = self.dependencies.build.get("flex")
            if fl is not None:
                libfl = os.path.join(fl.package_folder, "lib", "libfl.a")
                if os.path.isfile(libfl):
                    tc.configure_args.append("LEXLIB=%s" % libfl)
                    self.output.info("HMBS diag LEXLIB=%s" % libfl)
                else:
                    self.output.warning("HMBS diag flex libfl.a missing: %s" % libfl)
            else:
                self.output.warning("HMBS diag flex not in build context")
        except Exception as e:
            self.output.warning("HMBS diag LEXLIB resolve failed: %s" % e)
        tc.generate()
        # gb_create4 (2026-10-09 04:38) proved ncurses/libxcrypt never
        # reached the compile: configure probed "wrefresh in -lncurses
        # ... no" and pmenu.c died on 'curses.h' not found — only the
        # profile default -I~/usr/local/include was on the line.
        # AutotoolsDeps puts dep CPPFLAGS/LDFLAGS into conanbuild.
        deps = AutotoolsDeps(self)
        deps.generate()
        try:
            _cc, _cxx, _ar, _confmap = self._usable_compilers()
            self.output.info("HMBS diag compilers cc=%s cxx=%s ar=%s" % (_cc, _cxx, _ar))
            self._fix_generated_autotools_compiler(_confmap, _cc, _cxx)
        except Exception as e:
            self.output.warning("HMBS diag compiler resolve failed: %s" % e)
        try:
            _shell = self._resolve_shell()
            self.output.info("HMBS diag shell=%s" % _shell)
            _env = Environment()
            _env.define("CONFIG_SHELL", _shell)
            _env.define("SHELL", _shell)
            _env.vars(self, scope="build").save_sh("hmbs_shell")
        except Exception as e:
            self.output.warning("HMBS diag shell env export failed: %s" % e)

    def _resolve_compiler(self, configured, names):
        # Tool-specific candidates only: never fall back from C to C++
        # names or vice versa. Prefer the profile's configured absolute
        # path when it exists and is executable (CI workers); otherwise
        # resolve via PATH (true device migrated clang from
        # /data/service/hnp/bin to ~/usr/local/bin) or the
        # ~/usr/local/bin fallback. Adapted from rarian/0.8.6 + zydis.
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
        # embeds that dead path into conanautotools.sh, so configure probes
        # `gcc... /data/service/hnp/bin/clang` then dies with `C compiler
        # cannot create executables` (this round's preflight evidence).
        # Rewrite the generated artifacts in place (only when the configured
        # path is missing and the resolved one exists; CI workers untouched).
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

    def _resolve_shell(self):
        # Shared profile bakes CONFIG_SHELL=/data/service/hnp/bin/bash which
        # is inaccessible on the migrated true device (configure[139]
        # re-exec dies with "inaccessible or not found", Error 127).
        # HMBS guarantees shell=/bin/sh, so prefer it; bare "sh" fallback.
        for _cand in ("/bin/sh", os.environ.get("SHELL"), "sh"):
            if not _cand:
                continue
            if _cand.startswith("/data/service/hnp/"):
                continue
            if _cand == "sh" or (os.path.isfile(_cand)
                                 and os.access(_cand, os.X_OK)):
                return _cand
        _which = shutil.which("sh")
        if _which:
            return _which
        return "/bin/sh"

    def _scrub_poisoned_shell(self, root):
        try:
            good = self._resolve_shell()
        except Exception:
            good = "/bin/sh"
        bad = set()
        inherited = os.environ.get("CONFIG_SHELL")
        if inherited and inherited != good:
            bad.add(inherited)
        if "/data/service/hnp/bin/bash" != good:
            bad.add("/data/service/hnp/bin/bash")
        if not bad or not root or not os.path.isdir(root):
            return
        for _dir, _dirs, _files in os.walk(root):
            for _name in _files:
                if _name not in ("configure", "config.status"):
                    continue
                _path = os.path.join(_dir, _name)
                try:
                    with open(_path, "r", encoding="utf-8", errors="replace") as _f:
                        _content = _f.read()
                except OSError:
                    continue
                _fixed = _content
                for _b in bad:
                    _fixed = _fixed.replace(_b, good)
                if _fixed != _content:
                    try:
                        with open(_path, "w", encoding="utf-8", newline="\n") as _f:
                            _f.write(_fixed)
                        self.output.info("HMBS diag scrubbed poisoned shell in %s" % _path)
                    except OSError:
                        continue

    def _harden_configure_shell(self, configure_path, good):
        try:
            _path = os.fspath(configure_path)
        except Exception:
            return
        if not os.path.isfile(_path):
            return
        try:
            with open(_path, "r", encoding="utf-8", errors="replace") as _f:
                _cur = _f.read()
        except OSError:
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
            except OSError as e:
                self.output.warning("HMBS diag harden write failed %s: %s" % (_path, e))

    def _patch_config_guess_sub_for_ohos(self, root):
        """Add HarmonyOS branches to config.guess/config.sub (E007).

        The rrep 1.3.7 tarball ships config.sub timestamp 2022-01-03
        (single kernel-os whitelist) with an echo/exit-vintage
        config.guess: a static ``0001-build-aux-config-guess.patch``
        anchored on a GUESS-style ``*:Minix`` context cannot apply
        (preflight: source file is different at ``*:DragonFly:*:*)``).
        Do the insertion in tolerant Python instead: anchor on the first
        ``aarch64:Linux`` stanza when present, else on ``*:NetBSD``,
        else on the Minix stanza; the inserted block always uses this
        vintage's echo/exit style so the branch actually prints a triplet.
        Same for config.sub: cover both the 2018 two-whitelist layout
        (radvd precedent, ``-linux-musl* | -linux-uclibc*`` second list)
        and the 2022 single-whitelist layout (this tarball). Idempotent
        via marker checks.
        """
        if not root or not os.path.isdir(root):
            return
        guess_files, sub_files = [], []
        for _dir, _dirs, _files in os.walk(root):
            for _name in _files:
                if _name == "config.guess":
                    guess_files.append(os.path.join(_dir, _name))
                elif _name == "config.sub":
                    sub_files.append(os.path.join(_dir, _name))
        ohos_block = (
            "    *:HarmonyOS:*:*)\n"
            "\tcase $UNAME_MACHINE in\n"
            "\t    aarch64|arm64)\n"
            "\t\techo aarch64-unknown-linux-ohos\n"
            "\t\t;;\n"
            "\t    armv7*|armv8*)\n"
            "\t\techo arm-unknown-linux-ohos\n"
            "\t\t;;\n"
            "\t    x86_64|amd64)\n"
            "\t\techo x86_64-unknown-linux-ohos\n"
            "\t\t;;\n"
            "\t    i?86)\n"
            "\t\techo i686-unknown-linux-ohos\n"
            "\t\t;;\n"
            "\t    *)\n"
            "\t\techo \"$UNAME_MACHINE\"-unknown-linux-ohos\n"
            "\t\t;;\n"
            "\tesac\n"
            "\texit ;;\n"
        )
        for _path in guess_files:
            try:
                with open(_path, "r", encoding="utf-8", errors="replace") as _f:
                    _c = _f.read()
            except OSError:
                continue
            _orig = _c
            if "HarmonyOS" not in _c:
                inserted = False
                for _pat in (
                    r"(^[ \t]*aarch64:Linux:\*:\*\)[ \t]*\n)",
                    r"(^[ \t]*\*\+?:NetBSD:\*:\*\)[ \t]*\n)",
                    r"(^[ \t]*i\*86:Minix:\*:\*\)[ \t]*\n)",
                    r"(^[ \t]*\*+:DragonFly:\*:\*\)[ \t]*\n)",
                ):
                    _c2, _n = re.subn(_pat, ohos_block + r"\1", _c,
                                      count=1, flags=re.MULTILINE)
                    if _n:
                        _c = _c2
                        inserted = True
                        break
                if not inserted:
                    raise ConanInvalidConfiguration(
                        "HMBS diag config.guess HarmonyOS insert point not found in %s" % _path)
            if _c != _orig:
                with open(_path, "w", encoding="utf-8", newline="\n") as _f:
                    _f.write(_c)
                self.output.info("HMBS diag patched config.guess HarmonyOS in %s" % _path)
        for _path in sub_files:
            try:
                with open(_path, "r", encoding="utf-8", errors="replace") as _f:
                    _c = _f.read()
            except OSError:
                continue
            _orig = _c
            # config.sub 2022-01-03 (this tarball): single kernel-os
            # whitelist ``linux-musl* | linux-relibc* | linux-uclibc*``.
            # The 2018 vintage (radvd precedent) has TWO whitelists, the
            # second one with a leading dash
            # (``-linux-musl* | -linux-uclibc*``). Detect vintage via the
            # dash-prefixed markers; only the 2018 layout needs count>=2.
            _is_2018 = ('-linux-musl*' in _c or '-linux-uclibc*' in _c)
            if _is_2018:
                need_first = (_c.count('linux-ohos*') < 2)
            else:
                need_first = ('linux-ohos' not in _c)
            if need_first:
                _c2, _n1 = re.subn(
                    r'linux-musl\* \| linux-uclibc\*',
                    'linux-musl* | linux-ohos* | linux-uclibc*', _c, count=1)
                if _n1:
                    _c = _c2
                else:
                    _c2, _n1m = re.subn(
                        r'(linux-musl\*)(\s*\|\s*linux-(?:musl|relibc|uclibc|dietlibc|newlib))',
                        r'\1 | linux-ohos*\2', _c, count=1)
                    if _n1m:
                        _c = _c2
                _c2, _n2 = re.subn(
                    r'-linux-musl\* \| -linux-uclibc\*',
                    '-linux-musl* | -linux-ohos* | -linux-uclibc*', _c, count=1)
                if _n2:
                    _c = _c2
                # 2012 vintage (gnubatch tarball, config.sub timestamp
                # 2012-02-10): the kernel-os whitelist predates musl
                # entirely (linux-gnu* | linux-android* | linux-dietlibc |
                # linux-newlib* | linux-uclibc*) and the second whitelist
                # is the dash list (-linux-gnu* | -linux-android* |
                # -linux-newlib* | -linux-uclibc*). Anchor on the android
                # entries with a lookbehind so the non-dash and dash
                # lists each gain exactly one linux-ohos entry; the
                # patterns are appended last in the chain so musl-era
                # vintages keep matching the earlier patterns.
                _c2, _n7 = re.subn(r'(?<![-\w])linux-android\*',
                                   'linux-android* | linux-ohos*', _c, count=1)
                if _n7:
                    _c = _c2
                    _c2, _n8 = re.subn(r'(?<![-\w])-linux-android\*',
                                       '-linux-android* | -linux-ohos*', _c, count=1)
                    if _n8:
                        _c = _c2
            # ohos-linux triplet form (newer config.sub, rarian precedent).
            if 'ohos-linux)' not in _c:
                _m = re.search(
                    r'android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n'
                    r'\s*basic_os=linux-android\s*\n\s*;;', _c)
                if _m:
                    _ins = (_m.group(0)
                            + '\n\t\t\tohos-linux)\n'
                            + '\t\t\t\tbasic_machine=$field1-unknown\n'
                            + '\t\t\t\tbasic_os=linux-ohos\n'
                            + '\t\t\t\t;;')
                    _c = _c[:_m.start()] + _ins + _c[_m.end():]
            # Newer config.sub OS-type list (gnu* | android* | ohos*).
            # NOTE: guard must be specific (``android* | ohos*``): a bare
            # ``'ohos*' not in`` check is poisoned by ``linux-ohos*``
            # (which contains the substring ``ohos*``), so after the
            # kernel-os edit the OS list would be silently skipped and
            # configure would still die with OS `ohos' not recognized.
            if 'android* | ohos*' not in _c and 'gnu* | android* | ohos*' not in _c:
                _c2, _n3 = re.subn(
                    r'(gnu\*\s*\|\s*android\*)', r'\1 | ohos*', _c, count=1)
                if _n3:
                    _c = _c2
            # Newer kernel list single-entry form (xz precedent).
            if 'linux-ohos' not in _c:
                _c2, _n4 = re.subn(
                    r'(linux-uclibc\*[/-]?\s*)\)', r'\1| linux-ohos*)', _c, count=1)
                if _n4:
                    _c = _c2
            if 'linux-ohos' not in _c:
                raise ConanInvalidConfiguration(
                    'HMBS diag config.sub linux-ohos insert point not found in %s' % _path)
            # Vintage-aware gate: 2018 files carry two whitelists (both
            # must gain linux-ohos), 2022 files (this tarball, single
            # ``linux-*`` whitelist, no ``-linux-`` second list) need only
            # one. The old unconditional ``count < 2`` gate fired on this
            # tarball even after a correct single insertion.
            _has_second = ('-linux-musl*' in _c or '-linux-uclibc*' in _c)
            if _has_second and _c.count('linux-ohos*') < 2:
                raise ConanInvalidConfiguration(
                    'HMBS diag config.sub second whitelist missing linux-ohos in %s' % _path)
            if _c != _orig:
                with open(_path, 'w', encoding='utf-8', newline='\n') as _f:
                    _f.write(_c)
                self.output.info('HMBS diag patched config.sub ohos in %s' % _path)

    @staticmethod
    def _patch_configure_umask(configure_path):
        """Drop `umask 077` temp-dir wrappers (HMDFS E114).

        HMDFS forces setgid on directories, so `umask 077 && mktemp -d`
        yields a drwx--S--- dir that is not writable even by its owner.
        Plain string replacement (no line-context anchor) so it applies
        to any autoconf vintage.
        """
        with open(configure_path, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        content = content.replace("umask 077 && ", "")
        with open(configure_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _patch_configure_ipc_probes(self, configure_path):
        """Give configure's System V IPC runtime probes default fallbacks.

        OHOS blocks SysV IPC for unprivileged processes (2026-10-09
        device evidence: shmget(IPC_PRIVATE) fails at 4K/128K/8M for
        uid 2000, and msgget() is killed with Signal 31 SIGSYS — the
        syscall is seccomp-blocked), so the three AC_TRY_RUN probes
        (max shm size / msg queue depth / semaphore count) always take
        their AC_MSG_ERROR branch and abort configure.  The probed
        values only size btsched runtime defaults (NUMSEMA4/NUMXBUFS,
        job alloc); no front-end, password or API code compiled from
        them runs during the consumer tests.  Replace the four unique
        as_fn_error lines in the generated configure with sane
        compiled-in defaults (8MB shm, 64 queue slots, 32 semaphores —
        all within the probes' own acceptance ranges).  The scheduler
        runtime IPC limitation is a declared degradation boundary in
        notes.md, not a build blocker.
        """
        replacements = (
            ('as_fn_error $? "No joy - maybe no shm?" "$LINENO" 5',
             'ac_shmsize=8388608'),
            ('as_fn_error $? "Trouble with message queues - giving up" "$LINENO" 5',
             'ac_msgqsize=64'),
            ('as_fn_error $? "$ac_numsema4 is too few - giving up" "$LINENO" 5',
             'ac_numsema4=32'),
            ('as_fn_error $? "Trouble with semaphores - giving up" "$LINENO" 5',
             'ac_numsema4=32'),
        )
        try:
            with open(configure_path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        original = content
        hits = 0
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                hits += 1
        if content != original:
            with open(configure_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            try:
                _name = os.path.basename(os.path.dirname(configure_path))
            except Exception:
                _name = configure_path
            self.output.info("HMBS diag patched %d IPC probe error(s) in configure (%s)"
                             % (hits, _name))

    def _patch_configure_curses_probe(self, configure_path):
        """Retarget the upstream ncurses probe to the wide-char library.

        The published conan ncurses/6.6 package on OHOS ships only the
        wide-char static libraries (libncursesw.a, libmenuw.a, ... — no
        libncurses.a / libcurses.a; gb_diag2 device evidence 2026-10-09
        04:49 CST).  gnubatch 1.11's configure probes -lcurses then
        -lncurses, both fail with "unable to find library", LIBCURSES
        stays empty, and every curses link (gbch-pmenu/gbch-hostedit,
        src/btq family) dies on undefined keypad/wrefresh/stdscr
        (gb_create5 04:46 CST).  Rewrite the -lncurses probe to
        -lncursesw so LIBCURSES resolves to the library that exists.
        The probe link line already carries the conan -L path from
        AutotoolsDeps LDFLAGS, so the test links against the real
        package.  Upstream only ever *adds* curses features via
        LIBCURSES; the wide-char ABI is a superset of the narrow one
        the code was written against.
        """
        replacements = (
            ('LIBS="-lncurses  $LIBS"', 'LIBS="-lncursesw  $LIBS"'),
            ('LIBCURSES=-lncurses', 'LIBCURSES=-lncursesw'),
        )
        try:
            with open(configure_path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        original = content
        for old, new in replacements:
            content = content.replace(old, new)
        if content != original:
            with open(configure_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            self.output.info("HMBS diag patched curses probe to -lncursesw (%s)"
                             % os.path.basename(os.path.dirname(configure_path)))

    def _patch_makefile_ldflags(self, root):
        """Stop the util/ins/loccgi/motif/gtk Makefile.in from nulling LDFLAGS.

        Those Makefile.in files hardcode `LDFLAGS =` (empty), which
        overrides the conanbuild env LDFLAGS holding the conan -L paths
        (ncurses/libxcrypt/flex).  Result: even with LIBCURSES set, the
        explicit link rules `$(CC) $(LDFLAGS) -o $@ pmenu.o $(LIBCURSES)`
        cannot find -lncursesw/-lcrypt (gb_create5 link stage).  Point
        LDFLAGS at the configure-substituted value instead — @LDFLAGS@
        bakes the same -L list configure used for its probes.
        """
        targets = (
            os.path.join(root, "util", "Makefile.in"),
            os.path.join(root, "src", "ins", "Makefile.in"),
            os.path.join(root, "src", "loccgi", "Makefile.in"),
            os.path.join(root, "src", "motif", "Makefile.in"),
            os.path.join(root, "src", "gtk", "Makefile.in"),
        )
        patched = 0
        for path in targets:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
            except OSError:
                continue
            new = content.replace("LDFLAGS\t\t=\n", "LDFLAGS\t\t=@LDFLAGS@\n")
            if new != content:
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(new)
                patched += 1
        if patched:
            self.output.info("HMBS diag restored @LDFLAGS@ in %d Makefile.in" % patched)

    def _patch_gbpasswd_compat(self, source_root):
        """Give util/gbpasswd.c local getpass()/l64a() for OHOS musl.

        OHOS/musl's unistd.h declares neither getpass() nor l64a(), and
        libc.so exports no such symbols (gb_diag3/gb_diag4 device evidence
        2026-10-09 05:4x CST: header grep empty even with _GNU_SOURCE,
        llvm-nm finds nothing, explicit-extern link fails with undefined
        symbol). clang-15 then hard-errors the implicit int->char*
        conversions (-Wint-conversion, gb_create6/7). Upstream already
        carries an l64a fallback but gates it on OS_FREEBSD, whose macro
        is wired to FreeBSD-specific code paths elsewhere (incl_sig.h,
        getkey/setkey, ripc.c) so it cannot be defined globally. Inject
        static compat implementations right after the file's own
        `extern char *crypt(...)` prototype — before first use at
        line 133/144 — guarded on !__GLIBC__ so a glibc build keeps the
        system functions. getpass is only reached by the interactive
        (no -p) path; the test_package drives gbch-passwd -f -F ... -p,
        so the compat path needs to compile/link and read stdin, which
        it does via /dev/tty with stdin fallback.
        """
        path = os.path.join(source_root, "util", "gbpasswd.c")
        marker = "gb_ohos_compat_getpass"
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        if marker in content:
            return
        anchor = "extern char *crypt(const char *, const char *);"
        compat = """
/* OHOS compat (recipe-injected): musl on OHOS declares neither
   getpass() nor l64a() in unistd.h and exports no libc symbols for
   them (device evidence gb_diag3/gb_diag4 2026-10-09). Provide
   local implementations; glibc builds keep the system ones. */
#if !defined(__GLIBC__) && !defined(OS_FREEBSD)
static char *gb_ohos_compat_l64a(long v)
{
\tstatic char result[7];
\tint cnt;
\tfor (cnt = 0; cnt < 6; cnt++) {
\t\tresult[cnt] = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"[v & 63];
\t\tv >>= 6;
\t}
\tresult[6] = '\\0';
\treturn result;
}
static char *gb_ohos_compat_getpass(const char *prompt)
{
\tstatic char buf[128];
\tFILE *fp;
\tfputs(prompt, stderr);
\tfflush(stderr);
\tfp = fopen("/dev/tty", "r");
\tif (!fp)
\t\tfp = stdin;
\tif (!fgets(buf, sizeof(buf), fp))
\t\tbuf[0] = '\\0';
\tif (fp != stdin)
\t\tfclose(fp);
\tbuf[strcspn(buf, "\\n")] = '\\0';
\treturn buf;
}
#define l64a(v) gb_ohos_compat_l64a(v)
#define getpass(p) gb_ohos_compat_getpass(p)
#endif
"""
        if anchor not in content:
            self.output.warning("HMBS diag gbpasswd compat anchor missing")
            return
        content = content.replace(anchor, anchor + compat, 1)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("HMBS diag injected getpass/l64a compat into util/gbpasswd.c")

    def _patch_helpparse_stage_link(self, source_root):
        """Give util/helpparse.c a copy fallback for hmdfs-incompatible link().

        The top-level `buildd` rule runs helpparse to stage the src tree
        into build/; mod_copy() hard-links every regular file with
        link(2).  Device evidence gb_diag5 (2026-10-09 05:55 CST): hmdfs
        returns EPERM for link() everywhere (user storage AND the conan
        cache) while symlink()/copy work, so gb_create8 died with
        `Unable to link src/gtk/xbtqsel.menu to build/gtk/xbtqsel.menu`
        exit 27 on the very first staged file.  Wrap the call through a
        helper that tries link() first (glibc hosts keep upstream
        behavior) and falls back to a byte copy that preserves the
        source mode (staged files feed make in build/, so executable
        bits must survive).
        """
        path = os.path.join(source_root, "util", "helpparse.c")
        marker = "gb_ohos_stage_link"
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        if marker in content:
            return
        anchor = "static\tvoid\tmod_copy(char *src, char *dst)"
        helper = """/* OHOS compat (recipe-injected): hmdfs returns EPERM from link(2)
   hard links (device evidence gb_diag5 2026-10-09), so staging the
   src tree into build/ must fall back to a byte copy. link() is
   still tried first so glibc hosts keep upstream behavior. */
static int gb_ohos_stage_link(char *spath, char *dpath, int mode)
{
\tFILE *sf, *df;
\tchar buf[8192];
\tsize_t n;
\tif  (link(spath, dpath) == 0)
\t\treturn 0;
\tsf = fopen(spath, "rb");
\tif  (!sf)
\t\treturn -1;
\tdf = fopen(dpath, "wb");
\tif  (!df)  {
\t\tfclose(sf);
\t\treturn -1;
\t}
\twhile  ((n = fread(buf, 1, sizeof(buf), sf)) > 0)  {
\t\tif  (fwrite(buf, 1, n, df) != n)  {
\t\t\tfclose(sf);
\t\t\tfclose(df);
\t\t\treturn -1;
\t\t}
\t}
\tfclose(sf);
\tif  (fclose(df) != 0)
\t\treturn -1;
\tchmod(dpath, mode & 0777);
\treturn 0;
}

"""
        call_old = "if  (link(spath, dpath) < 0)  {"
        call_new = "if  (gb_ohos_stage_link(spath, dpath, (int)(sbuf.st_mode & 0777)) < 0)  {"
        if anchor not in content or call_old not in content:
            self.output.warning("HMBS diag helpparse compat anchor missing")
            return
        content = content.replace(anchor, helper + anchor, 1)
        content = content.replace(call_old, call_new, 1)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("HMBS diag injected stage-link copy fallback into util/helpparse.c")

    def _patch_termio_compat(self, source_root):
        """Back src/lib's termio paths with <termios.h> on OHOS/musl.

        configure reports `termio.h: no / termios.h: yes` (gb_createB
        device log 2026-10-09 06:22 CST), and musl ships neither
        <termio.h> nor <sgtty.h> nor struct termio/tchars/sgttyb, so
        src/lib/setkey.c:34's `#include <termio.h>` hard-fails
        (fatal error, gb_createB), and the HAVE_TERMIO_H-less
        fallbacks -- <sgtty.h> include at setkey.c:41 plus the
        struct tchars/sgttyb ioctl blocks at setkey.c case I/K/E/Q --
        would fail next.  Nothing outside src/lib needs this: the
        curses front-ends (btuser/btq/bq_*) all guard on HAVE_TERMIOS_H,
        which configure finds (yes).

        Injected into setkey.c and getkey.c:

        1. right after their own `#include "config.h"`: force
           HAVE_TERMIO_H (musl's check is a plain "no"; taking the
           termio branches skips the BSD sgtty/tchars paths entirely)
           and set gb_ohos_termio_forced;
        2. before the first local include: map termio -> termios via
           <termios.h> and remap TCGETA/TCSETA to TCGETS/TCSETS -- the
           codes that actually take struct termios (the legacy codes
           expect a 28-byte struct termio and would misplace the
           c_cc[VMIN/VTIME/VINTR] writes these files make);
        3. comment out the stale `#include <termio.h>` line.

        Idempotent: every edit is gated on the gb_ohos_termio marker,
        so a re-run over a cached source tree is a no-op.
        """
        marker = "gb_ohos_termio"
        targets = (
            (os.path.join(source_root, "src", "lib", "setkey.c"),
             '#include "keymap.h"'),
            (os.path.join(source_root, "src", "lib", "getkey.c"),
             '#include "incl_sig.h"'),
        )
        guard = (
            "\n/* %s: OHOS/musl provides neither <termio.h> nor <sgtty.h>\n"
            "   nor struct termio/tchars/sgttyb (configure: termio.h no,\n"
            "   termios.h yes; gb_createB died at setkey.c:34).  Take the\n"
            "   HAVE_TERMIO_H branches -- they are all standard POSIX --\n"
            "   and back them with <termios.h> below. */\n"
            "#ifndef HAVE_TERMIO_H\n"
            "#define HAVE_TERMIO_H 1\n"
            "#define gb_ohos_termio_forced 1\n"
            "#endif\n" % marker
        )
        mapping = (
            "#ifdef gb_ohos_termio_forced\n"
            "/* %s: termio is a musl myth -- use struct termios and the\n"
            "   ioctls that take it; legacy TCGETA/TCSETA expect a 28-byte\n"
            "   struct termio and would misplace the c_cc writes below. */\n"
            "#include <termios.h>\n"
            "#define termio termios\n"
            "#include <sys/ioctl.h>\n"
            "#undef TCGETA\n"
            "#define TCGETA TCGETS\n"
            "#undef TCSETA\n"
            "#define TCSETA TCSETS\n"
            "#endif\n" % marker
        )
        cfg_anchor = '#include "config.h"'
        stale = "#include <termio.h>"
        stale_new = ("/* %s: musl has no termio.h; termios mapping is "
                     "injected below */" % marker)
        touched = 0
        for path, map_anchor in targets:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
            except OSError:
                self.output.warning("HMBS diag termio patch target missing: %s" % path)
                continue
            if marker in content:
                continue
            if cfg_anchor not in content:
                self.output.warning("HMBS diag termio config.h anchor missing: %s" % path)
                continue
            if map_anchor not in content:
                self.output.warning("HMBS diag termio map anchor missing: %s" % path)
                continue
            content = content.replace(cfg_anchor, cfg_anchor + guard, 1)
            content = content.replace(stale, stale_new)
            content = content.replace(map_anchor, mapping + map_anchor, 1)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            touched += 1
        if touched:
            self.output.info("HMBS diag injected termio->termios compat into %d src/lib files" % touched)

    def _patch_sigcld_compat(self, source_root):
        """Define SIGCLD for musl/OHOS via hdrs/incl_sig.h.

        Upstream defines SIGCLD=SIGCHLD only under OS_FREEBSD
        (hdrs/incl_sig.h:63-65); every other platform is expected to get
        SIGCLD from <signal.h>. glibc aliases SIGCLD to SIGCHLD, but
        OHOS/musl defines neither, so btfilemon.c:1445 (and sh_exec.c /
        sh_misc.c, which include the same header) die with "use of
        undeclared identifier 'SIGCLD'" (device evidence 2026-10-10, job
        gnubatch-1.11-verify-20261010-1). Append a guarded alias so any
        platform whose signal.h lacks SIGCLD picks up the POSIX SIGCHLD
        value; platforms that already define it are untouched. Idempotent
        via the gb_ohos_sigcld marker.
        """
        # The source tree is rooted at source_folder with headers under
        # src/hdrs/ (termio compat patches src/lib too; the top-level
        # hdrs/ does not exist). Allow both spellings for robustness.
        candidates = (
            os.path.join(source_root, "src", "hdrs", "incl_sig.h"),
            os.path.join(source_root, "hdrs", "incl_sig.h"),
        )
        path = next((p for p in candidates if os.path.isfile(p)), None)
        marker = "gb_ohos_sigcld"
        if path is None:
            self.output.warning("HMBS diag sigcld compat target missing: %s" % (candidates,))
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            self.output.warning("HMBS diag sigcld compat target unreadable: %s" % path)
            return
        if marker in content:
            return
        block = (
            "\n/* %s: glibc aliases SIGCLD to SIGCHLD, but OHOS/musl\n"
            "   defines neither; upstream only maps it under OS_FREEBSD\n"
            "   above. Provide the POSIX alias whenever the platform\n"
            "   header lacks it (btfilemon.c:1445 et al.). */\n"
            "#ifndef SIGCLD\n"
            "#define SIGCLD SIGCHLD\n"
            "#endif\n" % marker
        )
        content = content.rstrip("\n") + "\n" + block
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("HMBS diag injected SIGCLD->SIGCHLD compat into hdrs/incl_sig.h")

    def _patch_btsched_ucontext_compat(self, source_root):
        """Port btsched.c's trap_loop() off the glibc x86_64 ucontext ABI.

        btsched.c:246-247 (inside `#ifdef OS_LINUX`) dereferences
        `struct ucontext *uc = (struct ucontext *) p; pc =
        uc->uc_mcontext.gregs[14];`, which is the glibc x86_64 layout.
        OHOS/musl exposes only the `ucontext_t` typedef (tag
        `struct __ucontext`) and `mcontext_t == struct sigcontext` with a
        dedicated `pc` field (sysroot aarch64-linux-ohos/bits/signal.h),
        so `struct ucontext` is incomplete (device evidence 2026-10-10,
        job gnubatch-1.11-verify-20261010-7: "incomplete definition of
        type 'struct ucontext'").  trap_loop() only logs the fault PC to
        loop.trap, so keep the glibc path for __GLIBC__/__x86_64__ builds
        and read the aarch64 `pc` field otherwise.  Idempotent via the
        gb_ohos_ucontext marker.
        """
        path = os.path.join(source_root, "src", "btsched.c")
        marker = "gb_ohos_ucontext"
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            self.output.warning("HMBS diag ucontext compat target missing: %s" % path)
            return
        if marker in content:
            return
        old = ("        struct  ucontext  *uc = (struct ucontext *) p;\n"
               "        pc = uc->uc_mcontext.gregs[14];\n")
        new = (
            "#if defined(__GLIBC__) && defined(__x86_64__)\n"
            "        struct  ucontext  *uc = (struct ucontext *) p;\n"
            "        pc = uc->uc_mcontext.gregs[14];\n"
            "#elif defined(__aarch64__)\n"
            "        /* %s: OHOS/musl exposes only ucontext_t (tag\n"
            "           struct __ucontext) and mcontext_t == struct\n"
            "           sigcontext with a dedicated pc field; gregs[14]\n"
            "           is the glibc x86_64 layout. */\n"
            "        ucontext_t  *uc = (ucontext_t *) p;\n"
            "        pc = (unsigned long) uc->uc_mcontext.pc;\n"
            "#else\n"
            "        (void) p;\n"
            "#endif\n" % marker
        )
        if old not in content:
            self.output.warning("HMBS diag ucontext compat anchor missing: %s" % path)
            return
        content = content.replace(old, new, 1)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("HMBS diag injected ucontext compat into src/btsched.c")

    def _patch_ulimit_compat(self, source_root):
        """Provide the legacy ulimit() RLIMIT_FSIZE subset on OHOS/musl.

        sh_exec.c declares `extern int ulimit(int, long)` under
        `#if defined(OS_LINUX) && !defined(HAVE_ULIMIT_H)` and calls
        `ulimit(2, jp->h.bj_ulimit)` at ~line 1001. glibc exports the
        legacy ulimit(); OHOS/musl does not, so the btsched link dies
        with `undefined symbol: ulimit` (device evidence 2026-10-10,
        jobs gnubatch-1.11-verify-20261010-8/-9). Note the upstream extern
        block is DEAD here: the OHOS sysroot ships a <ulimit.h> stub, so
        configure defines HAVE_ULIMIT_H=1 and the `#if` is false. Fix the
        call site directly: define a gb_ohos_ulimit_setfsize() helper
        (getrlimit/setrlimit(RLIMIT_FSIZE), 512-byte units) and route the
        single call to it on non-glibc. glibc keeps upstream's call.
        Idempotent via the gb_ohos_ulimit marker.
        """
        path = os.path.join(source_root, "src", "sh_exec.c")
        marker = "gb_ohos_ulimit"
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            self.output.warning("HMBS diag ulimit compat target missing: %s" % path)
            return
        if marker in content:
            return
        # NOTE: configure sets HAVE_ULIMIT_H=1 because the OHOS sysroot
        # ships a <ulimit.h> STUB that only defines UL_GETFSIZE/UL_SETFSIZE
        # and declares no ulimit(); libc exports none either. The upstream
        # extern block is therefore inside a false `#if`, so the compat
        # must NOT live there. Define a helper next to the includes
        # (glibc keeps the real function) and switch the single call site.
        anchor_inc = '#include "sh_ext.h"\n'
        helper = (
            '#include "sh_ext.h"\n'
            "/* %s: OHOS/musl ships a <ulimit.h> stub (configure sets\n"
            "   HAVE_ULIMIT_H=1) but declares no ulimit() and libc exports\n"
            "   none; give the RLIMIT_FSIZE subset gnubatch uses\n"
            "   (UL_SETFSIZE, 512-byte units) real code. */\n"
            "#if !defined(__GLIBC__)\n"
            "#include <sys/resource.h>\n"
            "static void gb_ohos_ulimit_setfsize(long val)\n"
            "{\n"
            "        struct rlimit rl;\n"
            "        if  (getrlimit(RLIMIT_FSIZE, &rl) == 0)  {\n"
            "                rl.rlim_cur = (rlim_t) val * 512;\n"
            "                setrlimit(RLIMIT_FSIZE, &rl);\n"
            "        }\n"
            "}\n"
            "#endif\n" % marker
        )
        call_old = "                ulimit(2, jp->h.bj_ulimit);\n"
        call_new = (
            "#if defined(__GLIBC__)\n"
            "                ulimit(2, jp->h.bj_ulimit);\n"
            "#else\n"
            "                gb_ohos_ulimit_setfsize(jp->h.bj_ulimit);\n"
            "#endif\n"
        )
        if anchor_inc not in content or call_old not in content:
            self.output.warning("HMBS diag ulimit compat anchor missing: %s" % path)
            return
        content = content.replace(anchor_inc, helper, 1)
        content = content.replace(call_old, call_new, 1)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("HMBS diag injected ulimit compat into src/sh_exec.c")

    def _patch_makefile_fcommon(self, root):
        """Append -fcommon to CCFLAGS in every Makefile.in.

        The subdir Makefiles bake `CC = <clang>` (a makefile assignment
        that overrides the build-env CC), so the recipe's intended
        `-std=gnu89 -fcommon` never reaches the compiler and clang
        defaults to -fno-common.  remcgi's rbtjccgi.o and the client
        library's optpparm.o both carry a tentative `BtjobRef JREQ;`,
        which -fno-common turns into `duplicate symbol: JREQ`
        (device evidence 2026-10-10, job gnubatch-1.11-verify-20261010-10).
        Upstream expects one shared definition (the classic -fcommon
        model), so append -fcommon to the CCFLAGS line; it propagates to
        CFLAGS and to the libtool link/compile lines.  Idempotent.
        Only -fcommon is added (not -std=gnu89) so already-C99-clean
        translation units keep compiling unchanged.
        """
        if not root or not os.path.isdir(root):
            return
        patched = 0
        for dirpath, _dirs, files in os.walk(root):
            if "Makefile.in" not in files:
                continue
            path = os.path.join(dirpath, "Makefile.in")
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    lines = handle.readlines()
            except OSError:
                continue
            changed = False
            for i, line in enumerate(lines):
                if line.startswith("CCFLAGS") and "=" in line and "-fcommon" not in line:
                    lines[i] = line.rstrip("\n") + " -fcommon\n"
                    changed = True
            if changed:
                try:
                    with open(path, "w", encoding="utf-8", newline="\n") as handle:
                        handle.writelines(lines)
                    patched += 1
                except OSError:
                    continue
        if patched:
            self.output.info("HMBS diag added -fcommon to CCFLAGS in %d Makefile.in" % patched)

    def _patch_makefile_ln_to_cp(self, root):
        """Replace install-time `ln -f` alias links with `cp -f`.

        hmdfs returns EPERM from link(2) (device evidence 2026-10-10,
        jobs gnubatch-1.11-verify-20261010-10/-12 and the earlier
        helpparse finding #14). The install rules create command aliases
        with `ln -f` — src/Makefile.in:239-240/262-263 for the
        gbch-disconn/gbch-conn/gbch-dst -> gbch-start and gbch-jdel
        families, and helpmsg/Makefile.in:42/46 for btq.help/btuser.help:
        `ln: cannot create hard link ... Operation not permitted`, which
        aborts the whole install. symlink()/copy both work on hmdfs, so
        swap `ln -f` for `cp -f` (same user-visible result: each alias is
        a usable copy of the target). Only -f (hard link) is touched;
        `ln -s` elsewhere is left alone.  Idempotent (no `ln -f` remains).
        """
        if not root or not os.path.isdir(root):
            return
        patched = 0
        # Command-position `ln <ws> -f <ws>` only (start of line or after
        # ; or whitespace), so ordinary words are never touched. Applies
        # to Makefile.in AND shipped shell scripts (helpmsg/Maketerms.sh
        # builds the terminfo hard links at install time).
        pattern = re.compile(r"(^|[;\t ])ln(\s+)-f(\s+)")
        targets = []
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                if name == "Makefile.in" or name.endswith(".sh"):
                    targets.append(os.path.join(dirpath, name))
        for path in targets:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
            except OSError:
                continue
            new = pattern.sub(r"\1cp\2-f\3", text)
            if new != text:
                try:
                    with open(path, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(new)
                    patched += 1
                except OSError:
                    continue
        if patched:
            self.output.info("HMBS diag replaced ln -f with cp -f in %d Makefile.in/.sh" % patched)

    def build(self):
        apply_conandata_patches(self)
        self._patch_config_guess_sub_for_ohos(self.source_folder)
        # Preflight config.sub path was .../p/b/<id>/b/build-aux/config.sub
        # (base build tree, not source_folder). Patch every candidate root
        # so the file actually used by configure is covered.
        try:
            _bf = self.build_folder
        except Exception:
            _bf = None
        if _bf and _bf != self.source_folder and os.path.isdir(_bf):
            self._patch_config_guess_sub_for_ohos(_bf)
        for _extra in ("base_source_folder", "base_build_folder"):
            try:
                _root = getattr(self, _extra, None)
            except Exception:
                _root = None
            if _root and _root not in (self.source_folder, _bf):
                try:
                    _root_s = os.fspath(_root)
                except Exception:
                    continue
                if os.path.isdir(_root_s):
                    try:
                        self._patch_config_guess_sub_for_ohos(_root_s)
                    except Exception as _e:
                        self.output.warning(
                            "HMBS diag extra root patch %s failed: %s" % (_root_s, _e))
        self._patch_configure_umask(os.path.join(self.source_folder, "configure"))
        self._patch_configure_ipc_probes(os.path.join(self.source_folder, "configure"))
        self._patch_configure_curses_probe(os.path.join(self.source_folder, "configure"))
        self._patch_makefile_ldflags(self.source_folder)
        self._patch_makefile_fcommon(self.source_folder)
        self._patch_makefile_ln_to_cp(self.source_folder)
        self._patch_gbpasswd_compat(self.source_folder)
        self._patch_helpparse_stage_link(self.source_folder)
        self._patch_termio_compat(self.source_folder)
        self._patch_sigcld_compat(self.source_folder)
        self._patch_btsched_ucontext_compat(self.source_folder)
        self._patch_ulimit_compat(self.source_folder)
        try:
            _bcfg = os.path.join(self.build_folder, "configure")
            if _bcfg != os.path.join(self.source_folder, "configure"):
                self._patch_configure_ipc_probes(_bcfg)
        except Exception as _e:
            self.output.warning("HMBS diag build-folder ipc probe patch skipped: %s" % _e)
        try:
            _good = self._resolve_shell()
        except Exception:
            _good = "/bin/sh"
        os.environ["CONFIG_SHELL"] = _good
        os.environ["SHELL"] = _good
        self._scrub_poisoned_shell(self.source_folder)
        self._harden_configure_shell(os.path.join(self.source_folder, "configure"), _good)
        self.output.info("HMBS diag configure shell=%s" % _good)
        try:
            _cc, _cxx, _ar, _confmap = self._usable_compilers()
            self.output.info("HMBS diag build compilers cc=%s cxx=%s ar=%s" % (_cc, _cxx, _ar))
            _old_cxx = _confmap.get("cpp") if isinstance(_confmap, dict) else None
            # gnubatch: 2009-vintage K&R C (implicit int main() in the
            # AC_TRY_RUN probes, tentative global definitions) — clang-15
            # defaults to gnu17 where both are hard errors. The upstream
            # Makefiles ignore CFLAGS entirely (CCFLAGS is configure-baked),
            # so the std flags must ride on CC itself.
            # _GNU_SOURCE: util/gbpasswd.c calls getpass()/l64a(), which
            # OHOS/musl unistd.h only declares under _GNU_SOURCE/_BSD_SOURCE
            # (gb_create6 device evidence 2026-10-09 05:25 CST: implicit
            # declaration -> clang-15 hard error -Wint-conversion). musl
            # guards these with feature macros only; the functions exist
            # in libc regardless, so defining the macro is declaration-only.
            if _cc:
                os.environ["CC"] = _cc + " -std=gnu89 -fcommon -D_GNU_SOURCE"
            if _cxx and _old_cxx and _cxx != _old_cxx:
                os.environ["CXX"] = _cxx
        except Exception as _e:
            self.output.warning("HMBS diag build compiler resolve failed: %s" % _e)
            _cc, _cxx = None, None
            try:
                _confmap = {}
            except Exception:
                _confmap = {}
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or ""
        )
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        build_env = Environment()
        build_env.define("CONFIG_SHELL", _good)
        build_env.define("SHELL", _good)
        try:
            _o = _confmap.get("c") if isinstance(_confmap, dict) else None
            if _cc and _o and _cc != _o:
                build_env.define("CC", _cc + " -std=gnu89 -fcommon")
            elif _cc:
                # conanautotools.sh may still bake the profile's configured
                # (possibly dead) CC; pin ours unconditionally with flags.
                build_env.define("CC", _cc + " -std=gnu89 -fcommon")
            _o2 = _confmap.get("cpp") if isinstance(_confmap, dict) else None
            if _cxx and _o2 and _cxx != _o2:
                build_env.define("CXX", _cxx)
        except Exception:
            pass
        build_env.define("TMPDIR", tmpdir)
        build_env.define("TMP", tmpdir)
        build_env.define("TEMP", tmpdir)
        autotools = Autotools(self)
        with build_env.vars(self).apply():
            autotools.configure()
            self._scrub_poisoned_shell(self.build_folder)
            autotools.make(args=["-j1"])

    def _find_install_sh(self):
        # Previous round only checked top-level source/build install-sh and
        # missed (log: "install-sh not found"); this tarball keeps aux
        # files under build-aux/ (cf. config.sub at .../b/build-aux/).
        # Walk every candidate root recursively instead of asserting layout.
        roots = []
        for _r in (getattr(self, "source_folder", None),
                   getattr(self, "build_folder", None),
                   getattr(self, "base_source_folder", None),
                   getattr(self, "base_build_folder", None)):
            try:
                _rs = os.fspath(_r) if _r is not None else None
            except Exception:
                continue
            if _rs and os.path.isdir(_rs) and _rs not in roots:
                roots.append(_rs)
        for _root in roots:
            for _dir, _dirs, _files in os.walk(_root):
                if "install-sh" in _files:
                    _p = os.path.join(_dir, "install-sh")
                    try:
                        if os.path.isfile(_p):
                            return _p
                    except Exception:
                        continue
        return None

    def _write_install_shim(self):
        # radcli/1.2.11 pattern, gnubatch-aware: cp/mkdir shim tolerating
        # unprivileged ownership flags. Two fixes over the earlier draft:
        # - gnubatch's VERY FIRST install call is
        #   `$(INSTALL) -d -o $(BATCHUSER) -g root -m 755 $(SPOOLDIR)`:
        #   `-d` comes FIRST with -o/-g/-m options AFTER it, so -d must be
        #   a mode flag (keep parsing options), not an option terminator
        #   that blindly mkdirs the remaining words;
        # - ZERO `$(...)` command substitution and no $(dirname): the
        #   migrated device /bin/sh materializes command substitution in
        #   hardcoded /tmp which is read-only erofs (rrep test.sh
        #   precedent); dirname via ${dest%/*}, counting via $(( ))
        #   (parser-internal, no temp file, no fork).
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
                    "dir_mode=0\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -d) dir_mode=1; shift ;;\n"
                    "    -m) mode=$2; shift 2 ;;\n"
                    "    -o|-g|-u) shift 2 ;;\n"
                    "    -p|-c|-s|-v) shift ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "if [ \"$dir_mode\" = 1 ]; then\n"
                    "  [ $# -gt 0 ] || exit 2\n"
                    "  for d in \"$@\"; do\n"
                    "    mkdir -p \"$d\"\n"
                    "    if [ -n \"$mode\" ]; then chmod \"$mode\" \"$d\" 2>/dev/null || true; fi\n"
                    "  done\n"
                    "  exit 0\n"
                    "fi\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "total=0\n"
                    "for a in \"$@\"; do total=$((total + 1)); done\n"
                    "dest=\n"
                    "i=0\n"
                    "for a in \"$@\"; do\n"
                    "  i=$((i + 1))\n"
                    "  if [ \"$i\" -eq \"$total\" ]; then dest=$a; fi\n"
                    "done\n"
                    "if [ \"$total\" -gt 2 ]; then\n"
                    "  mkdir -p \"$dest\"\n"
                    "else\n"
                    "  ddir=${dest%/*}\n"
                    "  if [ \"$ddir\" = \"$dest\" ]; then ddir=.; fi\n"
                    "  mkdir -p \"$ddir\"\n"
                    "fi\n"
                    "i=0\n"
                    "for src in \"$@\"; do\n"
                    "  i=$((i + 1))\n"
                    "  [ \"$i\" -lt \"$total\" ] || break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else chmod \"$mode\" \"$dest\" 2>/dev/null || true; fi\n"
                    "  fi\n"
                    "done\n"
                )
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass
        return install

    def _redirect_install_to_shim(self, shim_install):
        # configure bakes the probed shim path into every Makefile's
        # INSTALL; rewrite in place so libtool --mode=install paths follow
        # even if a sub-make drops the command-line override.
        try:
            _bf = os.fspath(self.build_folder)
        except Exception:
            return
        if not _bf or not os.path.isdir(_bf):
            return
        for _root, _dirs, _files in os.walk(_bf):
            if "Makefile" not in _files:
                continue
            _mp = os.path.join(_root, "Makefile")
            try:
                with open(_mp, "r", encoding="utf-8", errors="ignore") as _f:
                    _content = _f.read()
            except OSError:
                continue
            if "INSTALL =" not in _content:
                continue
            _lines = []
            _changed = False
            for _line in _content.splitlines(True):
                _stripped = _line.lstrip()
                if _stripped.startswith("INSTALL = ") and "/install" in _stripped:
                    _indent = _line[:len(_line) - len(_stripped)]
                    _lines.append("%sINSTALL = %s\n" % (_indent, shim_install))
                    _changed = True
                else:
                    _lines.append(_line)
            if _changed:
                try:
                    with open(_mp, "w", encoding="utf-8", newline="\n") as _f:
                        _f.write("".join(_lines))
                except OSError:
                    continue

    def package(self):
        try:
            _good = self._resolve_shell()
        except Exception:
            _good = "/bin/sh"
        self._scrub_poisoned_shell(self.build_folder)
        self._scrub_poisoned_shell(self.source_folder)
        _penv = Environment()
        _penv.define("CONFIG_SHELL", _good)
        _penv.define("SHELL", _good)
        with _penv.vars(self).apply():
            # gnubatch install passes ownership flags (USERMODES =
            # "-o gnubatch -g root -m 4755", TTYGROUP "-g tty") through
            # $(INSTALL); the tarball's install-sh rejects -o/-g and the
            # HMBS device/CI users are unprivileged (chown root fails).
            # Always route install through the tolerant cp/mkdir shim
            # (handles -o/-g/-u/-m/-c/-p/-d), incl. the libtool
            # --mode=install invocations in src/Makefile.
            _install_cmd = None
            try:
                _shim = self._write_install_shim()
                self._redirect_install_to_shim(_shim)
                self.output.info("HMBS diag install shim override=%s" % _shim)
                _install_cmd = _shim
            except Exception as _e:
                self.output.warning("HMBS diag install shim setup failed: %s" % _e)
                _install_cmd = None
            if _install_cmd:
                # Conan 2 configures with --prefix=/ (verified in the
                # configure line of job gnubatch-1.11-verify-20261010-11),
                # NOT --prefix=package_folder. The install dirs are
                # "$(DESTDIR)@bindir@" etc. with @bindir@=/bin, so the
                # Conan-standard DESTDIR=<package_folder> lands files in
                # <pkg>/bin with no nesting (the earlier "DESTDIR would
                # double-prefix" note assumed a baked package_folder
                # prefix that does not exist here). Without DESTDIR the
                # install writes to //bin and dies with EROFS
                # (job ...-11: "cp: //bin/gbch-pmenu: Read-only file
                # system"). STAGED_INSTALL is a plain make variable
                # (src/Makefile.in: `STAGED_INSTALL = false`): overriding
                # it to true short-circuits `$(STAGED_INSTALL) || perl
                # Checkuserinst/Checknetinst` — those exit 1 whenever the
                # gnubatch system user does not exist (always the case on
                # device/CI) and perl may be absent at all.
                self.run('make -j1 install INSTALL="%s" STAGED_INSTALL=true DESTDIR="%s"'
                         % (_install_cmd, self.package_folder))
            else:
                self.output.warning("HMBS diag no install override; using default install")
                autotools = Autotools(self)
                autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        # shipped license file is LICENSE (GPLv3 text)
        for _lic in ("LICENSE", "COPYING"):
            if os.path.isfile(os.path.join(self.source_folder, _lic)):
                copy(self, _lic, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"),
                     keep_path=False)
                break

    def package_info(self):
        # application suite with internal shared libs: keep lib/ on
        # LD_LIBRARY_PATH (libgnubatch_int/curs), no public headers
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        # bin = user front-ends (gbch-*); libexec/gnubatch = internal
        # programs (btsched, btexec, btpwchk, jobdump...); sbin = util
        # helpers (helpparse, gbpasswd, hostedit...)
        self.cpp_info.bindirs = ["bin", "libexec/gnubatch", "sbin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "libexec", "gnubatch"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "sbin"))
