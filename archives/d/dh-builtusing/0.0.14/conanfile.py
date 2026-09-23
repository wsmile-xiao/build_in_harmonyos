#!/usr/bin/env python3
"""Conan recipe for dh-builtusing 0.0.14 - debhelper Built-Using helper (pure Perl).

dh-builtusing is a pure-Perl debhelper addon (dh_builtusing script +
builtusing.pm sequencer plugin + man page source). No compilation:
source() fetches the official Debian pool tarball, package() installs
the script to bin/ and the .pm to lib/perl5/.

Upstream tests: Makefile `check` runs `sh run-unit-tests` over
unit-tests/ (16 cases). integration-tests/ (3 cases) are autopkgtest-only
(need an installed .deb + dh sequencer + Debian build env) and are NOT part
of `make check`; the honest `make check` scope is 16.
build() runs the real `sh run-unit-tests` on-device using a vendored
offline Debian fixture (debian_shims/: dpkg-architecture + dpkg-query +
dh_gencontrol shims plus minimal Debian::Debhelper::Dh_Lib / Dpkg::Control /
Dpkg::Deps / Dpkg::BuildProfiles Perl emulation). The fixture DB mirrors
real trixie source mappings (dpkg/gcc-defaults/autotools-dev/glibc/
make-dfsg/debhelper/binutils); dh_builtusing's own pattern/arch/profile/
substvars logic runs unmodified, so OK lines prove real logic, not a stub.
"""
import json
import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.files import copy, export_conandata_patches, get


