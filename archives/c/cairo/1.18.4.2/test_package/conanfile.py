#!/usr/bin/env python3
"""Conan test_package for cairo 1.18.4.2.

Consumer-view checks: compile against the installed cairo headers, link the
installed libcairo, and run 8 headless assertions (version, image surface,
context, paint, PNG round-trip with non-empty output, PDF/SVG backends,
operator-OVER ARGB32/RGB24 parity probe).
Emits HMBS_TEST_PACKAGE_RESULT and re-emits the persisted upstream marker.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class CairoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        incs = []
        for _ref, dep in self.dependencies.items():
            incs += ["-I" + p for p in dep.cpp_info.includedirs]
        inc = " ".join(incs)
        cairo_dep = self.dependencies["cairo"]
        libdirs = " ".join("-L" + d for d in cairo_dep.cpp_info.libdirs)
        libs = " ".join("-l" + lib for lib in cairo_dep.cpp_info.libs)
        sys_libs = " ".join("-l" + lib for lib in cairo_dep.cpp_info.system_libs)
        conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = conf.get("c") or os.environ.get("CC", "clang")
        # Link installed libcairo directly; dep libdirs carry transitive
        # pixman/png/freetype/fontconfig via pkg-config .pc Requires.
        # Embed rpath so the OHOS loader finds the package lib without
        # relying on LD_LIBRARY_PATH (ignored by the OHOS loader).
        rpath = " ".join(
            "-Wl,-rpath,%s" % d for d in cairo_dep.cpp_info.libdirs)
        self.run('%s test.c -o test_probe %s %s %s %s %s -ldl' % (
            cc, inc, libdirs, libs, sys_libs, rpath))

    def test(self):
        if not can_run(self):
            raise ConanException("cairo test_probe is not runnable on this configuration")
        # Conan 2.30: self.cpp.build.bindir raises when bindirs is empty.
        # Probe bindirs safely, then fall back to build_folder where
        # build() wrote ./test_probe (direct cc layout, no layout()).
        probe = None
        try:
            bindirs = self.cpp.build.bindirs
        except ConanException:
            bindirs = []
        if bindirs:
            cand = os.path.join(bindirs[0], "test_probe")
            if os.path.isfile(cand):
                probe = cand
        if probe is None:
            probe = os.path.join(self.build_folder, "test_probe")
        if not os.path.isfile(probe):
            raise ConanException("test_probe binary missing: %s" % probe)
        executable = self._stage_signed(probe)
        # HMBS readonly_tmp: guarantee the probe sees a writable TMPDIR
        # (test.c prefers TMPDIR; /tmp is read-only on OHOS真机).
        run_env = dict(os.environ)
        _tmp = run_env.get("TMPDIR") or run_env.get("TMP") or run_env.get("TEMP")
        try:
            if _tmp and os.path.isdir(_tmp):
                fd, _p = tempfile.mkstemp(dir=_tmp)
                os.close(fd)
                os.unlink(_p)
            else:
                _tmp = os.path.dirname(executable)
                run_env["TMPDIR"] = _tmp
                run_env["TMP"] = _tmp
                run_env["TEMP"] = _tmp
        except Exception:
            _tmp = os.path.dirname(executable)
            run_env["TMPDIR"] = _tmp
            run_env["TMP"] = _tmp
            run_env["TEMP"] = _tmp
        # HMBS stale_runtime_library: raw subprocess.run bypasses Conan
        # runenv, so the OHOS loader resolved libcairo.so.2 outside the
        # package (preflight: symbol not found on every cairo_* symbol,
        # rc=127). Collect every dependency libdir into LD_LIBRARY_PATH
        # and, because the OHOS loader ignores LD_LIBRARY_PATH, also
        # LD_PRELOAD the exact package libcairo.so.2 for this test only.
        import glob as _glob
        _libdirs = []
        for _dep in self.dependencies.values():
            try:
                _dirs = _dep.cpp_info.libdirs
            except Exception:
                continue
            for _d in _dirs or []:
                if _d and os.path.isdir(_d) and _d not in _libdirs:
                    _libdirs.append(_d)
        if _libdirs:
            _old_ld = run_env.get("LD_LIBRARY_PATH", "")
            run_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                _libdirs + ([_old_ld] if _old_ld else []))
        try:
            _cairo_pkg = self.dependencies["cairo"].package_folder
        except Exception:
            _cairo_pkg = None
        if _cairo_pkg:
            _cands = []
            _cands += sorted(_glob.glob(
                os.path.join(_cairo_pkg, "lib", "libcairo.so*")))
            _cairo_so = None
            for _c in _cands:
                if os.path.isfile(_c) and _c.endswith(".so.2"):
                    _cairo_so = _c
                    break
            if _cairo_so is None:
                for _c in _cands:
                    if os.path.isfile(_c):
                        _cairo_so = _c
                        break
            if _cairo_so:
                run_env["LD_PRELOAD"] = _cairo_so
                self.output.info("LD_PRELOAD=%s" % _cairo_so)
            else:
                self.output.warning(
                    "cairo shared lib not found under %s" % _cairo_pkg)
        # HMBS readonly_tmp: exec directly with no shell. /bin/sh on OHOS
        # creates its temp file under hardcoded /tmp (read-only), so the
        # previous [bash, -c] wrapper was SIGKILLed before any test ran.
        proc = subprocess.run(
            [executable],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=300, cwd=os.path.dirname(executable),
            env=run_env)
        output = proc.stdout or ""
        self.output.info("test_probe output:\n%s" % output[-3000:])
        total = 0
        passed = 0
        m = re.search(r"CAIRO_TEST total=(\d+) passed=(\d+)", output)
        if m:
            total = int(m.group(1))
            passed = int(m.group(2))
        else:
            # Fallback: count CHECK lines so a format drift cannot fake a pass.
            total = len(re.findall(r"^CHECK \d+ (PASS|FAIL)", output, flags=re.M))
            passed = len(re.findall(r"^CHECK \d+ PASS", output, flags=re.M))
        ok = proc.returncode == 0 and total == 8 and passed == 8
        marker = {
            "executed": True,
            "passed": bool(ok),
            "command": "./test_probe",
            "discovered": total,
            "passedCount": passed,
        }
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)
        self._reemit_upstream()
        self._print_diag()
        self._emit_parity(output)
        if not ok:
            raise ConanException("cairo test_probe failed: total=%d passed=%d rc=%d"
                                 % (total, passed, proc.returncode))

    def _writable_stage_dir(self):
        # HMBS readonly_tmp: never hardcode /tmp or a fixed cache path.
        # Probe task-private TMPDIR/TMP/TEMP/HMBS_TMPDIR for writability,
        # else fall back to the writable build folder.
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            d = os.environ.get(var)
            if d and os.path.isdir(d):
                try:
                    fd, p = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(p)
                    return tempfile.mkdtemp(prefix="cairo-test-", dir=d)
                except Exception:
                    continue
        return tempfile.mkdtemp(prefix="cairo-test-", dir=self.build_folder)

    def _stage_signed(self, probe):
        # OHOS requires a valid .codesign to exec; stage via a writable
        # task-private dir and self-sign so the consumer check really runs.
        if str(self.settings.os) != "OHOS":
            return probe
        staged_dir = self._writable_stage_dir()
        staged = os.path.join(staged_dir, "test_probe")
        shutil.copy2(probe, staged)
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        tmp_signed = staged + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", staged, "-outFile", tmp_signed, "-selfSign", "1"],
            check=True, timeout=60)
        sections = subprocess.run(
            [readelf, "-SW", tmp_signed],
            check=True, capture_output=True, text=True, timeout=30).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("signed test_probe has invalid .codesign")
        mode = os.stat(staged).st_mode
        os.chmod(tmp_signed, (mode & 0o777) | 0o055)
        os.replace(tmp_signed, staged)
        return staged

    def _reemit_upstream(self):
        # Re-emit the build-time upstream evidence every run so cache hits
        # still carry both HMBS markers in the log.
        for dep in self.dependencies.values():
            cand = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
            if os.path.isfile(cand):
                try:
                    with open(cand, encoding="utf-8") as f:
                        data = json.load(f)
                    line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data, ensure_ascii=False)
                    print(line, flush=True)
                    self.output.info(line)
                    return
                except (OSError, ValueError):
                    continue

    def _print_diag(self):
        # Re-print build-step failure classification AFTER the markers.
        # Plain-text lines only; marker formats are untouched.
        for dep in self.dependencies.values():
            cand = os.path.join(dep.package_folder, "res", "hmbs_diag.json")
            if os.path.isfile(cand):
                try:
                    with open(cand, encoding="utf-8") as f:
                        data = json.load(f)
                except (OSError, ValueError):
                    continue
                try:
                    _fm = data.get("failing_meson") or []
                    _fn = data.get("failing_names") or []
                    _fc = data.get("failing_count", len(_fn))
                    self.output.info(
                        "cairo diag upstream: sub PASS=%s FAIL=%s XFAIL=%s ERROR=%s; failing meson=%s"
                        % (data.get("sub_pass"), data.get("sub_fail"),
                           data.get("sub_xfail"), data.get("sub_error"),
                           ", ".join(_fm[:8]) or "(none)"))
                    self.output.info(
                        "cairo diag fonts: dejavu=%s vendored=%s dirs=%s counts=%s sys_sample=%s"
                        % (data.get("dejavu"), data.get("vendored", 0),
                           ", ".join(data.get("font_dirs") or []) or "(none)",
                           ", ".join("%s=%s" % (_k, _v)
                                     for _k, _v in (data.get("font_counts") or {}).items()) or "(none)",
                           ", ".join(data.get("sys_sample") or []) or "(none)"))
                    if _fn:
                        self.output.info(
                            "cairo diag failing sub-cases (%s, first 20): %s"
                            % (_fc, ", ".join(_fn[:20])))
                    else:
                        self.output.info("cairo diag failing sub-cases: (none parsed)")
                    if data.get("fail_diff_top") is not None:
                        self.output.info(
                            "cairo diag diff-magnitudes: n=%s total_px=%s max=%s top10=%s"
                            % (data.get("fail_diff_n"), data.get("fail_diff_total_px"),
                               data.get("fail_diff_max"),
                               ", ".join("%s/%s" % (a, b) for a, b in (data.get("fail_diff_top") or [])[:10]) or "(none)"))
                    else:
                        self.output.info("cairo diag diff-magnitudes: (unavailable - rebuild)")
                    if data.get("pass_sample") is not None:
                        self.output.info(
                            "cairo diag pass-sample: %s"
                            % ("; ".join(data.get("pass_sample") or []) or "(none)"))
                    if data.get("fc_match"):
                        self.output.info(
                            "cairo diag fc-match: %s"
                            % "; ".join("%s->%s" % (_k, _v) for _k, _v in sorted((data.get("fc_match") or {}).items())))
                    if data.get("fail_fam_op") is not None:
                        self.output.info(
                            "cairo diag fail-family: operator-ish=%s text-ish=%s (full names persisted: %d)"
                            % (data.get("fail_fam_op"), data.get("fail_fam_tx"),
                               len(data.get("failing_names") or [])))
                    if data.get("fail_fontfree") is not None:
                        self.output.info(
                            "cairo diag fail-fontfree floor: %s"
                            % data.get("fail_fontfree"))
                    _fbf = data.get("fail_by_format")
                    if _fbf is not None:
                        self.output.info(
                            "cairo diag fail-by-format: %s; parsed=%s unparsed=%s; top-tokens=%s"
                            % (", ".join("%s=%s" % (_k, _v) for _k, _v in sorted(_fbf.items())) or "(none)",
                               data.get("fail_parsed"), data.get("fail_unparsed"),
                               ", ".join("%s=%s" % (_k, _v) for _k, _v in (data.get("fail_top_tokens") or [])[:12]) or "(none)"))
                        if data.get("rgb24_only") is not None:
                            self.output.info(
                                "cairo diag rgb24-only (padding suspects, %d): %s"
                                % (len(data.get("rgb24_only") or []),
                                   ", ".join((data.get("rgb24_only") or [])[:20]) or "(none)"))
                    else:
                        self.output.info("cairo diag fail-by-format: (unavailable - rebuild)")
                    if data.get("refs_total", -1) != -1:
                        self.output.info(
                            "cairo diag refs: total=%s xfail=%s failing-missing-ref=%s%s"
                            % (data.get("refs_total"), data.get("xfail_total"),
                               data.get("fail_missing_ref_total"),
                               (" [" + ", ".join(data.get("fail_missing_ref") or []) + "]") if data.get("fail_missing_ref") else ""))
                        self.output.info(
                            "cairo diag out-sample: %s"
                            % ("; ".join(data.get("out_sample") or []) or "(none)"))
                    else:
                        self.output.info("cairo diag refs: (unavailable - rebuild)")
                except Exception as _e:
                    self.output.warning("cairo diag print skipped: %s" % _e)
                return

    def _emit_parity(self, output):
        # Re-emit the OVER-parity probe pixels as one short tail-visible
        # diag line: the full test_probe stdout is truncated from the
        # preflight tail, so without this the pixels never reach the
        # next diagnosis round. Guarded: never fails the gate.
        try:
            m = re.search(r"INFO in_parity ([^\r\n]+)", output or "")
            if m:
                line = "cairo diag in-parity: " + m.group(1).strip()[:200]
            else:
                line = "cairo diag in-parity: (probe line absent)"
            print(line, flush=True)
            self.output.info(line)
        except Exception as _e:
            self.output.warning("in-parity emit skipped: %s" % _e)
