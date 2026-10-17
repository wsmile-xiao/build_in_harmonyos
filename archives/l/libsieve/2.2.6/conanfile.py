#!/usr/bin/env python3
"""Conan recipe -- libsieve 2.2.6 (Autotools, configure lives in src/)."""
import contextlib
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


@contextlib.contextmanager
def _env_append(env_vars):
    """Portable replacement for conan.tools.env.environment_append.

    conan 2.30 no longer exports environment_append (ImportError blocks
    the whole recipe). Plain os.environ save/restore works on every
    Conan 2.x and, together with the generate() Environment script
    (which wins inside the conanbuild aggregation), guarantees the
    HMBS writable TMPDIR/SHELL reach configure/make children.
    """
    saved = {}
    for _k, _v in env_vars.items():
        saved[_k] = os.environ.get(_k)
        os.environ[_k] = _v
    try:
        yield
    finally:
        for _k, _old in saved.items():
            if _old is None:
                os.environ.pop(_k, None)
            else:
                os.environ[_k] = _old


class LibsieveConan(ConanFile):
    name = "libsieve"
    version = "2.2.6"
    description = "Library for parsing, sorting and filtering mail (Sieve mail filtering language, RFC 3028)"
    license = "LGPL-2.1"
    homepage = "http://libsieve.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # Round-4: no tool_requires. Round-3 declared flex/bison but the
        # true machine still reported `checking for flex... no` even
        # though both recipes downloaded (no aarch64 prebuilt binary in
        # PATH). The tarball already ships pre-generated sieve-lex.c /
        # sieve.c, so use local flex/bison shims + timestamp refresh
        # instead of external generator binaries.
        pass

    def layout(self):
        basic_layout(self)

    def _hmbs_writable_tmpdir(self):
        """Pick a truly writable tmpdir (HMBS readonly-/tmp fix).

        Priority: HMBS_TMPDIR > HMBS_PLATFORM_CAPABILITIES.tmpdir >
        TMPDIR/TMP/TEMP (non-/tmp) > HMBS_AUTOCONF_MKTEMP_FALLBACK >
        ~/tmp > build_folder/.tmp. Each candidate is verified with a real
        makedirs + open/write/unlink probe (HMDFS ignores chmod and
        os.access(X_OK), so permission probing is not reliable).
        """
        cands = []
        v = os.environ.get("HMBS_TMPDIR")
        if v:
            cands.append(v)
        cap = os.environ.get("HMBS_PLATFORM_CAPABILITIES")
        if cap:
            try:
                cands.append(json.loads(cap).get("tmpdir", ""))
            except Exception:
                pass
        for k in ("TMPDIR", "TMP", "TEMP"):
            v = os.environ.get(k)
            if v and v != "/tmp":
                cands.append(v)
        v = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if v:
            cands.append(v)
        try:
            cands.append(os.path.join(os.path.expanduser("~"), "tmp"))
        except Exception:
            pass
        try:
            cands.append(os.path.join(self.build_folder, ".tmp"))
        except Exception:
            pass
        for c in cands:
            if not c:
                continue
            try:
                os.makedirs(c, exist_ok=True)
                probe = os.path.join(c, ".tmp-write-probe")
                with open(probe, "w") as _pf:
                    _pf.write("ok")
                os.unlink(probe)
                return c
            except OSError:
                continue
        fallback = os.path.join(self.build_folder, ".tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _hmbs_working_shell(self):
        """Prefer HMBS-provided /bin/sh; hnp bash is inaccessible in sandbox."""
        cap_shell = ""
        cap = os.environ.get("HMBS_PLATFORM_CAPABILITIES")
        if cap:
            try:
                cap_shell = json.loads(cap).get("shell", "")
            except Exception:
                cap_shell = ""
        for cand in (cap_shell, os.environ.get("SHELL"), "/bin/sh",
                     "/system/bin/sh"):
            if cand and os.path.exists(cand):
                return cand
        return "/bin/sh"

    def _hmbs_toolchain_vars(self):
        """Resolve absolute toolchain binaries (Exp2 adapt + empty-var fix).

        Profile ohos-aarch64 sets tools.build:compiler_executables as a
        dict {c, cpp}. Some workers export AS/AR/... as empty strings,
        which defeats upstream `${VAR-default}` fallbacks (empty !=
        unset). Return explicit absolute paths so the configure command
        line can pin them inline (R33, wins over any inherited empty).
        """
        def _pick(conf_key, hnp_name, path_name):
            v = None
            try:
                v = self.conf.get(conf_key, check_type=str)
            except Exception:
                v = None
            if v:
                return v
            for cand in ("/data/service/hnp/bin/%s" % hnp_name,
                         path_name):
                try:
                    if cand and os.path.isfile(cand):
                        return cand
                except Exception:
                    continue
            return path_name

        cc = _pick("tools.build:compiler_executables:c",
                   "clang", "clang")
        cxx = None
        try:
            cxx = self.conf.get("tools.build:compiler_executables:cpp",
                                check_type=str)
        except Exception:
            cxx = None
        if not cxx:
            # Derive CXX from CC (clang -> clang++, gcc -> g++).
            if cc.endswith("clang"):
                cxx = cc + "++"
            elif cc.endswith("gcc"):
                cxx = cc[:-3] + "g++"
            else:
                cxx = _pick("tools.build:compiler_executables:cpp",
                            "clang++", "clang++")
        tools = {
            "CC": cc,
            "CXX": cxx,
            # AS via CC (clang assembles -c directly; avoids empty $AS).
            "AS": cc,
            "AR": _pick("tools.build:compiler_executables:ar",
                        "llvm-ar", "llvm-ar"),
            "RANLIB": _pick("tools.build:compiler_executables:ranlib",
                            "llvm-ranlib", "llvm-ranlib"),
            "NM": _pick("tools.build:compiler_executables:nm",
                        "llvm-nm", "llvm-nm"),
            "STRIP": _pick("tools.build:compiler_executables:strip",
                           "llvm-strip", "llvm-strip"),
        }
        return tools

    def _hmbs_workdir(self):
        """Shallow HMDFS-safe work dir (DRAFT-6487 adapt).

        conan cache `p/b/<hash>/b/build-release` triggers getcwd storms
        with hnp bash; its parent `.../b` (base_build_folder) is proven
        calm. Build there via shell-internal `cd` instead of cwd= param
        so neither Python nor the outer shell chdirs to the deep path.
        """
        w = None
        try:
            w = self.base_build_folder
        except Exception:
            w = None
        if not w:
            try:
                w = os.path.dirname(self.build_folder.rstrip("/\\"))
            except Exception:
                w = self.build_folder
        try:
            os.makedirs(w, exist_ok=True)
        except Exception:
            pass
        return w

    def _ensure_lex_yacc_shims(self, workdir, shell):
        """Create local flex/bison/lex shims (Round-4, pregenerated route).

        Round-3 assumed the missing generator itself was the root cause
        and declared flex/bison tool_requires, but the true machine still
        logged `checking for flex... no` after downloading both recipes
        (no usable aarch64 binary landed in PATH). The release tarball
        already contains pre-generated sieve-lex.c / sieve.c, so the
        generators are never needed at build time -- configure only needs
        *some* `flex` executable to pass its AM_PROG_LEX output-root
        probe (`missing --run` hard-errors when flex is absent). These
        shims satisfy that probe (produce the expected output file,
        exit 0) while timestamp refresh below keeps make from ever
        invoking a real regeneration.
        """
        shimdir = os.path.join(workdir, ".hmbs-shims")
        try:
            os.makedirs(shimdir, exist_ok=True)
        except Exception:
            pass
        flex_body = (
            "#!%s\n"
            "out=\"lex.yy.c\"\n"
            "prev=\"\"\n"
            "for a in \"$@\"; do\n"
            "  if [ \"$prev\" = \"-o\" ]; then out=\"$a\"; prev=\"\"; continue; fi\n"
            "  case \"$a\" in -o) prev=\"-o\";; -o*) out=\"${a#-o}\";; esac\n"
            "done\n"
            ": > \"$out\" 2>/dev/null || touch \"$out\"\n"
            "exit 0\n" % shell
        )
        bison_body = (
            "#!%s\n"
            "out=\"\"; prev=\"\"; yacc=0\n"
            "for a in \"$@\"; do\n"
            "  if [ \"$prev\" = \"-o\" ]; then out=\"$a\"; prev=\"\"; continue; fi\n"
            "  case \"$a\" in -o) prev=\"-o\";; -o*) out=\"${a#-o}\";; -y|--yacc) yacc=1;; esac\n"
            "done\n"
            "if [ -z \"$out\" ]; then if [ \"$yacc\" = \"1\" ]; then out=\"y.tab.c\"; else out=\"sieve.tab.c\"; fi; fi\n"
            ": > \"$out\" 2>/dev/null || touch \"$out\"\n"
            "exit 0\n" % shell
        )
        for name, body in (("flex", flex_body), ("lex", flex_body),
                           ("bison", bison_body), ("yacc", bison_body)):
            p = os.path.join(shimdir, name)
            try:
                with open(p, "w", newline="\n") as _f:
                    _f.write(body)
            except OSError:
                continue
            try:
                os.chmod(p, 0o755)
            except Exception:
                pass
        # Keep make from regenerating: pregenerated outputs newer than .l/.y.
        # Covers both lex (.l -> *-lex.c) and yacc (.y -> addr/header/sieve.c)
        # outputs so the flex/bison shims are never invoked for real.
        try:
            for _root, _dirs, _files in os.walk(self.source_folder):
                for _fn in _files:
                    if _fn in ("sieve-lex.c", "sieve.c", "sieve-lex.h",
                               "sieve.h", "addr.c", "addr-lex.c",
                               "header.c", "header-lex.c",
                               "lex.yy.c", "sieve.tab.c",
                               "sieve.tab.h", "y.tab.c", "y.tab.h"):
                        try:
                            os.utime(os.path.join(_root, _fn), None)
                        except Exception:
                            pass
        except Exception:
            pass
        return shimdir

    def _patch_configure_umask(self):
        """Fix E011 HMDFS umask 077 config.status failure (buildtorrent adapt).

        Old autoconf (libsieve src/configure, 2007 era) does
        `umask 077` before `mktemp -d ./confgXXXXXX`. On HMDFS the
        0700 (drwx--S---) temp dir is unreadable to the same process
        (UID mapping), so config.status cannot create subs-*.sed/awk
        and no Makefile is generated. Replace with `umask 022`
        (E011 rec_command). This covers both the configure body and
        the embedded config.status template, so the generated
        config.status is already fixed. TMPDIR redirect alone cannot
        fix it because the failing tmp is `./confgXXXXXX`, not $TMPDIR.
        """
        patched = 0
        try:
            for _root, _dirs, _files in os.walk(self.source_folder):
                for _fn in _files:
                    if _fn != "configure":
                        continue
                    _p = os.path.join(_root, _fn)
                    try:
                        with open(_p, "rb") as _f:
                            _data = _f.read()
                        if b"umask 077" not in _data:
                            continue
                        _n = _data.count(b"umask 077")
                        _data = _data.replace(b"umask 077", b"umask 022")
                        try:
                            os.chmod(_p, 0o755)
                        except Exception:
                            pass
                        with open(_p, "wb") as _f:
                            _f.write(_data)
                        patched += _n
                        self.output.info("HMBS umask patch %s: %d occurrence(s) 077->022" % (_p, _n))
                    except Exception as _e:
                        self.output.warning("HMBS umask patch skipped %s: %s" % (_p, _e))
        except Exception as _e:
            self.output.warning("HMBS umask patch walk failed: %s" % _e)
        if not patched:
            self.output.warning("HMBS umask patch: no 'umask 077' found (unexpected)")
        return patched

    def _patch_fno_common(self):
        """Declare libsieve_parse_context extern in addr.c/addr.y (Round-8).

        Replaces the removed 0002 unified-diff patch: that diff parsed but
        its addr.y context did not match the real tarball bytes (conan
        reported `source file is different - src/sv_parser/addr.y`), and
        hand-tuning context lines without the pristine bytes is guesswork.
        Byte-level replacement of the single tentative-definition line is
        immune to surrounding-line drift. The single definition stays in
        sieve.c (never touched here); only the addr.c/addr.y tentative
        definitions become extern declarations. Idempotent: already-extern
        lines are left alone. Raises when no anchor and no prior extern is
        found, so a silent no-op can never pass as fixed; on miss it dumps
        the real `libsieve_parse_context` lines at ERROR level for the next
        round's evidence.
        """
        _target = b"struct sieve2_context *libsieve_parse_context;"
        _repl = b"extern struct sieve2_context *libsieve_parse_context;"
        _rels = ("src/sv_parser/addr.c", "src/sv_parser/addr.y")
        total = 0
        for _rel in _rels:
            _p = os.path.join(self.source_folder, _rel)
            if not os.path.isfile(_p):
                self.output.warning("HMBS fno-common: missing %s" % _rel)
                continue
            try:
                with open(_p, "rb") as _f:
                    _data = _f.read()
            except Exception as _e:
                self.output.warning("HMBS fno-common: cannot read %s: %s" % (_rel, _e))
                continue
            _lines = _data.split(b"\n")
            _n = 0
            for _i, _ln in enumerate(_lines):
                if _ln.strip() == _target:
                    _lines[_i] = _ln.replace(_target, _repl)
                    _n += 1
            if _n:
                try:
                    with open(_p, "wb") as _f:
                        _f.write(b"\n".join(_lines))
                    self.output.info("HMBS fno-common %s: %d line(s) tentative -> extern" % (_rel, _n))
                    total += _n
                except Exception as _e:
                    raise ConanException("libsieve fno-common write failed %s: %s" % (_rel, _e))
            elif _repl in _data:
                self.output.info("HMBS fno-common %s: already extern, nothing to do" % _rel)
            else:
                self.output.warning("HMBS fno-common %s: anchor not found" % _rel)
                for _ln in _data.split(b"\n"):
                    if b"libsieve_parse_context" in _ln:
                        try:
                            self.output.error("HMBS fno-common CTX %s: %s" % (_rel, _ln.strip()[:200].decode("utf-8", "replace")))
                        except Exception:
                            pass
        if not total:
            _any = False
            for _rel in _rels:
                try:
                    with open(os.path.join(self.source_folder, _rel), "rb") as _f:
                        if _repl in _f.read():
                            _any = True
                except Exception:
                    pass
            if not _any:
                raise ConanException("libsieve fno-common anchors missing in addr.c/addr.y (see HMBS fno-common CTX lines)")
        return total

    def _patch_headererror_const(self):
        """Align libsieve_headererror prototype to const (Round-9).

        True-machine clang-15 fails in sv_parser/header.lo:
        headerinc.h declares void libsieve_headererror(char *str) but the
        shipped pregenerated header.c defines
        void libsieve_headererror(const char *s) (via line 77 header.y),
        so clang reports conflicting types for libsieve_headererror.
        The .y source still says char *s; the .c was regenerated with a
        newer bison skeleton (const yyerror) without syncing the .y and
        header. Byte-level edits (same pattern as _patch_fno_common):
        headerinc.h + header.y signatures become const, and the
        libsieve_do_error_header(..., s) call sites in header.y + header.c
        gain an explicit (char *) cast so passing the now-const s to the
        char *msg callback stays warning-free. Idempotent; raises with
        ERROR dump when no anchor is found so a silent no-op never passes.
        """
        _decl_old = b"void libsieve_headererror(char *str);"
        _decl_new = b"void libsieve_headererror(const char *str);"
        _def_old = b"void libsieve_headererror(char *s)"
        _def_new = b"void libsieve_headererror(const char *s)"
        _call_old = b"libsieve_do_error_header(libsieve_parse_context, libsieve_headerlineno, s)"
        _call_new = b"libsieve_do_error_header(libsieve_parse_context, libsieve_headerlineno, (char *)s)"
        _files = ("src/sv_parser/headerinc.h", "src/sv_parser/header.y",
                  "src/sv_parser/header.c")
        for _rel in _files:
            _p = os.path.join(self.source_folder, _rel)
            if not os.path.isfile(_p):
                self.output.warning("HMBS headererror-const: missing %s" % _rel)
                continue
            try:
                with open(_p, "rb") as _f:
                    _data = _f.read()
            except Exception as _e:
                self.output.warning("HMBS headererror-const: cannot read %s: %s" % (_rel, _e))
                continue
            _orig = _data
            if _decl_old in _data:
                _data = _data.replace(_decl_old, _decl_new)
            if _def_old in _data:
                _data = _data.replace(_def_old, _def_new)
            if _call_old in _data and _call_new not in _data:
                _data = _data.replace(_call_old, _call_new)
            if _data != _orig:
                try:
                    with open(_p, "wb") as _f:
                        _f.write(_data)
                    self.output.info("HMBS headererror-const patched %s" % _rel)
                except Exception as _e:
                    raise ConanException("libsieve headererror-const write failed %s: %s" % (_rel, _e))
            else:
                self.output.info("HMBS headererror-const %s: already aligned, nothing to do" % _rel)
        _ok = True
        for _rel, _needle in (("src/sv_parser/headerinc.h", _decl_new),
                              ("src/sv_parser/header.y", _def_new),
                              ("src/sv_parser/header.c", _def_new)):
            try:
                with open(os.path.join(self.source_folder, _rel), "rb") as _f:
                    if _needle not in _f.read():
                        _ok = False
                        self.output.error("HMBS headererror-const MISS %s" % _rel)
            except Exception as _e:
                _ok = False
                self.output.error("HMBS headererror-const reread failed %s: %s" % (_rel, _e))
        if not _ok:
            raise ConanException("libsieve headererror const alignment anchors missing (see HMBS headererror-const MISS lines)")
        return True

    def _patch_example_eof(self):
        """Drop the spurious EOF byte in sv_test/example.c read_file (Round-10).

        Upstream read_file does `f_buf[f_pos] = fgetc(f)` inside a
        `while (!feof(f))` loop, so the final fgetc hits EOF (-1) and stores
        byte 0xFF before NUL: every script/message buffer ends with
        "...\\n\\xFF\\0". The sieve lexer fallback (`. return yytext[0];`)
        returns that byte as a token; bison treats `<= YYEOF (0)` as EOF, so
        on x86 (signed char) -1 is silently accepted as EOF while on ARM
        (unsigned char, AArch64 default) it arrives as 255 -> the parser
        reports `syntax error, unexpected $undefined` on the trailing empty
        line of every script (true-machine log: script10.sv line 25,
        script11.sv line 9, script12.sv line 6, 36/37 failed, only testcomp
        passed). Byte-level single-statement fix: break on EOF instead of
        storing it. Test-harness only (installed lib untouched); not an
        assertion deletion. Idempotent; raises with ERROR dump on miss.
        """
        _rel = "src/sv_test/example.c"
        _p = os.path.join(self.source_folder, _rel)
        if not os.path.isfile(_p):
            raise ConanException("libsieve example-eof patch: missing %s" % _rel)
        try:
            with open(_p, "rb") as _f:
                _data = _f.read()
        except Exception as _e:
            raise ConanException("libsieve example-eof patch: cannot read %s: %s" % (_rel, _e))
        _fixed = b"{ int _c = fgetc(f); if (_c == EOF) break; f_buf[f_pos] = (char)_c; }"
        if _fixed in _data:
            self.output.info("HMBS example-eof %s: already fixed, nothing to do" % _rel)
            return True
        _old = b"f_buf[f_pos] = fgetc(f);"
        if _old not in _data:
            for _ln in _data.split(b"\n"):
                if b"fgetc(f)" in _ln:
                    try:
                        self.output.error("HMBS example-eof CTX: %s" % _ln.strip()[:200].decode("utf-8", "replace"))
                    except Exception:
                        pass
            raise ConanException("libsieve example-eof anchor missing in %s (see HMBS example-eof CTX lines)" % _rel)
        _data = _data.replace(_old, _fixed)
        try:
            with open(_p, "wb") as _f:
                _f.write(_data)
            self.output.info("HMBS example-eof patched %s" % _rel)
        except Exception as _e:
            raise ConanException("libsieve example-eof write failed %s: %s" % (_rel, _e))
        return True

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        if self.settings.os == "OHOS":
            # Upstream ships 2007 config.guess/sub which predate aarch64.
            # patches/0001-src-config.sub.patch teaches config.sub the
            # aarch64 triplets so explicit triplets canonicalize cleanly.
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()
        # HMBS preflight: /tmp is read-only erofs, and the profile's
        # CONFIG_SHELL (/data/service/hnp/bin/bash) is inaccessible in the
        # sandbox ("inaccessible or not found" -> compiler test Error 77).
        # Redirect temp root to the HMBS-provided writable tmpdir and pin
        # both shells to the working /bin/sh for configure/make children.
        # Dual-inject CC/CXX here as well (Exp2): build() pins them inline
        # again so an empty inherited value cannot win.
        try:
            _tmp = self._hmbs_writable_tmpdir()
            _sh = self._hmbs_working_shell()
            _tools = self._hmbs_toolchain_vars()
            env = Environment()
            env.define("TMPDIR", _tmp)
            env.define("TMP", _tmp)
            env.define("TEMP", _tmp)
            env.define("SHELL", _sh)
            env.define("CONFIG_SHELL", _sh)
            env.define("CC", _tools["CC"])
            env.define("CXX", _tools["CXX"])
            env.vars(self).save_script("hmbs_tmp_shell")
        except Exception as e:
            self.output.warning("HMBS tmp/shell env setup skipped: %s" % e)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dump_config_log(self):
        """Print config.log excerpts so the next round sees the real error.

        Round-2 inline SHELL/TMPDIR removed the hnp-bash line but Error 77
        persists, so dump the actual compiler invocation: 60 lines around
        the first 'cannot create executables', plus the 'failed program
        was' block and surrounding 'checking for C compiler' context.
        Also covers the shallow workdir (base_build_folder).
        """
        cands = []
        try:
            cands.append(os.path.join(self._hmbs_workdir(), "config.log"))
        except Exception:
            pass
        cands += [
            os.path.join(self.build_folder, "config.log"),
            os.path.join(self.build_folder, "src", "config.log"),
            os.path.join(self.source_folder, "src", "config.log"),
            os.path.join(self.source_folder, "config.log"),
        ]
        for p in cands:
            try:
                if os.path.isfile(p):
                    self.output.error("=== config.log: %s ===" % p)
                    with open(p, "r", errors="replace") as f:
                        lines = f.read().splitlines()
                    idx = None
                    for i, ln in enumerate(lines):
                        if "cannot create executables" in ln.lower():
                            idx = i
                            break
                    if idx is not None:
                        lo = max(0, idx - 60)
                        hi = min(len(lines), idx + 20)
                        for ln in lines[lo:hi]:
                            self.output.error("CFGCTX: " + ln[:400])
                    # Failed-program block is the ground truth.
                    for i, ln in enumerate(lines):
                        if "failed program was" in ln.lower():
                            for ln2 in lines[i:i + 25]:
                                self.output.error("CFGPROG: " + ln2[:400])
                            break
                    interesting = [ln for ln in lines
                                   if "error" in ln.lower() or "cannot" in ln.lower()
                                   or "temporary" in ln.lower() or "readonly" in ln.lower()
                                   or "conftest" in ln.lower() or "clang" in ln.lower()]
                    for ln in interesting[-30:]:
                        self.output.error("CFGLOG: " + ln[:400])
                    for ln in lines[-15:]:
                        self.output.error("CFGTAIL: " + ln[:400])
                    return
            except Exception as e:
                self.output.warning("config.log dump failed: %s" % e)
        self.output.warning("config.log not found in build/source folders")

    def _dump_make_log(self, workdir):
        """Emit make.log tail as ERROR so HMBS summaries preserve it.

        Round-6: configure exits 0 (CFGTAIL proves it) but
        `make -j1` dies with Error 2; the聚焦摘要 omits the middle
        of stdout, so the real failing command/undefined symbol is
        lost. make output is redirected to make.log; this dump
        re-emits the last 80 lines plus error-keyword lines with the
        ERROR level (same channel as CFGLOG, which the summary kept).
        """
        cands = []
        try:
            cands.append(os.path.join(workdir, "make.log"))
        except Exception:
            pass
        try:
            cands.append(os.path.join(self.build_folder, "make.log"))
        except Exception:
            pass
        for p in cands:
            try:
                if os.path.isfile(p):
                    self.output.error("=== make.log: %s ===" % p)
                    with open(p, "r", errors="replace") as f:
                        lines = f.read().splitlines()
                    key = [ln for ln in lines
                           if "error" in ln.lower() or "undefined" in ln.lower()
                           or "cannot" in ln.lower() or "failed" in ln.lower()
                           or "no such" in ln.lower() or "***" in ln]
                    for ln in key[-30:]:
                        self.output.error("MAKEERR: " + ln[:400])
                    for ln in lines[-80:]:
                        self.output.error("MAKETAIL: " + ln[:400])
                    return
            except Exception as e:
                self.output.warning("make.log dump failed: %s" % e)
        self.output.warning("make.log not found in work/build folders")

    def _first_make_error(self, workdir):
        """Return the first linker/compiler error line (<=300 chars).

        The聚焦摘要 keeps the final `Error in build() method` block
        but may omit the middle ERROR dumps, so the fingerprint is
        embedded into the raised exception message itself.
        """
        cands = []
        for base in (workdir, self.build_folder):
            try:
                cands.append(os.path.join(base, "make.log"))
            except Exception:
                pass
        for p in cands:
            try:
                if not os.path.isfile(p):
                    continue
                with open(p, "r", errors="replace") as f:
                    lines = f.read().splitlines()
                for ln in lines:
                    low = ln.lower()
                    if ("multiple definition" in low or "undefined" in low
                            or "undefined symbol" in low or "error:" in low
                            or "*** " in ln and "error" in low):
                        return ln.strip()[:300]
                for ln in reversed(lines):
                    if ln.strip():
                        return ln.strip()[:300]
            except Exception:
                pass
        return "unknown (make.log missing)"

    def build(self):
        # Round-4 (different route from round-3 tool_requires): the tarball
        # already ships pre-generated sieve-lex.c / sieve.c, so satisfy the
        # AM_PROG_LEX probe with local flex/bison/lex/yacc shims on an
        # inline PATH instead of external generator binaries. Timestamp
        # refresh in _ensure_lex_yacc_shims keeps make from regenerating.
        # Toolchain inline pins + shallow base_build_folder build kept
        # from round-2/3 (they fixed hnp-bash + Error 77).
        # Manual configure keeps --prefix=/ : OHOS conan's
        # Autotools.install() auto-injects DESTDIR=<package_folder>.
        _tmp = self._hmbs_writable_tmpdir()
        _sh = self._hmbs_working_shell()
        _tools = self._hmbs_toolchain_vars()
        _work = self._hmbs_workdir()
        _shimdir = self._ensure_lex_yacc_shims(_work, _sh)
        self.output.info("HMBS tmpdir=%s shell=%s work=%s" % (_tmp, _sh, _work))
        self.output.info("HMBS toolchain CC=%s CXX=%s AR=%s" % (_tools["CC"], _tools["CXX"], _tools["AR"]))
        self.output.info("HMBS lex/yacc shims in %s" % _shimdir)
        apply_conandata_patches(self)
        # E011: umask 077 -> 022 before configure (else config.status
        # ./confgXXXXXX is drwx--S--- on HMDFS and no Makefile appears).
        self._patch_configure_umask()
        # Round-8: -fno-common tentative-definition fix via byte-level text
        # edit (replaces the removed 0002 unified diff, whose addr.y context
        # mismatched the real tarball bytes). sieve.c keeps the single
        # definition; only addr.c/addr.y become extern declarations.
        self._patch_fno_common()
        # Round-9: clang-15 conflicting types for libsieve_headererror
        # (headerinc.h char * vs pregenerated header.c const char *).
        self._patch_headererror_const()
        # Round-10: example.c read_file stores fgetc EOF (-1) as 0xFF byte;
        # unsigned-char ARM lexer returns it as token 255 ($undefined) at
        # every script's trailing empty line (36/37 failed). Break on EOF.
        self._patch_example_eof()
        # Re-touch after patches so pregenerated outputs stay newer than .l/.y.
        self._ensure_lex_yacc_shims(_work, _sh)
        # The top-level Makefile only handles releases; the real
        # configure + Makefile.in live in src/ (berkeley-db pattern).
        conf = os.path.join(self.source_folder, "src", "configure")
        if self.options.shared:
            _lib_args = "--enable-shared --disable-static"
        else:
            _lib_args = "--enable-static --disable-shared"
        _prefix = ("PATH=\"%s:$PATH\" LEX=\"flex\" YACC=\"bison -y\" "
                   "CONFIG_SHELL=\"%s\" SHELL=\"%s\" TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
                   "CC=\"%s\" CXX=\"%s\" AS=\"%s\" AR=\"%s\" RANLIB=\"%s\" NM=\"%s\" STRIP=\"%s\"" % (
                       _shimdir,
                       _sh, _sh, _tmp, _tmp, _tmp,
                       _tools["CC"], _tools["CXX"], _tools["AS"],
                       _tools["AR"], _tools["RANLIB"], _tools["NM"], _tools["STRIP"]))
        # Compiler sanity before configure (Round-5 fork-starved adapt):
        # three separate self.run probes cost three conan shell forks
        # before configure even starts; on a box logging "can't fork"
        # each extra fork is another failure opportunity. Run all three
        # diagnostics (clang version, shim presence, CC pipe compile)
        # inside ONE shell so pre-configure forks drop 3 -> 1 with
        # identical checks and identical HMBS_*_OK markers.
        self.run("cd \"%s\" && %s sh -c '\"%s\" --version && command -v flex && command -v bison && echo HMBS_SHIM_OK && echo \"int main(){return 0;}\" | \"%s\" -x c - -o \"%s/conftest-probe\" && rm -f \"%s/conftest-probe\" && echo HMBS_CC_PROBE_OK'" % (_work, _prefix, _tools["CC"], _tools["CC"], _tmp, _tmp), env="conanbuild")
        cfg_cmd = ("cd \"%s\" && %s \"%s\" \"%s\" --prefix=/ %s --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu" % (_work, _prefix, _sh, conf, _lib_args))
        try:
            self.run(cfg_cmd, env="conanbuild")
        except ConanException:
            self._dump_config_log()
            raise
        # Round-6: guard + verbose make to file. Configure proved OK
        # (exit 0), so a missing Makefile here means config.status wrote
        # elsewhere; fail fast with an explicit listing instead of a
        # cryptic make Error 2. V=1 surfaces the failing cc/ld line;
        # redirect+tail keeps it at stdout tail (summary keeps the end)
        # and _dump_make_log re-emits it on the ERROR channel.
        import glob as _glob
        if not os.path.isfile(os.path.join(_work, "Makefile")):
            try:
                self.output.error("HMBS no Makefile in work=%s; listing:" % _work)
                for _p in sorted(_glob.glob(os.path.join(_work, "*")))[:40]:
                    self.output.error("WORKLS: " + _p[:400])
            except Exception:
                pass
            self._dump_config_log()
            raise ConanException("libsieve configure produced no Makefile in %s" % _work)
        _make_log = os.path.join(_work, "make.log")
        try:
            self.run("cd \"%s\" && %s sh -c 'make -j1 V=1 > \"%s\" 2>&1; rc=$?; tail -n 60 \"%s\"; exit $rc'" % (_work, _prefix, _make_log, _make_log), env="conanbuild")
        except ConanException as _make_exc:
            self._dump_make_log(_work)
            self._dump_config_log()
            raise ConanException(
                "libsieve make -j1 failed in %s; first error: %s"
                % (_work, self._first_make_error(_work))) from _make_exc
        _env = {"TMPDIR": _tmp, "TMP": _tmp, "TEMP": _tmp,
                "SHELL": _sh, "CONFIG_SHELL": _sh}
        with _env_append(_env):
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the real upstream suite: testcomp + testvalid(12) + testmessage(24)."""
        # Build now happens in the shallow workdir (base_build_folder);
        # fall back to build_folder for older trees.
        try:
            _work = self._hmbs_workdir()
        except Exception:
            _work = self.build_folder
        build_test = os.path.join(_work, "sv_test")
        if not os.path.isfile(os.path.join(build_test, "testcomp")):
            build_test = os.path.join(self.build_folder, "sv_test")
        src_test = os.path.join(self.source_folder, "src", "sv_test")
        total = 0
        passed = 0
        # 1) comparator unit binary: 134 internal assertions, exit code verdict.
        total += 1
        if self.run(os.path.join(build_test, "testcomp"), ignore_errors=True) == 0:
            passed += 1
        else:
            self.output.warning("upstream testcomp FAILED")
        # 2) script validation loop (upstream testvalid.sh, scripts 1-12).
        for i in range(1, 13):
            total += 1
            cmd = "%s %s" % (os.path.join(build_test, "example"),
                             os.path.join(src_test, "script%d.sv" % i))
            if self.run(cmd, ignore_errors=True) == 0:
                passed += 1
            else:
                self.output.warning("upstream validation FAILED: script%d.sv" % i)
        # 3) message execution loop (upstream testmessage.sh, scripts 1-12
        # on messagea/messageb). stdin from /dev/null: vacation-action
        # scripts (5, 7) ask one getchar() question, EOF answers "no".
        for i in range(1, 13):
            for mbox in ("messagea.mbox", "messageb.mbox"):
                total += 1
                cmd = "%s %s %s < /dev/null" % (
                    os.path.join(build_test, "example"),
                    os.path.join(src_test, "script%d.sv" % i),
                    os.path.join(src_test, mbox))
                if self.run(cmd, ignore_errors=True) == 0:
                    passed += 1
                else:
                    self.output.warning("upstream message run FAILED: script%d.sv %s" % (i, mbox))
        failed = total - passed
        result = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "sv_test-shell",
            "command": "testcomp + testvalid.sh(12) + testmessage.sh(24)",
            "discovered": total,
            "executed": total,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "reason": "testcomp(1)+testvalid(12)+testmessage(24) all unattended; vacation stdin from /dev/null",
        }
        _marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result)
        # Dual-channel emit (stdout + conan output) so HMBS summaries keep it.
        print(_marker)
        try:
            self.output.info(_marker)
        except Exception:
            pass
        # Persist for cache-hit rounds: package() carries this file in
        # package/res and test_package re-emits it when build() is skipped.
        for _base in (self.build_folder, _work):
            try:
                if _base:
                    _p = os.path.join(_base, "hmbs_upstream.json")
                    with open(_p, "w", encoding="utf-8", newline="\n") as _f:
                        _f.write(json.dumps(result))
                    self.output.info("HMBS upstream result persisted: %s" % _p)
                    break
            except Exception as _e:
                self.output.warning("HMBS upstream persist skipped %s: %s" % (_base, _e))
        if failed:
            raise ConanException("libsieve upstream tests failed: %d/%d" % (failed, total))

    def package(self):
        # HMDFS-safe manual install (Round-11): old libtool
        # `make install` does `install -c .libs/libsieve.a DEST`
        # + explicit `chmod 644 DEST` + ranlib. True-machine caps are
        # chmod:0/hardlink:0 with install_shim:true, and the package
        # step fails as `chmod: cannot access '.../p//lib/libsieve.a':
        # No such file or directory` right after the shimmed install
        # line (ERROR in package(), make[2] install-libLTLIBRARIES).
        # Bypass install(1)/chmod/hardlink entirely: Python copy of
        # the already-ranlib'd .libs archive + public sieve2*.h
        # headers. No shell, no install-sh, no chmod.
        import glob as _glob
        try:
            _work = self._hmbs_workdir()
        except Exception:
            _work = self.build_folder
        _libdir = os.path.join(self.package_folder, "lib")
        _incdir = os.path.join(self.package_folder, "include")
        try:
            os.makedirs(_libdir, exist_ok=True)
            os.makedirs(_incdir, exist_ok=True)
        except Exception:
            pass
        # --- libs: find built archives under the shallow workdir ---
        _lib_cands = []
        for _pat in (os.path.join(_work, ".libs", "libsieve.a"),
                     os.path.join(_work, "**", ".libs", "libsieve.a"),
                     os.path.join(_work, "**", "libsieve.a")):
            try:
                _lib_cands.extend(_glob.glob(_pat, recursive=True))
            except Exception:
                pass
        _lib_src = None
        for _c in _lib_cands:
            try:
                if os.path.isfile(_c):
                    _lib_src = _c
                    break
            except Exception:
                continue
        _so_cands = []
        for _pat in (os.path.join(_work, ".libs", "libsieve.so*"),
                     os.path.join(_work, "**", ".libs", "libsieve.so*")):
            try:
                _so_cands.extend(_glob.glob(_pat, recursive=True))
            except Exception:
                pass
        _copied = []
        if self.options.shared:
            for _s in _so_cands:
                try:
                    if os.path.isfile(_s) and not os.path.islink(_s):
                        copy(self, os.path.basename(_s),
                             src=os.path.dirname(_s), dst=_libdir,
                             keep_path=False)
                        _copied.append(_s)
                    elif os.path.islink(_s):
                        # HMDFS-safe: copy link target content under
                        # the link name (no symlinks in package).
                        try:
                            _t = os.path.join(os.path.dirname(_s),
                                              os.readlink(_s))
                        except Exception:
                            _t = None
                        if _t and os.path.isfile(_t):
                            copy(self, os.path.basename(_t),
                                 src=os.path.dirname(_t), dst=_libdir,
                                 keep_path=False)
                            _copied.append(_s + "->" + _t)
                except Exception as _e:
                    self.output.warning("HMBS manual-install so skip %s: %s" % (_s, _e))
        else:
            if _lib_src:
                try:
                    copy(self, "libsieve.a",
                         src=os.path.dirname(_lib_src), dst=_libdir,
                         keep_path=False)
                    _copied.append(_lib_src)
                except Exception as _e:
                    raise ConanException(
                        "libsieve manual install copy failed %s: %s"
                        % (_lib_src, _e))
        # --- headers: public sieve2*.h wherever they live in-tree ---
        _hdr_cands = []
        for _pat in (os.path.join(self.source_folder, "**", "sieve2*.h"),
                     os.path.join(self.source_folder, "**", "sieve2*.h".upper())):
            try:
                _hdr_cands.extend(_glob.glob(_pat, recursive=True))
            except Exception:
                pass
        # Preferred public dir first (sv_include) so flattening is stable.
        def _hdr_rank(_p):
            try:
                if "sv_include" in _p:
                    return 0
                return 1
            except Exception:
                return 1
        try:
            _hdr_cands = sorted(set(_hdr_cands), key=_hdr_rank)
        except Exception:
            pass
        _hdrs = []
        for _h in _hdr_cands:
            try:
                if os.path.isfile(_h):
                    copy(self, os.path.basename(_h),
                         src=os.path.dirname(_h), dst=_incdir,
                         keep_path=False)
                    _hdrs.append(_h)
            except Exception as _e:
                self.output.warning("HMBS manual-install header skip %s: %s" % (_h, _e))
        self.output.info("HMBS manual-install libs=%s headers=%s" % (_copied, _hdrs))
        # --- verify the consumer-visible file set, else fail loudly ---
        _ok = True
        if self.options.shared:
            try:
                _libs = _glob.glob(os.path.join(_libdir, "libsieve.so*"))
            except Exception:
                _libs = []
            if not _libs:
                self.output.error("HMBS manual-install MISS: no libsieve.so* in %s (work=%s)" % (_libdir, _work))
                _ok = False
        else:
            if not os.path.isfile(os.path.join(_libdir, "libsieve.a")):
                self.output.error("HMBS manual-install MISS: libsieve.a not in %s (src=%s work=%s)" % (_libdir, _lib_src, _work))
                _ok = False
        if not os.path.isfile(os.path.join(_incdir, "sieve2.h")):
            self.output.error("HMBS manual-install MISS: sieve2.h not in %s (found=%s)" % (_incdir, _hdrs))
            _ok = False
        if not _ok:
            try:
                self.output.error("HMBS manual-install work listing (top):")
                for _p in sorted(_glob.glob(os.path.join(_work, "*")))[:40]:
                    self.output.error("WORKLS: " + _p[:400])
                self.output.error("HMBS manual-install source header search:")
                for _p in sorted(_glob.glob(os.path.join(self.source_folder, "src", "*")))[:40]:
                    self.output.error("SRCLS: " + _p[:400])
            except Exception:
                pass
            raise ConanException("libsieve manual install file set incomplete (see HMBS manual-install MISS lines)")
        # Drop libtool leftovers if a future make install ever runs;
        # conan convention: no .la in packages.
        try:
            for _p in _glob.glob(os.path.join(_libdir, "*.la")):
                os.unlink(_p)
        except Exception:
            pass
        # Persist upstream evidence with the package so cache-hit rounds
        # (build() skipped) can still re-emit the real in-build numbers.
        try:
            _resdir = os.path.join(self.package_folder, "res")
            os.makedirs(_resdir, exist_ok=True)
            _src_json = None
            for _base in (_work, self.build_folder):
                try:
                    _cand = os.path.join(_base, "hmbs_upstream.json")
                    if _cand and os.path.isfile(_cand):
                        _src_json = _cand
                        break
                except Exception:
                    continue
            if _src_json:
                copy(self, "hmbs_upstream.json",
                     src=os.path.dirname(_src_json), dst=_resdir,
                     keep_path=False)
                self.output.info("HMBS upstream evidence carried: %s -> res/" % _src_json)
            else:
                self.output.warning("HMBS upstream evidence missing: no hmbs_upstream.json in work/build")
        except Exception as _e:
            self.output.warning("HMBS upstream evidence carry skipped: %s" % _e)

    def package_info(self):
        self.cpp_info.libs = ["sieve"]
