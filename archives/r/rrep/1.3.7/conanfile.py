#!/usr/bin/env python3
"""Conan recipe — rrep 1.3.7 (Autotools).

Pattern replacement utility: searches input files for a pattern and replaces
it with a replacement string (regex, recursive, backup, dry-run, prompting).
Upstream: https://sourceforge.net/projects/rrep/
Build: autotools (configure + make), single bin_PROGRAMS (rrep).
Upstream ships no test suite (no tests/ dir, no TESTS/check target), so
build() runs configure + make only; functional coverage lives in test_package.
"""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class RrepConan(ConanFile):
    name = "rrep"
    version = "1.3.7"
    description = "Replace strings with regular expressions in files and directories"
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/rrep/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("rrep", "regex", "replace", "cli", "utility")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "rrep is supported only on Linux/OHOS, not %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-nls",
            "MAKEINFO=true",
        ])
        tc.generate()
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
            _old_c = _confmap.get("c") if isinstance(_confmap, dict) else None
            _old_cxx = _confmap.get("cpp") if isinstance(_confmap, dict) else None
            if _cc and _old_c and _cc != _old_c:
                os.environ["CC"] = _cc
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
                build_env.define("CC", _cc)
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
        # radcli/1.2.11 pattern: cp/mkdir shim tolerating chmod=0 and
        # supporting single + multi-source forms. Used only when no
        # tarball install-sh exists; install tool only, no test skipping.
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
                    "    if [ -d \"$dest\" ]; then chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else chmod \"$mode\" \"$dest\" 2>/dev/null || true; fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
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
            # HMDFS toybox install multi-file Error 64 (rarian/0.8.6 +
            # E596/libnih precedent): configure probes INSTALL to the HMBS
            # runtime shim binary whose multi-source
            # `install -c -m 644 README COPYING dest` fails with Error 64
            # (this round: install-dist_docDATA). Prefer the tarball's own
            # install-sh (found recursively: build-aux/, not top level),
            # else fall back to a cp/mkdir shim (radcli pattern) that
            # tolerates chmod=0. Never fall back to the broken probed
            # INSTALL. Scoped to install only.
            _install_cmd = None
            try:
                _found = self._find_install_sh()
            except Exception:
                _found = None
            if _found:
                self.output.info("HMBS diag install-sh override=%s" % _found)
                _install_cmd = "/bin/sh %s -c" % _found
            else:
                try:
                    _shim = self._write_install_shim()
                    self._redirect_install_to_shim(_shim)
                    self.output.info("HMBS diag install shim override=%s" % _shim)
                    _install_cmd = _shim
                except Exception as _e:
                    self.output.warning("HMBS diag install shim setup failed: %s" % _e)
                    _install_cmd = None
            if _install_cmd:
                self.run('make -j1 install DESTDIR="%s" INSTALL="%s"'
                         % (self.package_folder, _install_cmd))
            else:
                self.output.warning("HMBS diag no install override; using default install")
                autotools = Autotools(self)
                autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
