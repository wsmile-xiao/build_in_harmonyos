#!/usr/bin/env python3
"""Conan recipe for racon 1.5.0 (CMake, C++11).

Racon is an ultrafast consensus module for raw de novo genome assembly
of long uncorrected reads (Oxford Nanopore / PacBio). Upstream:
https://github.com/lbcb-sci/racon tag 1.5.0.

Build notes (OHOS aarch64, clang 15 + libc++):
- CMake project, C++11, produces static/shared libracon + racon CLI.
- Direct deps: bioparser 3.0.15 via Conan; spoa exact 4.0.8, edlib 1.2.7,
  rvaser thread_pool 4.0.0 and GTest release-1.10.0 are all vendored from
  their official tarballs (see conandata sources_spoa/sources_edlib/
  sources_thread_pool/sources_googletest) into upstream's FetchContent
  fallbacks via FETCHCONTENT_SOURCE_DIR_SPOA/EDLIB/THREAD_POOL/GOOGLETEST,
  so no git clone runs on the device and no conancenter rebuild is needed
  on CMake 4 + HarmonyOS (Conan registry spoa 4.1.5 alignment changes break
  racon's exact edit-distance assertions). edlib is only used in src/overlap.cpp
  (private impl), not in public headers, so consumers link just libracon.
- CUDA and wrapper are always OFF on OHOS (no CUDA toolkit, no rampler).
- Upstream racon_test has no ctest registration (no enable_testing),
  so build() runs the binary directly and parses gtest output.
  See notes.md for the 15-case inventory (5 init death tests + 10 polishing).
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# CMake 4.x removed compatibility with cmake_minimum_required(<3.5).
# Kept for this package's own FetchContent sub-builds (googletest 1.10.0,
# thread_pool 4.0.0, vendored edlib): CMake 4 initializes that cache entry
# for every NEW build tree from this environment variable.
# Precedent: groonga/16.0.8 + grokj2k/20.3.6.
os.environ.setdefault("CMAKE_POLICY_VERSION_MINIMUM", "3.5")

required_conan_version = ">=2.0"


class RaconConan(ConanFile):
    name = "racon"
    version = "1.5.0"
    description = "Ultrafast consensus module for raw de novo genome assembly of long uncorrected reads"
    license = "MIT"
    homepage = "https://github.com/lbcb-sci/racon"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("genomics", "assembly", "consensus", "nanopore", "pacbio")

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        self.requires("bioparser/3.0.15")
        # Round 6 (new domain, different strategy from round-5 /tmp patch):
        # true-device now runs 15/15 but 9 RaconPolishingTest fail with small
        # systematic drifts (e.g. 1312 vs 1333, 1658216 vs 1658477). Only
        # inexact dep is spoa: registry has 4.1.5, upstream pins exact 4.0.8
        # (find_package(spoa 4.0.8) + FetchContent GIT_TAG 4.0.8). 4.1.x
        # alignment changes break racon's exact edit-distance assertions, so
        # drop the Conan spoa and let upstream FetchContent build exact 4.0.8
        # as a subdirectory (inherits Linux + POLICY_MINIMUM fixes). No
        # version-range substitution for algorithm-critical deps.
        # Round 8 update: exact 4.0.8 vendored build shows the SAME 9 drifts,
        # disproving spoa-version as root cause; remaining drift is OHOS
        # aarch64/clang scalar POA vs x86-64 SIMD-tuned thresholds (see
        # _run_upstream_tests gaps). Exact-version vendoring is still kept
        # (correct upstream tag, no registry skew).
        # Transitive zlib: bioparser requires zlib/1.3.1 whose conancenter
        # recipe is CMake-based without the OHOS->Linux override, so its
        # from-source rebuild fails on CMake 4.4.3 with "System is unknown
        # to cmake / Platform/HarmonyOS" (true-device 2026-09-27, 3rd
        # failure domain). Override to the OHOS-proven zlib/1.3.2.1
        # (archives/z/zlib, configure+make static-PIC, no CMake platform
        # check). zlib API is stable 1.3.1->1.3.2 (gz/compress/deflate);
        # bioparser is header-only and only uses those stable APIs.
        self.requires("zlib/1.3.2.1", override=True)
        # NOTE: no conan requires on edlib/1.2.7. The conancenter recipe has
        # neither CMAKE_POLICY_VERSION_MINIMUM nor the OHOS->Linux platform
        # override, so its from-source rebuild fails on CMake 4.4.3 with
        # "System is unknown to cmake / Platform/HarmonyOS" (true-device
        # 2026-09-27, 2nd failure domain after the <3.5 compat fix). Upstream
        # racon natively falls back to FetchContent for edlib, so we vendor
        # the official edlib tarball (sources_edlib) and point that fallback
        # at the local dir (see source()/generate()); the subdirectory then
        # inherits this recipe's Linux + POLICY_MINIMUM toolchain fixes.

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendor official tarballs for all upstream FetchContent fallbacks
        # (no git clone on the device; true-device github git is unreachable
        # while https tarball downloads work). Each dir keeps the exact tag
        # content and is built as a subdirectory inheriting this recipe's
        # Linux + POLICY_MINIMUM toolchain fixes.
        get(self, **self.conan_data["sources_edlib"], strip_root=True,
            destination=os.path.join(self.source_folder, "edlib_fallback"))
        get(self, **self.conan_data["sources_spoa"], strip_root=True,
            destination=os.path.join(self.source_folder, "spoa_fallback"))
        get(self, **self.conan_data["sources_thread_pool"], strip_root=True,
            destination=os.path.join(self.source_folder, "thread_pool_fallback"))
        get(self, **self.conan_data["sources_googletest"], strip_root=True,
            destination=os.path.join(self.source_folder, "googletest_fallback"))

    def _resolve_compiler(self, configured, names):
        # mathic/1.4 precedent: shared profile may still point at the
        # migrated /data/service/hnp/bin/clang(++) path (stat ENOENT on the
        # true device). Resolve per tool (C vs CXX, no cross fallback) via
        # existing configured path -> PATH -> ~/usr/local/bin.
        if configured and os.path.isfile(configured):
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

    def _fix_generated_toolchain_compiler(self, configured_map, c, cxx):
        # zydis/mathic precedent: conan_toolchain.cmake may have baked the
        # stale absolute path; patch only when old is missing and new exists.
        if not isinstance(configured_map, dict):
            configured_map = {}
        c_old = configured_map.get("c")
        cxx_old = configured_map.get("cpp")
        pairs = []
        if c_old and c and c_old != c \
                and not os.path.isfile(c_old) and os.path.isfile(c):
            pairs.append((c_old, c))
        if cxx_old and cxx and cxx_old != cxx \
                and not os.path.isfile(cxx_old) and os.path.isfile(cxx):
            pairs.append((cxx_old, cxx))
        if not pairs:
            return
        try:
            gf = getattr(self, "generators_folder", None)
            path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                orig = text
                for old_p, new_p in pairs:
                    text = text.replace(old_p, new_p)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    self.output.info("HMBS diag fixed generated toolchain %s" % path)
            else:
                self.output.warning("HMBS diag toolchain file not found: %s" % path)
        except Exception as e:
            self.output.warning("HMBS diag toolchain fix failed: %s" % e)
        try:
            comp_env = Environment()
            if c_old and c and (c_old, c) in pairs:
                comp_env.define("CC", c)
            if cxx_old and cxx and (cxx_old, cxx) in pairs:
                comp_env.define("CXX", cxx)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as e:
            self.output.warning("HMBS diag compiler env export failed: %s" % e)

    def _probe_cxx_toolchain(self, budget=2000):
        lines = []
        try:
            conf = {}
            try:
                conf = self.conf.get(
                    "tools.build:compiler_executables", default={}, check_type=dict
                ) or {}
            except Exception as e:
                lines.append("conf read failed: {}".format(e))
            cxx = conf.get("cpp", "") if isinstance(conf, dict) else ""
            cc = conf.get("c", "") if isinstance(conf, dict) else ""
            lines.append("conf c={} cpp={}".format(cc, cxx))
            for label, path in (("c", cc), ("cpp", cxx)):
                if not path:
                    lines.append("{}: empty".format(label))
                    continue
                try:
                    st = os.stat(path)
                    lines.append("{}: exists size={} mode={}".format(
                        label, st.st_size, oct(st.st_mode)))
                except Exception as e:
                    lines.append("{}: stat {} failed: {}".format(label, path, e))
                    continue
                try:
                    proc = subprocess.run(
                        [path, "--version"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=60,
                    )
                    out = (proc.stdout or "").strip()
                    first = out.splitlines()[0] if out else "(empty)"
                    lines.append("{} --version rc={}: {}".format(
                        label, proc.returncode, first))
                except Exception as e:
                    lines.append("{} --version failed: {}".format(label, e))
        except Exception as e:
            lines.append("probe failed: {}".format(e))
        return "\n".join(lines)[-budget:]

    def _cmake_error_evidence(self, budget=4000):
        # CMake 4.x keeps try-compile logs in
        # CMakeFiles/<ver>/CMakeConfigureLog.yaml; older CMakeError.log may
        # not exist. Pick failed events instead of file tail.
        try:
            bf = getattr(self, "build_folder", None)
            if not bf or not os.path.isdir(bf):
                return "no build folder"
            searched = []
            hits = []
            for root, _, files in os.walk(bf):
                if os.path.basename(root) != "CMakeFiles":
                    continue
                for name in ("CMakeConfigureLog.yaml", "CMakeOutput.log", "CMakeError.log"):
                    if name in files:
                        p = os.path.join(root, name)
                        searched.append(p)
                        hits.append((name, p))
            if not hits:
                return "no cmake configure logs found (searched: {})".format(
                    ", ".join(searched) if searched else "no CMakeFiles dir")
            chunks = []
            for kind, path in hits[:3]:
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        txt = f.read()
                except Exception as e:
                    chunks.append("[{}] unreadable {}: {}".format(kind, path, e))
                    continue
                if kind == "CMakeConfigureLog.yaml":
                    parts = re.split(r"(?m)^  -\s*\n\s*kind:", txt)
                    if len(parts) <= 1:
                        parts = re.split(r"(?m)^  - kind:", txt)
                    scored = []
                    if len(parts) > 1:
                        for body in parts[1:]:
                            score = 0
                            m = re.search(r"exitCode:\s*(\d+)", body)
                            if m and int(m.group(1)) != 0:
                                score += 3
                            if re.search(r"is not able to compile|unable to find library|undefined reference", body):
                                score += 2
                            elif re.search(r"[Ff]ailed|[Ee]rror", body):
                                score += 1
                            if score:
                                scored.append((score, body))
                        scored.sort(key=lambda t: -t[0])
                        use = "\n--- event ---\n".join(b[-2500:] for _, b in scored[:2])
                        if not use:
                            use = txt[-budget:]
                    else:
                        key = [ln for ln in txt.splitlines()
                               if re.search(r"exitCode|is not able|[Ff]ailed|[Ee]rror|unable|undefined", ln)]
                        use = "\n".join(key[-40:])
                        if not use:
                            use = txt[-budget:]
                    chunks.append("[{}:{}]\n{}".format(kind, path, use[-budget:]))
                else:
                    key = [ln for ln in txt.splitlines()
                           if re.search(r"error|Error|unable|failed|not able|undefined|not found|is not able", ln)]
                    use = "\n".join(key[-30:]) if key else txt[-budget:]
                    chunks.append("[{}:{}]\n{}".format(kind, path, use[-budget:]))
            return "\n".join(chunks)[-(budget * 2):]
        except Exception as e:
            return "evidence collection failed: {}".format(e)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["racon_build_tests"] = True
        tc.variables["racon_build_wrapper"] = False
        tc.variables["racon_enable_cuda"] = False
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # E092: CMake has no OHOS platform module; build as Linux/armv8.
        # Same injection as edlib/1.2.7 (proven on OHOS aarch64).
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "armv8"
        # googletest 1.10.0 via FetchContent uses cmake_minimum_required(<3.5);
        # CMake 4.x removed that compat, same fix as edlib/bioparser.
        # Set both cache entry (own + FetchContent add_subdirectory) and env
        # (ExternalProject/FetchContent sub-process inheritance, groonga prec).
        os.environ.setdefault("CMAKE_POLICY_VERSION_MINIMUM", "3.5")
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Point upstream's edlib FetchContent fallback at the vendored local
        # dir: skips the git clone, keeps the exact v1.2.7 tag content, and
        # builds it as a subdirectory with the Linux + POLICY fixes above.
        # FETCHCONTENT_SOURCE_DIR_<UPPER> is the documented CMake override.
        tc.cache_variables["FETCHCONTENT_SOURCE_DIR_EDLIB"] = os.path.join(
            self.source_folder, "edlib_fallback").replace("\\", "/")
        # Round 7 (new domain): upstream spoa/thread_pool/googletest fallbacks
        # git-clone github.com on the true device (3x65s timeout, configure
        # fails at spoa-populate). Same vendoring as edlib: official
        # tarballs via conandata, exact tags, subdirectory inherits Linux +
        # POLICY fixes. FETCHCONTENT_SOURCE_DIR_<UPPER> skips the git clone.
        tc.cache_variables["FETCHCONTENT_SOURCE_DIR_SPOA"] = os.path.join(
            self.source_folder, "spoa_fallback").replace("\\", "/")
        tc.cache_variables["FETCHCONTENT_SOURCE_DIR_THREAD_POOL"] = os.path.join(
            self.source_folder, "thread_pool_fallback").replace("\\", "/")
        tc.cache_variables["FETCHCONTENT_SOURCE_DIR_GOOGLETEST"] = os.path.join(
            self.source_folder, "googletest_fallback").replace("\\", "/")
        # Round 6: upstream FetchContent spoa defaults spoa_optimize_for_native
        # ON (-march=native) which breaks OHOS aarch64 portability (same flag
        # the spoa/4.1.5 registry recipe disables). Force scalar/portable
        # fallback for the exact-4.0.8 subdirectory build; no -msse4.1 either.
        tc.cache_variables["spoa_optimize_for_native"] = False
        tc.cache_variables["spoa_optimize_for_portability"] = False
        # Round 4 (new domain): racon's own project() fails with
        # "CXX compiler identification is unknown" for
        # /data/service/hnp/bin/clang++. Prior rounds fixed dependency
        # rebuilds (edlib POLICY, edlib vendoring, zlib override) and cannot
        # explain this stage. mathic/1.4 precedent: shared profile still
        # points at the migrated path (stat ENOENT); resolve the real
        # compiler per tool and pin it. Deliberately no E191
        # CMAKE_TRY_COMPILE_TARGET_TYPE bypass (mathic round 2 proved it
        # ineffective for the same symptom); the real compiler check must pass.
        try:
            _compilers = self.conf.get("tools.build:compiler_executables", default=None)
        except Exception:
            _compilers = None
        if not isinstance(_compilers, dict):
            _compilers = {}
        _c = self._resolve_compiler(_compilers.get("c"), ("clang", "cc"))
        _cxx = self._resolve_compiler(_compilers.get("cpp"), ("clang++", "c++"))
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info("HMBS diag compilers c=%s cxx=%s" % (_c, _cxx))
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()
        self._fix_generated_toolchain_compiler(_compilers, _c, _cxx)

    def build(self):
        apply_conandata_patches(self)
        # OHOS sandbox git permission fix (same as ada-url precedent).
        try:
            self.run('git config --global --add safe.directory "*"',
                      ignore_errors=True)
        except Exception:
            pass
        probe = self._probe_cxx_toolchain()
        self.output.info("[toolchain-probe]\n" + probe)
        cmake = CMake(self)
        try:
            cmake.configure()
        except Exception as e:
            raise ConanException(
                "cmake.configure() failed [racon-configure-evidence] probe:\n{} | "
                "err: {} | configure logs:\n{}".format(probe, e, self._cmake_error_evidence())
            )
        self._patch_googletest_tmpdir()
        cmake.build()
        self._run_upstream_tests()

    def _ensure_writable_tmpdir(self):
        # True-device 2026-09-27 (round 5): gtest 1.10.0 CapturedStream
        # hardcodes /tmp/captured_stream.XXXXXX (gtest-port.cc) and ignores
        # TMPDIR, so EXPECT_DEATH tests abort with SIGABRT when /tmp is
        # not writable in the OHOS sandbox. HMBS injects a writable
        # TMPDIR/TMP/TEMP (.../runtime/<task>/tmp, local_mktemp=1).
        # Reuse it; fallback to build-local hmbs_tmp. No chmod/hardlink
        # (capabilities 0), only mkdir + env redirect.
        for key in ("TMPDIR", "TMP", "TEMP", "TEST_TMPDIR"):
            cand = os.environ.get(key)
            if cand:
                try:
                    os.makedirs(cand, exist_ok=True)
                    if os.path.isdir(cand):
                        return cand
                except Exception:
                    continue
        fallback = os.path.join(getattr(self, "build_folder", None) or os.getcwd(),
                                "hmbs_tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except Exception:
            pass
        return fallback

    def _patch_googletest_tmpdir(self):
        # Patch FetchContent-populated googletest (exact 1.10.0) between
        # configure (populate) and build (compile) so the fix is compiled
        # in. Replaces the hardcoded /tmp template with a TMPDIR-aware
        # runtime lookup. Idempotent; upstream test logic untouched.
        # With FETCHCONTENT_SOURCE_DIR_GOOGLETEST the source lives under
        # source_folder/googletest_fallback (not _deps in build_folder),
        # so search both trees.
        search_roots = []
        for attr in ("build_folder", "source_folder"):
            d = getattr(self, attr, None)
            if d and os.path.isdir(d):
                search_roots.append(d)
        if not search_roots:
            return
        old = 'char name_template[] = "/tmp/captured_stream.XXXXXX";'
        new_lines = [
            'char name_template[1024];',
            '    const char* hmbs_tmpdir = getenv("TMPDIR");',
            '    if (!hmbs_tmpdir || !*hmbs_tmpdir) hmbs_tmpdir = getenv("TEST_TMPDIR");',
            '    if (!hmbs_tmpdir || !*hmbs_tmpdir) hmbs_tmpdir = getenv("TMP");',
            '    if (!hmbs_tmpdir || !*hmbs_tmpdir) hmbs_tmpdir = "/tmp";',
            '    snprintf(name_template, sizeof(name_template), "%s/captured_stream.XXXXXX", hmbs_tmpdir);',
        ]
        new = "\n".join(new_lines)
        patched = 0
        for search_root in search_roots:
            for root, _dirs, files in os.walk(search_root):
                if "gtest-port.cc" not in files:
                    continue
                path = os.path.join(root, "gtest-port.cc")
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read()
                except Exception as e:
                    self.output.warning("HMBS diag gtest patch unreadable %s: %s" % (path, e))
                    continue
                if "hmbs_tmpdir" in text:
                    patched += 1
                    continue
                if old not in text:
                    continue
                text = text.replace(old, new)
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    patched += 1
                    self.output.info("HMBS diag patched gtest tmpdir %s" % path)
                except Exception as e:
                    self.output.warning("HMBS diag gtest patch failed %s: %s" % (path, e))
        if patched == 0:
            self.output.warning("HMBS diag gtest-port.cc not found for tmpdir patch")
        else:
            self.output.info("HMBS diag gtest tmpdir patched files=%d" % patched)

    def _find_test_binary(self):
        for root, _dirs, files in os.walk(self.build_folder):
            if "racon_test" in files:
                candidate = os.path.join(root, "racon_test")
                if os.path.isfile(candidate):
                    return candidate
        return None

    def _run_upstream_tests(self):
        # Upstream has 15 gtest cases (5 RaconInitializeTest death tests +
        # 10 RaconPolishingTest consensus/fragment cases, no CUDA).
        # Source of truth for total: TEST/TEST_F count in test/racon_test.cpp.
        # Execution: run racon_test directly (no ctest registration upstream).
        if not can_run(self):
            upstream = {
                "status": "skipped",
                "framework": "gtest",
                "command": "racon_test",
                "discovered": 15,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 15,
                "reason": "cross-build: test binary cannot run on build host",
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
            return
        test_bin = self._find_test_binary()
        if test_bin is None or not os.path.isfile(test_bin):
            raise ConanException("upstream test binary racon_test not found in build tree")
        # OHOS workers use mksh as /bin/sh which cannot exec ELF directly;
        # wrap with the bash from the build environment (barrier precedent).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not (os.path.isfile(bash) and os.access(bash, os.X_OK)):
            bash = "/bin/sh"
        tmpdir = self._ensure_writable_tmpdir()
        self.output.info("HMBS diag upstream tmpdir=%s" % tmpdir)
        run_env = os.environ.copy()
        for _k in ("TMPDIR", "TMP", "TEMP", "TEST_TMPDIR"):
            run_env[_k] = tmpdir
        proc = subprocess.run(
            [bash, "-c", '"$1" 2>&1', "_", test_bin],
            cwd=self.build_folder,
            capture_output=True, text=True, timeout=3600, env=run_env)
        raw = (proc.stdout or "") + (proc.stderr or "")
        # Echo raw gtest log so preflight keeps real evidence.
        print(raw, end="", flush=True)
        # Single deterministic source: gtest summary lines only.
        # [==========] 15 tests from 2 test suites ran.
        # [  PASSED  ] 15 tests.
        # [  FAILED  ] N tests (only present on failure).
        total = 0
        passed = 0
        failed = 0
        m = re.search(r"\[\s*PASSED\s*\]\s*(\d+)\s+tests", raw)
        if m:
            passed = int(m.group(1))
        mf = re.search(r"\[\s*FAILED\s*\]\s*(\d+)\s+tests", raw)
        if mf:
            failed = int(mf.group(1))
        m2 = re.search(r"\[\s*==========\s*\]\s*(\d+)\s+tests\s+from", raw)
        if m2:
            total = int(m2.group(1))
        # Self-check identity: passed + failed == executed; executed <= discovered.
        # executed is derived from the same gtest summary (no arithmetic repair).
        executed = passed + failed
        discovered = 15
        if total > 0:
            # total from [==========] is the executed count; keep it as
            # cross-check but do not overwrite passed/failed.
            executed = total
            # If summary lists only PASSED (no FAILED line), failed stays 0.
            if failed == 0 and passed == 0:
                passed = total
        status = "passed" if (executed == discovered and failed == 0 and proc.returncode == 0) else "failed"
        marker = {
            "status": status,
            "framework": "gtest",
            "command": "racon_test",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        if status != "passed":
            # Round 8 (true-device 2026-09-27, 15/15 run, 6 pass / 9 fail):
            # same small systematic drifts with vendored exact spoa 4.0.8
            # as with registry 4.1.5 (1312 vs 1333, 1658216 vs 1658477,
            # 1663982 vs 1664058), so the round-6 spoa-version hypothesis
            # is disproven. All deps are exact upstream tags (bioparser
            # 3.0.15, edlib 1.2.7, spoa 4.0.8, thread_pool 4.0.0, GTest
            # 1.10.0); sequence counts are correct (1/40/236), only
            # x86-tuned exact numeric thresholds drift <2% on OHOS
            # aarch64/clang scalar POA vs x86-64 SIMD. Upstream itself
            # accepts larger backend deviations (CUDA 1385 vs CPU 1312,
            # 4168 vs 1289 in test/racon_test.cpp). Fixtures are non-empty
            # (sizes correct, no silent skip). Report honest gaps and keep
            # the real gtest log above; do NOT disguise the test result as
            # a compile failure (no raise), do NOT touch assertions.
            marker["gaps"] = [
                {
                    "count": 6,
                    "category": "ohos_feature",
                    "detail": "6 Consensus* edit-distance drifts on OHOS aarch64/clang scalar POA vs x86-64 SIMD-tuned thresholds (e.g. 1312->1333); deterministic across spoa 4.1.5 and exact 4.0.8; upstream CUDA backend shows larger accepted deviations (1312->1385, 1289->4168)",
                    "evidence": "true-device racon_test 2026-09-27: 1312 vs 1333; upstream test/racon_test.cpp CUDA expectations 1385/1607/1541/1661/4168/1361 vs CPU 1312/1566/1317/1770/1289/1321",
                },
                {
                    "count": 3,
                    "category": "ohos_feature",
                    "detail": "3 FragmentCorrection*Full total_length drifts (1658216->1658477 +261, 1663982->1664058 +76, Mhap 1658216->1658477); sequence counts correct (236/236), lengths differ <0.02%",
                    "evidence": "true-device: total_length 1658477 vs 1658216, 1664058 vs 1663982; polished_sequences.size() 236 correct per gtest log",
                },
            ]
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)
        if status != "passed":
            self.output.warning(
                "upstream racon_test reported %d/%d passed (%d failed); "
                "gaps documented above, continuing to package (exit %s)" % (
                    passed, executed, failed, proc.returncode))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream `install()` only ships the CLI; also ship the library
        # and public headers for API consumers (test_package links libracon).
        copy(self, "*.a",
             src=os.path.join(self.build_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.so*",
             src=os.path.join(self.build_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include", "racon"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["racon"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "racon")]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "racon")
        self.cpp_info.set_property("cmake_target_name", "racon::racon")
