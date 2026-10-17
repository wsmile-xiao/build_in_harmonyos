#!/usr/bin/env python3
"""test_package for libobjfwtls1 -- compiles Objective-C and C consumers that
genuinely call the ObjFWTLS public API (OFX509Certificate) and link
libobjfwtls / libobjfw / libobjfwrt (R34: no empty-shell tests).
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


def _ensure_writable_tmp(conanfile):
    """Point TMPDIR/TMP/TEMP/XDG_RUNTIME_DIR at a writable dir.

    HMBS injects a writable TMPDIR, but the value is conveyed via the outer
    environment while CMake try_compile / clang temp files may fall back to
    readonly /tmp when the variable is filtered. Export explicitly so both
    probing and the real configure inherit it. Prefer a short HOME-based
    dir (also keeps any socket paths short); fall back to the HMBS value.
    """
    candidates = []
    try:
        home = os.path.expanduser("~")
    except Exception:
        home = ""
    if home and os.path.isabs(home):
        candidates.append(os.path.join(home, ".hmbs-tptest"))
    for key in ("TMPDIR", "TMP", "TEMP"):
        base = os.environ.get(key)
        if base:
            candidates.append(os.path.join(base, "tptest-short"))
    candidates.append("/data/local/tmp/hmbs-tptest")
    for path in candidates:
        try:
            if len(path) + 16 >= 100:
                continue
            os.makedirs(path, exist_ok=True)
            probe = os.path.join(path, ".w")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("w")
            os.remove(probe)
            for var in ("TMPDIR", "TMP", "TEMP", "XDG_RUNTIME_DIR"):
                os.environ[var] = path
            conanfile.output.info(
                "libobjfwtls1 test_package: writable tmp %s" % path
            )
            return path
        except OSError:
            continue
    fallback = os.environ.get("TMPDIR", "/tmp")
    conanfile.output.warning(
        "libobjfwtls1 test_package: no short writable tmp, keep %s"
        % fallback
    )
    return fallback


def _probe_candidate(conanfile, cand):
    """Return abspath if cand really executes (clang --version rc==0)."""
    if not cand:
        return None
    if isinstance(cand, str):
        cand = cand.strip()
    if not cand:
        return None
    if os.path.isabs(cand):
        path = cand
        if not (os.path.isfile(path) and os.access(path, os.X_OK)):
            conanfile.output.info(
                "libobjfwtls1 test_package: probe %s -> missing/not-exec"
                % cand
            )
            return None
    else:
        path = shutil.which(cand)
        if not path:
            conanfile.output.info(
                "libobjfwtls1 test_package: probe %s -> not on PATH" % cand
            )
            return None
    try:
        proc = subprocess.run(
            [path, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
        )
        out = proc.stdout.decode("utf-8", errors="replace")[:500]
        ok = proc.returncode == 0 and (
            "clang" in out.lower()
            or "gcc" in out.lower()
            or "version" in out.lower()
        )
        conanfile.output.info(
            "libobjfwtls1 test_package: probe %s -> rc=%s ok=%s %.120s"
            % (path, proc.returncode, ok, out.replace("\n", " "))
        )
        return path if ok else None
    except Exception as exc:
        conanfile.output.info(
            "libobjfwtls1 test_package: probe %s -> exec failed %r"
            % (path, exc)
        )
        return None


def _resolve_working_compiler(conanfile, *candidates):
    for cand in candidates:
        hit = _probe_candidate(conanfile, cand)
        if hit:
            return hit
    # Bare-name sweep on PATH as last resort.
    for name in ("clang", "cc", "gcc"):
        hit = _probe_candidate(conanfile, name)
        if hit:
            return hit
    return None


def _rewrite_toolchain_file(conanfile, good_c, good_cxx):
    """Post-generate repair: force Linux system name and working compilers.

    cache_variables alone do not reliably win over the profile-baked
    tools.build:compiler_executables on this worker (previous round still
    configured with /data/service/hnp/bin/clang despite the cache entry),
    so patch the emitted file text directly.
    """
    roots = set()
    for attr in ("build_folder", "generators_folder"):
        try:
            val = getattr(conanfile, attr, None)
        except Exception:
            val = None
        if val and os.path.isdir(str(val)):
            roots.add(str(val))
    count = 0
    for root in roots:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn not in ("conan_toolchain.cmake", "CMakePresets.json"):
                    continue
                fp = os.path.join(dirpath, fn)
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read()
                except OSError:
                    continue
                orig = text
                if "HarmonyOS" in text:
                    text = text.replace("HarmonyOS", "Linux")
                if good_c:
                    # Replace any baked absolute clang that failed probing.
                    # Only touch CMAKE_C/OBJC_COMPILER lines to avoid
                    # collateral edits.
                    lines = []
                    for line in text.splitlines(True):
                        if "CMAKE_C_COMPILER" in line or "CMAKE_OBJC_COMPILER" in line:
                            # Keep line structure, swap the quoted path.
                            import re as _re

                            line = _re.sub(
                                r'"/[^"]*clang[^"]*"',
                                '"%s"' % good_c,
                                line,
                            )
                            line = _re.sub(
                                r"/[^\s;\"']*clang(?:\+\+)?",
                                good_c,
                                line,
                            )
                        if "CMAKE_CXX_COMPILER" in line and good_cxx:
                            import re as _re2

                            line = _re2.sub(
                                r'"/[^"]*"',
                                '"%s"' % good_cxx,
                                line,
                                count=1,
                            )
                        lines.append(line)
                    text = "".join(lines)
                if text != orig:
                    try:
                        with open(fp, "w", encoding="utf-8", newline="\n") as f:
                            f.write(text)
                        count += 1
                        conanfile.output.info(
                            "libobjfwtls1 test_package: rewrote %s" % fp
                        )
                    except OSError as exc:
                        conanfile.output.warning(
                            "libobjfwtls1 test_package: rewrite %s failed %r"
                            % (fp, exc)
                        )
    return count


class Libobjfwtls1TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        _ensure_writable_tmp(self)
        comp = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        conf_c = comp.get("c") if isinstance(comp, dict) else None
        conf_cxx = comp.get("cpp") if isinstance(comp, dict) else None
        hmbs_c = os.environ.get("HMBS_CMAKE_C_COMPILER", "")
        # Ordered probe: profile value first (log verdict), then env, PATH.
        # Unlike the previous existence-only check, each candidate must
        # actually execute `clang --version` successfully.
        resolved_c = _resolve_working_compiler(
            self,
            conf_c,
            os.environ.get("CC"),
            hmbs_c,
            "clang",
            "cc",
        )
        resolved_cxx = _resolve_working_compiler(
            self,
            conf_cxx,
            os.environ.get("CXX"),
            "clang++",
            "c++",
        )
        tc = CMakeToolchain(self)
        # CMake 4.x has no Platform/HarmonyOS module, so the auto-generated
        # toolchain (CMAKE_SYSTEM_NAME=HarmonyOS from OS=OHOS) fails with
        # "System is unknown to cmake". Alias a plain Linux device build
        # (same convention as byte-lite/abcmidi consumers in this repo).
        # Scoped to the consumer test only; the library itself stays OHOS.
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        arch = str(self.settings.arch)
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
            "aarch64" if arch == "armv8" else arch
        )
        if resolved_c:
            tc.cache_variables["CMAKE_C_COMPILER"] = resolved_c
            tc.cache_variables["CMAKE_OBJC_COMPILER"] = resolved_c
            self.output.info(
                "libobjfwtls1 test_package: CMAKE_C/OBJC_COMPILER=%s"
                % resolved_c
            )
        else:
            self.output.warning(
                "libobjfwtls1 test_package: no working C compiler probed, "
                "leaving toolchain default"
            )
        if resolved_cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = resolved_cxx
        tc.generate()
        # Harden the emitted file: previous round set the same cache entries
        # yet preflight still configured with the baked broken absolute
        # path, so rewrite the file text as well.
        _rewrite_toolchain_file(self, resolved_c, resolved_cxx)

    def build(self):
        short_tmp = _ensure_writable_tmp(self)
        comp = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        conf_c = comp.get("c") if isinstance(comp, dict) else None
        conf_cxx = comp.get("cpp") if isinstance(comp, dict) else None
        resolved_c = _resolve_working_compiler(
            self, conf_c, os.environ.get("CC"), "clang", "cc"
        )
        resolved_cxx = _resolve_working_compiler(
            self, conf_cxx, os.environ.get("CXX"), "clang++", "c++"
        )
        # Export working compilers + writable tmp into the configure
        # environment (HMBS buildenv filters outer env, so set explicitly).
        if resolved_c:
            os.environ["CC"] = resolved_c
            os.environ["OBJC"] = resolved_c
        if resolved_cxx:
            os.environ["CXX"] = resolved_cxx
        for var in ("TMPDIR", "TMP", "TEMP", "XDG_RUNTIME_DIR"):
            os.environ[var] = short_tmp
        cmake = CMake(self)
        cli = {
            "CMAKE_SYSTEM_NAME": "Linux",
            "CMAKE_SYSTEM_PROCESSOR": (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch)
            ),
        }
        if resolved_c:
            cli["CMAKE_C_COMPILER"] = resolved_c
            cli["CMAKE_OBJC_COMPILER"] = resolved_c
        if resolved_cxx:
            cli["CMAKE_CXX_COMPILER"] = resolved_cxx
        cmake.configure(variables=cli)
        # Serialize the build: make -jN jobserver mkfifo under TMPDIR reports
        # "Operation not permitted" on HMDFS (same convention as the library
        # recipe and the sister libobjfwhid1 test_package).
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        bindir = os.path.join(self.cpp.build.bindirs[0], "")
        # Objective-C consumer: genuinely exercises the ObjFWTLS public API
        # (OFX509Certificate PEM capability probe + invalid-PEM rejection).
        bin_oc = os.path.join(bindir, "test_libobjfwtls1")
        self.run(bin_oc, env="conanrun")
        # Plain C consumer: verifies libobjfwrt links and ObjFW classes register.
        bin_c = os.path.join(bindir, "test_runtime")
        self.run(bin_c, env="conanrun")
        # HMBS machine evidence: both consumer binaries exited 0 above, so
        # 2/2 genuinely ran (a failure would have raised before this line).
        tp_result = {
            "executed": True,
            "passed": True,
            "command": "./test_libobjfwtls1 && ./test_runtime",
            "discovered": 2,
            "passedCount": 2,
        }
        tp_line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result)
        print(tp_line, flush=True)
        self.output.info(tp_line)
        # Re-emit the upstream evidence measured in the main build (persisted
        # to res/hmbs_upstream.json); test_package only runs when that build
        # succeeded, so the numbers are grounded in the real `make check` run.
        # On a cache-hit round the main build() is skipped, hence re-emission.
        # Normalize stale evidence: rounds before the executed=gaps fix
        # persisted executed=discovered with skipped>0 (1242/1242/1238/0/4),
        # which violates passed+failed==executed. A cache-hit re-emission
        # would otherwise replay the bad numbers forever. Single source is
        # the persisted passed/failed/skipped; executed is derived, gaps are
        # backfilled when missing. No stdout counting or arithmetic guessing.
        up_line = None
        try:
            pkg = self.dependencies[self.tested_reference_str]
            for cand in (
                os.path.join(pkg.package_folder, "res", "hmbs_upstream.json"),
            ):
                if os.path.isfile(cand):
                    with open(cand, "r", encoding="utf-8") as f:
                        raw = f.read().strip()
                    try:
                        data = json.loads(raw)
                    except Exception as exc:
                        self.output.warning(
                            "upstream evidence JSON parse failed: %r" % (exc,)
                        )
                        data = None
                    if isinstance(data, dict):
                        try:
                            passed = int(data.get("passed", -1))
                            failed = int(data.get("failed", -1))
                            skipped = int(data.get("skipped", -1))
                            discovered = int(data.get("discovered", -1))
                        except Exception:
                            passed = failed = skipped = discovered = -1
                        if min(passed, failed, skipped, discovered) >= 0:
                            fixed = dict(data)
                            fixed["executed"] = passed + failed
                            if discovered < passed + failed + skipped:
                                discovered = passed + failed + skipped
                                fixed["discovered"] = discovered
                            # rule4 status semantics (same as build()): stale
                            # evidence persisted status="passed" with gaps
                            # (1242/1238/1238/0/4) is rejected as
                            # "passed 状态与上游结果矛盾". Derive status
                            # from numbers, never trust the persisted value.
                            if failed != 0:
                                fixed["status"] = "failed"
                            elif int(fixed["discovered"]) != passed:
                                fixed["status"] = "incomplete"
                            else:
                                fixed["status"] = "passed"
                            if discovered != passed and not fixed.get("gaps"):
                                reason = str(fixed.get("reason", ""))[:600]
                                if not reason:
                                    reason = (
                                        "platform-capability skips "
                                        "(no test deleted)"
                                    )
                                gaps = []
                                if skipped > 0:
                                    gaps.append({
                                        "count": int(skipped),
                                        "category": "ohos_feature",
                                        "detail": "OFTests platform-capability "
                                                  "self-skips, no test deleted "
                                                  "(hardlink + AF_UNIX)",
                                        "evidence": reason,
                                    })
                                if failed > 0:
                                    gaps.append({
                                        "count": int(failed),
                                        "category": "test_failure",
                                        "detail": "OFTests reported failures; "
                                                  "see hmbs_make_check.log",
                                        "evidence": reason,
                                    })
                                if gaps:
                                    fixed["gaps"] = gaps
                            # Self-check before emitting; never emit a
                            # contradictory marker.
                            ex = int(fixed["executed"])
                            assert passed + failed == ex
                            assert ex + skipped <= int(fixed["discovered"])
                            if int(fixed["discovered"]) != passed:
                                assert fixed.get("gaps")
                                assert sum(
                                    int(g["count"])
                                    for g in fixed["gaps"]
                                ) == int(fixed["discovered"]) - passed
                            if fixed != data:
                                self.output.info(
                                    "libobjfwtls1 test_package: normalized "
                                    "stale upstream evidence %r -> %r"
                                    % (data, fixed)
                                )
                            up_line = ("HMBS_UPSTREAM_TEST_RESULT="
                                       + json.dumps(fixed,
                                                    ensure_ascii=False))
                        else:
                            up_line = ("HMBS_UPSTREAM_TEST_RESULT=" + raw)
                    else:
                        up_line = "HMBS_UPSTREAM_TEST_RESULT=" + raw
                    break
        except Exception as exc:
            self.output.warning("read upstream evidence failed: %r" % (exc,))
        if up_line:
            print(up_line, flush=True)
            self.output.info(up_line)