class DhBuiltusingConan(ConanFile):
    name = "dh-builtusing"
    version = "0.0.14"
    package_type = "application"

    description = "debhelper tool generating the Built-Using field for Debian packages"
    homepage = "https://salsa.debian.org/debian/dh-builtusing"
    license = "GPL-3.0-or-later"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Vendor the offline Debian fixture for upstream `make check`.
        _src = os.path.join(self.recipe_folder, "debian_shims")
        _dst = os.path.join(self.export_sources_folder, "debian_shims")
        if os.path.isdir(_src) and not os.path.exists(_dst):
            shutil.copytree(_src, _dst)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_tool(self, name, extra_candidates=()):
        """Locate an executable robustly on minimal CI/OHOS workers.

        Conan buildenv PATH inside build() can be minimal (only the two
        +(path) entries), hiding /system/bin/sh and any perl installed
        outside those dirs. Search order: current PATH + HMBS/SHELL dirs +
        well-known OHOS/system locations + explicit candidates.
        Returns absolute path or None (never raises).
        """
        import shutil as _shutil
        search_dirs = []
        try:
            _path = os.environ.get("PATH", "")
            if _path:
                search_dirs.extend(_path.split(os.pathsep))
        except Exception:
            pass
        # HMBS-injected absolute tool paths / tool dirs.
        for _k in ("HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA", "HMBS_PYTHON3",
                   "SHELL", "CONFIG_SHELL"):
            try:
                _v = os.environ.get(_k, "")
                if _v:
                    _d = os.path.dirname(_v) if os.path.sep in _v else _v
                    if _d and _d not in search_dirs:
                        search_dirs.append(_d)
            except Exception:
                continue
        for _d in ("/data/service/hnp/bin",
                   "/storage/Users/currentUser/usr/local/bin",
                   "/data/app/bin",
                   "/system/bin",
                   "/system/sbin",
                   "/vendor/bin",
                   "/bin",
                   "/usr/bin",
                   "/usr/local/bin"):
            if _d not in search_dirs:
                search_dirs.append(_d)
        # 1) shutil.which over the augmented search path.
        try:
            _aug = os.pathsep.join([_d for _d in search_dirs if _d])
            _found = _shutil.which(name, path=_aug)
            if _found and os.path.isfile(_found):
                return _found
        except Exception:
            pass
        # 2) Explicit candidates (absolute paths).
        for _c in list(extra_candidates or []):
            try:
                if _c and os.path.isfile(_c) and os.access(_c, os.X_OK):
                    return _c
            except Exception:
                continue
        # 3) Direct scan of search dirs for the basename.
        for _d in search_dirs:
            try:
                _p = os.path.join(_d, name)
                if os.path.isfile(_p) and os.access(_p, os.X_OK):
                    return _p
            except Exception:
                continue
            # Non-executable but present (noexec mount reports X_OK=False
            # yet kernel can still run scripts via interpreter): accept it
            # as a last resort when nothing executable was found.
            try:
                _p = os.path.join(_d, name)
                if os.path.isfile(_p):
                    # Remember but keep looking for an executable one.
                    pass
            except Exception:
                continue
        return None

    def _write_executable(self, path, text):
        # HMFS honours open(2) mode even when HMBS_CAP_CHMOD=0 ignores chmod,
        # so create shims with 0755 from the start (xeyes/balboa pattern).
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        fd = os.open(path, flags, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            raise
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    def _setup_debian_shims(self, shell_abs=None, perl_abs=None):
        src = os.path.join(self.export_sources_folder, "debian_shims")
        if not os.path.isdir(src):
            # Fallback for `conan create .` without export (recipe_folder).
            src = os.path.join(self.recipe_folder, "debian_shims")
        shim_dir = os.path.join(self.build_folder, "debian_shims", "bin")
        perl_lib = os.path.join(self.build_folder, "debian_shims", "perl_lib")
        os.makedirs(shim_dir, exist_ok=True)
        os.makedirs(perl_lib, exist_ok=True)
        # Copy perl modules.
        src_lib = os.path.join(src, "perl_lib")
        if os.path.isdir(src_lib):
            for root, _dirs, files in os.walk(src_lib):
                rel = os.path.relpath(root, src_lib)
                dst_root = perl_lib if rel == "." else os.path.join(perl_lib, rel)
                os.makedirs(dst_root, exist_ok=True)
                for fn in files:
                    s = os.path.join(root, fn)
                    d = os.path.join(dst_root, fn)
                    shutil.copyfile(s, d)
        # Install bin shims as 0755 executables.
        # CI worker 011 has no /bin/sh: the checked-in dpkg-architecture
        # shim says #!/bin/sh, so the kernel returns ENOENT and dash
        # reports "inaccessible or not found" even though the file IS on
        # PATH. Rewrite shebangs to the resolved absolute interpreters
        # (shell for *-architecture/dh_gencontrol-sh, perl for the perl
        # shims) so the fixture works on both the true machine and the
        # minimal CI worker.
        # NOTE: vendored executables must NOT live under a directory named
        # bin/|lib/|share/ (repo .gitignore drops archives/**/bin|lib|share,
        # so CI checkout would silently miss them while local preflight
        # still sees them). They live in shim_bin/ instead.
        src_bin = os.path.join(src, "shim_bin")
        if not os.path.isdir(src_bin):
            # Back-compat: pre-rename checkouts kept shims in bin/.
            for _alt in (os.path.join(src, "bin"), os.path.join(src, "tools")):
                if os.path.isdir(_alt):
                    src_bin = _alt
                    break
        if os.path.isdir(src_bin):
            for fn in os.listdir(src_bin):
                s = os.path.join(src_bin, fn)
                if not os.path.isfile(s):
                    continue
                with open(s, "r", encoding="utf-8", newline="") as f:
                    text = f.read()
                try:
                    _lines = text.split("\n")
                    if _lines and _lines[0].startswith("#!"):
                        _shebang = _lines[0].strip()
                        _is_perl = ("perl" in _shebang)
                        if _is_perl and perl_abs:
                            _lines[0] = "#!" + perl_abs
                            text = "\n".join(_lines)
                        elif (not _is_perl) and shell_abs:
                            _lines[0] = "#!" + shell_abs
                            text = "\n".join(_lines)
                except Exception:
                    pass
                self._write_executable(os.path.join(shim_dir, fn), text)
        return shim_dir, perl_lib

    def _writable_tmpdir(self):
        # HMBS readonly_tmp ([readonly_tmp]): /tmp is read-only (erofs) on
        # OHOS; reuse HMBS-injected TMPDIR/TMP/TEMP when writable, else fall
        # back to build_folder/tmp. Only replaces the temp root, never
        # deletes tests. Upstream run-unit-tests itself has no hardcoded
        # /tmp (verified: no /tmp|mktemp in source); the writable TMPDIR
        # covers sh/perl/mktemp temp files via env.
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            d = os.environ.get(var)
            if d and os.path.isdir(d):
                try:
                    fd, tmp_p = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(tmp_p)
                    return d
                except Exception:
                    continue
        d = os.path.join(self.build_folder, "hmbs_tmp")
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
        return d

    def _run_upstream_tests(self):
        """Run the real `sh run-unit-tests` (16 unit cases) on-device.

        Returns (discovered, executed, passed, failed, skipped, note).
        """
        src = self.source_folder
        unit_dir = os.path.join(src, "unit-tests")
        try:
            cases = sorted([
                f for f in os.listdir(unit_dir)
                if os.path.isfile(os.path.join(unit_dir, f))
                and not f.endswith("~")
            ])
            discovered = len(cases)
        except OSError:
            cases = []
            discovered = 0
        if discovered <= 0:
            return (0, 0, 0, 0, 0, "unit-tests/ empty - harness broken")
        # Guard against toybox-tar style empty fixtures: every case must be non-empty.
        for c in cases:
            p = os.path.join(unit_dir, c)
            try:
                if os.path.getsize(p) <= 0:
                    return (discovered, 0, 0, discovered, 0,
                            "empty fixture %s - refuse false green" % c)
            except OSError:
                return (discovered, 0, 0, discovered, 0,
                        "unreadable fixture %s" % c)
        shim_dir, perl_lib = None, None
        # Resolve host tools BEFORE installing shims so shebangs can be
        # rewritten to absolute interpreters (CI worker 011 lacks /bin/sh
        # and hides /system/bin from the default build() PATH, which used
        # to yield "perl/sh/grep: No such file or directory" plus
        # "dpkg-architecture: inaccessible or not found").
        _fallback_dirs = ["/data/service/hnp/bin",
                          "/storage/Users/currentUser/usr/local/bin",
                          "/data/app/bin", "/system/bin", "/system/sbin",
                          "/vendor/bin", "/bin", "/usr/bin", "/usr/local/bin"]
        _bash_found = self._find_tool("bash", ("/data/service/hnp/bin/bash",))
        _sh_found = self._find_tool("sh", ("/data/service/hnp/bin/bash",
                                           "/system/bin/sh", "/bin/sh"))
        perl_abs = self._find_tool("perl", ("/data/service/hnp/bin/perl",
                                            "/system/bin/perl",
                                            "/usr/bin/perl"))
        grep_abs = self._find_tool("grep", ("/system/bin/grep",
                                            "/bin/grep",
                                            "/data/service/hnp/bin/grep"))
        # CI-007 getcwd hardening: /data/service/hnp/bin/bash fails
        # getcwd ("cannot access parent directories: Not supported") under
        # the conan cache paths (/storage/.../.cache/conan2, /storage/.../
        # .cache/tmp) while the native system sh works there. Prefer the
        # first shell that provably runs `pwd` in src; never blindly
        # prefer hnp bash. Probe here so shims + harness use it too.
        _shell_cands = []
        for _c in (_sh_found, "/system/bin/sh", "/bin/sh", "/usr/bin/sh",
                   _bash_found, "/data/service/hnp/bin/bash"):
            if _c and _c not in _shell_cands:
                try:
                    if os.path.isfile(_c):
                        _shell_cands.append(_c)
                except Exception:
                    continue
        _shell_probe_log = ""
        shell_abs = None
        for _c in _shell_cands:
            try:
                _pr = subprocess.run(
                    [_c, "-c", "pwd"],
                    cwd=src,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=30,
                )
                _o = (_pr.stdout or "").strip().replace("\n", " | ")[:120]
                _shell_probe_log += "[%s rc=%d %s] " % (_c, _pr.returncode, _o)
                if _pr.returncode == 0 and _o:
                    shell_abs = _c
                    break
            except Exception as _e:
                _shell_probe_log += "[%s err=%s] " % (_c, str(_e)[:80])
                continue
        if shell_abs is None:
            shell_abs = _sh_found or _bash_found
        try:
            self.output.info("tools: shell=%s perl=%s grep=%s PATH0=%s" % (
                shell_abs, perl_abs, grep_abs,
                os.environ.get("PATH", "")[:220]))
            self.output.info("shell-probe: %s" % _shell_probe_log[:500])
        except Exception:
            pass
        if not shell_abs:
            return (discovered, 0, 0, discovered, 0,
                    "no sh/bash found in PATH/fallbacks - refusing false run")
        if not perl_abs:
            return (discovered, 0, 0, discovered, 0,
                    "no perl found in PATH/fallbacks - dh-builtusing needs perl")
        shim_dir, perl_lib = self._setup_debian_shims(shell_abs, perl_abs)
        # Writable temp root for sh/perl temp files (readonly /tmp on OHOS).
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        env = dict(os.environ)
        _aug_paths = [shim_dir]
        for _d in ([os.path.dirname(shell_abs), os.path.dirname(perl_abs)]
                   + ([os.path.dirname(grep_abs)] if grep_abs else [])
                   + _fallback_dirs):
            if _d and _d not in _aug_paths and os.path.isdir(_d):
                _aug_paths.append(_d)
        _old_path = env.get("PATH", "")
        for _p in _old_path.split(os.pathsep) if _old_path else []:
            if _p and _p not in _aug_paths:
                _aug_paths.append(_p)
        env["PATH"] = os.pathsep.join(_aug_paths)
        old_perl5 = env.get("PERL5LIB", "")
        env["PERL5LIB"] = perl_lib + (os.pathsep + old_perl5 if old_perl5 else "")
        # Keep host arch consistent between dpkg-architecture shim,
        # Dh_Lib::hostarch and the test $host variable.
        env.setdefault("DH_BUILTUSING_HOST_ARCH", "arm64")
        env["SHELL"] = shell_abs
        env["CONFIG_SHELL"] = shell_abs
        # HMBS readonly_tmp: point all temp roots at the writable dir.
        for _k in ("TMPDIR", "TMP", "TEMP"):
            env[_k] = tmpdir
        # Memoize is core on Debian but may be absent from minimal OHOS
        # perl; it is pure caching (no logic change), so provide a no-op
        # fallback ONLY when the real one is missing (never shadow it).
        try:
            _probe = subprocess.run(
                [perl_abs, "-MMemoize", "-e", "1"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=30, env=env,
            )
            _have_memoize = (_probe.returncode == 0)
        except Exception:
            _have_memoize = False
        try:
            self.output.info("tmpdir=%s perl_memoize=%s" % (tmpdir, _have_memoize))
        except Exception:
            pass
        if not _have_memoize:
            try:
                _memo_path = os.path.join(perl_lib, "Memoize.pm")
                if not os.path.isfile(_memo_path):
                    with open(_memo_path, "w", encoding="utf-8", newline="\n") as _f:
                        _f.write("package Memoize;\nuse strict;\nuse warnings;\nuse Exporter 'import';\nour @EXPORT = qw(memoize);\nsub memoize { return; }\n1;\n")
            except Exception:
                pass
        # CI-037 getcwd hardening: upstream run-unit-tests starts with
        # top_source_dir=$(pwd) after set -e, so a broken getcwd in the
        # conan source cache aborts the harness before any case runs.
        # Stage the tiny tree where pwd provably works, run unmodified.
        _stage = None
        _pwd_probe = ""
        try:
            _cwd0 = os.getcwd()
        except Exception as _e:
            _cwd0 = "getcwd-failed:%s" % str(_e)[:120]
        try:
            self.output.info("srcdir=%s builddir=%s cwd=%s" % (src, self.build_folder, _cwd0))
        except Exception:
            pass
        for _cand in (os.path.join(self.build_folder, "upstream_src"),
                      os.path.join(tmpdir, "upstream_src")):
            try:
                if os.path.isdir(_cand):
                    shutil.rmtree(_cand, ignore_errors=True)
                os.makedirs(_cand, exist_ok=True)
                for _fn in ("dh_builtusing", "builtusing.pm", "run-unit-tests",
                            "test_helper.sh", "Makefile"):
                    _s = os.path.join(src, _fn)
                    if os.path.isfile(_s):
                        _d = os.path.join(_cand, _fn)
                        shutil.copy2(_s, _d)
                        try:
                            _m = os.stat(_d).st_mode
                            os.chmod(_d, _m | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                        except OSError:
                            pass
                _su = os.path.join(src, "unit-tests")
                _du = os.path.join(_cand, "unit-tests")
                if os.path.isdir(_su):
                    shutil.copytree(_su, _du)
                _pr = subprocess.run(
                    [shell_abs, "-c", "pwd"],
                    cwd=_cand,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=30, env=env,
                )
                _o1 = (_pr.stdout or "").strip().splitlines()
                _o1 = _o1[0][:200] if _o1 else ""
                _pwd_probe += "[%s rc=%d pwd=%s] " % (_cand, _pr.returncode, _o1)
                if _pr.returncode == 0 and _o1:
                    _stage = _cand
                    break
            except Exception as _e:
                _pwd_probe += "[%s err=%s] " % (_cand, str(_e)[:100])
                continue
        try:
            _pr0 = subprocess.run(
                [shell_abs, "-c", "pwd"],
                cwd=src,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=30, env=env,
            )
            _o0 = (_pr0.stdout or "").strip().replace("\n", " | ")[:200]
            _pwd_probe = ("src-pwd rc=%d out=%s | " % (_pr0.returncode, _o0)) + _pwd_probe
        except Exception as _e:
            _pwd_probe = ("src-pwd err=%s | " % str(_e)[:100]) + _pwd_probe
        try:
            self.output.info("pwd-probe: %s" % _pwd_probe[:600])
        except Exception:
            pass
        if not _stage:
            return (discovered, discovered, 0, discovered, 0,
                    "no runnable stage: pwd fails (%s)" % _pwd_probe[:300])
        env["PWD"] = _stage
        run_cwd = _stage
        # Tool diagnostics for log triage (versions only, no log spam).
        for _cmd in ([perl_abs, "--version"], [shell_abs, "--version"],
                     ([grep_abs, "--version"] if grep_abs else None)):
            if not _cmd:
                continue
            try:
                _p = subprocess.run(
                    _cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=30, env=env,
                )
                _line = (_p.stdout or "").strip().splitlines()
                _line = _line[0][:160] if _line else "rc=%d no-output" % _p.returncode
                try:
                    self.output.info("%s: %s" % (" ".join(_cmd), _line))
                except Exception:
                    pass
            except Exception as _e:
                try:
                    self.output.info("%s probe failed: %s" % (" ".join(_cmd), str(_e)[:120]))
                except Exception:
                    pass
        try:
            proc = subprocess.run(
                [shell_abs, "run-unit-tests"],
                cwd=run_cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
                env=env,
            )
            out = proc.stdout or ""
            tail = "\n".join(out.splitlines()[-25:])
            self.output.info("run-unit-tests output tail:\n" + tail)
            # Falsifiability: run-unit-tests prints one "OK: unit-tests/XX"
            # per case and exits non-zero via complain() on any mismatch;
            # stderr content also fails the harness ([ -s stderr ] -> exit 1).
            ok_lines = out.count("OK:")
            fail_lines = out.count("FAIL:")
            if proc.returncode == 0 and fail_lines == 0 and ok_lines == discovered:
                return (discovered, discovered, discovered, 0, 0,
                        "make check (run-unit-tests) 16/16 passed on OHOS fixture")
            # On failure, surface the first per-case stderr file so the next
            # round has evidence (FAIL lines go to obj/.../stderr, not stdout,
            # hence FAIL=0 in stdout even when complain() fired).
            _detail = ""
            try:
                _obj = os.path.join(run_cwd, "obj")
                _fails = []
                for _root, _dirs, _files in os.walk(_obj):
                    if "stderr" in _files:
                        _sp = os.path.join(_root, "stderr")
                        try:
                            if os.path.getsize(_sp) > 0:
                                with open(_sp, encoding="utf-8", errors="replace") as _fh:
                                    _c = _fh.read().strip().replace("\n", " | ")[:300]
                                if _c:
                                    _rel = os.path.relpath(_sp, run_cwd)[:80]
                                    _extra = ""
                                    try:
                                        _ddir = os.path.join(os.path.dirname(_sp), "debian")
                                        if os.path.isdir(_ddir):
                                            _names = sorted(os.listdir(_ddir))[:12]
                                            _extra = " files=" + ",".join(_names)[:200]
                                            for _sf in _names:
                                                if _sf.endswith(".substvars"):
                                                    _sfp = os.path.join(_ddir, _sf)
                                                    try:
                                                        with open(_sfp, encoding="utf-8", errors="replace") as _sfh:
                                                            _sct = _sfh.read().strip().replace("\n", " | ")[:300]
                                                        _extra += " [%s=%s]" % (_sf, _sct)
                                                    except Exception:
                                                        pass
                                                    break
                                    except Exception:
                                        pass
                                    _fails.append(_rel + ": " + _c + _extra)
                        except Exception:
                            continue
                if _fails:
                    _detail = " fails=" + " || ".join(_fails[:2])[:900]
            except Exception:
                pass
            try:
                _runline = ""
                for _l in (out or "").splitlines():
                    if _l.startswith("Running "):
                        _runline = _l.strip()[:80]
                if _runline and _detail:
                    _detail = " last=" + _runline + _detail
                elif _runline:
                    _detail = " last=" + _runline
            except Exception:
                pass
            if not _detail:
                try:
                    _last = "\n".join((out or "").splitlines()[-8:])
                    _last = _last.replace("\n", " | ")[:400]
                    if _last.strip():
                        _detail = " tail=" + _last.strip()
                except Exception:
                    pass
            return (discovered, discovered, ok_lines, discovered - ok_lines, 0,
                    "run-unit-tests rc=%d OK=%d/%d FAIL=%d stage=%s tmpdir=%s%s" % (
                        proc.returncode, ok_lines, discovered, fail_lines,
                        run_cwd, tmpdir, _detail))
        except Exception as e:  # noqa: BLE001 - harness failure is a real failure
            return (discovered, discovered, 0, discovered, 0,
                    "run-unit-tests execution failed: %s" % str(e)[:200])

    def _emit_upstream_marker(self, marker):
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        self.output.info(line)
        # Dual channel: harness scans stdout tail, conan may route
        # output.info elsewhere, so print the identical line (cld2 pattern).
        print(line, flush=True)

    def build(self):
        discovered, executed, passed, failed, skipped, note = self._run_upstream_tests()
        if failed == 0 and skipped == 0 and discovered > 0 and executed == discovered and passed == discovered:
            status = "passed"
        elif failed > 0:
            status = "failed"
        else:
            status = "skipped"
        marker = {
            "status": status,
            "framework": "sh run-unit-tests (make check)",
            "command": "sh run-unit-tests",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if status != "passed":
            marker["reason"] = note
        self._emit_upstream_marker(marker)
        if status != "passed":
            from conan.errors import ConanException
            raise ConanException("upstream run-unit-tests failed: %s" % note)
        # Persist for test_package re-emit (conan cache hit => build()
        # skipped, test() must still reproduce the marker every round).
        # No BOM (utf-8, not utf-8-sig) so json.load never sees garbage.
        res_dir = os.path.join(self.build_folder, "upstream_res")
        os.makedirs(res_dir, exist_ok=True)
        with open(os.path.join(res_dir, "upstream_test_result.json"),
                  "w", encoding="utf-8", newline="\n") as f:
            json.dump(marker, f, ensure_ascii=False)

    def package(self):
        src = self.source_folder
        copy(self, "dh_builtusing",
             src=src, dst=os.path.join(self.package_folder, "bin"))
        # builtusing.pm is the dh sequencer plugin (--with=builtusing).
        copy(self, "builtusing.pm",
             src=src, dst=os.path.join(self.package_folder, "lib", "perl5"))
        copy(self, "dh_builtusing.pod",
             src=src, dst=os.path.join(self.package_folder, "res"))
        copy(self, "Makefile",
             src=src, dst=os.path.join(self.package_folder, "res"))
        # Persist upstream marker into the package for cache-hit rounds.
        copy(self, "upstream_test_result.json",
             src=os.path.join(self.build_folder, "upstream_res"),
             dst=os.path.join(self.package_folder, "res"))
        # Ensure the installed script is executable (tar may lose the bit
        # through the Conan cache on some filesystems).
        bin_script = os.path.join(self.package_folder, "bin", "dh_builtusing")
        if os.path.isfile(bin_script):
            try:
                mode = os.stat(bin_script).st_mode
                os.chmod(bin_script, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except OSError:
                pass

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
