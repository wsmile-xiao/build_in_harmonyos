#!/usr/bin/env python3
"""Conan recipe — laz-perf 3.4.0 (CMake)

laz-perf is the C++ LAS/LAZ reader-writer and compression codec used by PDAL.
It implements the LASzip chunked-LAZ codec plus the LAS 1.2/1.3/1.4 header
models and the stream-level file API (`reader::named_file` /
`writer::named_file` / chunk compressor-decompressor pairs).

OHOS notes
----------
* The upstream test harness (`cpp/test/io_tests.cpp::makeTempFileName()`)
  hardcodes `/var/tmp/fnXXXXXX` for the scratch LAS/LAZ files it round-trips.
  HarmonyOS' root filesystem is read-only and `/var/tmp` may not exist at all,
  so `mkstemp()` fails, its return value is ignored, and the following
  `ofstream` silently produces nothing - 7 of the 21 io_tests cases then fail
  for reasons unrelated to lazperf (measured with /var/tmp mounted read-only:
  21 ran / 14 PASSED / 7 FAILED, and 21/21 once patched).  `patches/0001-...`
  resolves the scratch path through `$TMPDIR` instead (E002 family).
* The recipe creates a writable `$TMPDIR` under the build folder and exports it
  for the `ctest` run, because the upstream `add_test()` uses
  `WORKING_DIRECTORY "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/../.."`, which resolves
  to `/` when `CMAKE_RUNTIME_OUTPUT_DIRECTORY` is unset.
* `patches/0002-...` puts the configure-time `file(DOWNLOAD)` of the autzen
  benchmark asset behind an opt-in option: nothing in this build consumes it
  (only the `laszip` benchmark reads it, and that target needs an external
  LASzip that is not present), while CI must not reach github.com directly.
* `cpp/test/gtest/gtest-10-06-21/googletest/CMakeLists.txt` still declares
  `cmake_minimum_required(VERSION 2.8.12)`, which CMake >= 4 rejects outright;
  `CMAKE_POLICY_VERSION_MINIMUM` is pinned so the vendored gtest configures on
  both old and new CMake.
* gtest 1.10.0 is vendored inside the tarball (no configure-time network fetch)
  and compiles with `-Wall -Wshadow -Werror -Wconversion`; the OHOS clang
  driver emits `-Wunused-command-line-argument` for the flags its wrapper
  injects, so that one diagnostic is disabled.  No test assertion is touched.
* Upstream's `install()` rules only ship the six stream-level headers plus
  `lazperf_user_base.hpp` renamed to `lazperf_base.hpp`; the packaged header
  set mirrors that exactly.
"""
import glob
import json
import os
import re
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
)

required_conan_version = ">=2.0"


class LazPerfConan(ConanFile):
    name = "laz-perf"
    version = "3.4.0"

    description = (
        "C++ library for reading and writing LAS/LAZ LiDAR files; implements "
        "the LASzip chunked compression codec used by PDAL."
    )
    homepage = "https://github.com/hobuinc/laz-perf"
    license = "Apache-2.0"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("laz-perf", "las", "laz", "laszip", "lidar", "point-cloud",
              "compression")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_writable_tmp(self):
        # 真机 /tmp 只读时 CMake try_compile（project() 的编译器检查）也会
        # 失败。复用 hmbs 注入的可写 TMPDIR（zydis/4.1.1 先例），只重定向
        # 临时目录，不跳过任何测试。
        candidates = []
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            val = os.getenv(key)
            if val and val not in candidates:
                candidates.append(val)
        cap = os.getenv("HMBS_PLATFORM_CAPABILITIES")
        if cap:
            try:
                import json as _json
                tmpdir = _json.loads(cap).get("tmpdir")
                if tmpdir and tmpdir not in candidates:
                    candidates.insert(0, tmpdir)
            except Exception:
                pass
        home = os.path.expanduser("~")
        if home and home != "~":
            home_tmp = os.path.join(home, "tmp")
            if home_tmp not in candidates:
                candidates.append(home_tmp)
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                local_tmp = os.path.join(bf, "hmbs-tmp")
                if local_tmp not in candidates:
                    candidates.append(local_tmp)
        except Exception:
            pass
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w") as f:
                    f.write("ok")
                os.remove(probe)
                os.environ["TMPDIR"] = cand
                os.environ["TMP"] = cand
                os.environ["TEMP"] = cand
                return cand
            except Exception:
                continue
        return None

    def _resolve_compiler(self, configured, names):
        # 真机 clang 已从 /data/service/hnp/bin 迁移到 ~/usr/local/bin，
        # 而共享 profile 仍指向旧路径（zydis/4.1.1 实测先例）。按工具分别
        # 解析：旧路径存在则沿用，否则按 PATH 解析，最后试 ~/usr/local/bin。
        if configured and os.path.exists(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local",
                                "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.exists(cand):
                return cand
        return configured or names[0]

    def _fix_generated_toolchain_compiler(self, configured_map, c, cxx):
        # 实测（zydis/4.1.1 preflight 2026-09-18）：仅 pin
        # toolchain.cache_variables 并不能覆盖 profile 注入的旧路径，
        # 生成的 conan_toolchain.cmake 仍引用缺失的
        # /data/service/hnp/bin/clang，导致 project() 失败。所以直接修正
        # 已生成的单文件并导出 CC/CXX——仅在旧路径缺失且新路径存在时生效，
        # CI worker 不受影响。
        if not isinstance(configured_map, dict):
            configured_map = {}
        c_old = configured_map.get("c")
        cxx_old = configured_map.get("cpp")
        pairs = []
        if c_old and c and c_old != c \
                and not os.path.exists(c_old) and os.path.exists(c):
            pairs.append((c_old, c))
        if cxx_old and cxx and cxx_old != cxx \
                and not os.path.exists(cxx_old) and os.path.exists(cxx):
            pairs.append((cxx_old, cxx))
        if not pairs:
            return
        try:
            gf = getattr(self, "generators_folder", None)
            path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8",
                          errors="replace") as f:
                    text = f.read()
                orig = text
                for old_p, new_p in pairs:
                    text = text.replace(old_p, new_p)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    self.output.info(
                        "HMBS diag fixed generated toolchain %s" % path)
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
            self.output.warning(
                "HMBS diag compiler env export failed: %s" % e)

    def generate(self):
        tmpdir = self._ensure_writable_tmp()
        if tmpdir:
            env = Environment()
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
            env.vars(self, scope="build").save_sh("hmbs_tmpdir")
        tc = CMakeToolchain(self)
        # E092: CMake 4.4.3 自带模块没有 Platform/HarmonyOS.cmake，
        # 保留 CMAKE_SYSTEM_NAME=HarmonyOS 会在 project() 报
        # "System is unknown to cmake" 并连带编译器可用性检查失败
        # （本轮真机日志即此症状）。OHOS 与 Linux 同内核，借用 Linux
        # 平台模块（站内 lzo/2.10、ayatana-ido、abcmidi、ball 同类先例）；
        # 编译器仍由 conan_toolchain 指向 OHOS clang，不改变交叉编译语义。
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 编译器解析（zydis/4.1.1 实测先例）：profile 仍指向旧的
        # /data/service/hnp/bin/clang，而真机 clang 已迁移到 ~/usr/local/bin。
        # 按工具分别解析并 pin 到 toolchain；仅 pin 不足以覆盖 profile 注入
        # 的旧路径（zydis preflight 2026-09-18 证据），所以 generate 后再
        # 直接修正已生成的 conan_toolchain.cmake 并导出 CC/CXX。
        try:
            _exes = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        except Exception:
            _exes = None
        if not isinstance(_exes, dict):
            _exes = {}
        _c = self._resolve_compiler(_exes.get("c"), ("clang", "cc"))
        _cxx = self._resolve_compiler(_exes.get("cpp"),
                                      ("clang++", "c++"))
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info("HMBS diag compilers c=%s cxx=%s" % (_c, _cxx))
        # Build the upstream test suite: it is the L1 "上游官方测试" evidence.
        tc.variables["WITH_TESTS"] = True
        # The vendored gtest declares cmake_minimum_required(VERSION 2.8.12);
        # CMake >= 4 refuses policies below 3.5 unless a floor is given.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # gtest builds with -Werror; the OHOS clang wrapper injects flags that
        # it then reports as unused.  Disable only that diagnostic (E293
        # pattern - no blanket -Wno-error).
        tc.extra_cxxflags.append("-Wno-unused-command-line-argument")
        # HMBS lowmem (adapted from libarcus/5.0.0: `rm: Out of memory` /
        # Signal 9 with empty log): append -O1 -g0 via buildenv, additive
        # only. Never overwrites profile/toolchain flags (sysroot stays in
        # the toolchain file); only lowers per-TU peak RSS and object size.
        # Scoped to OHOS so local Linux defaults are untouched. Heavy
        # optional stack stays OFF (LAZPERF_FETCH_TEST_DATA default OFF,
        # benchmarks need external LASzip); WITH_TESTS stays ON, no test
        # is skipped.
        if self.settings.os == "OHOS":
            try:
                _lowmem = Environment()
                _lowmem.append("CFLAGS", ["-O1", "-g0"])
                _lowmem.append("CXXFLAGS", ["-O1", "-g0"])
                _lowmem.vars(self).save_script("hmbs_lowmem")
            except Exception:
                pass
        tc.generate()
        self._fix_generated_toolchain_compiler(_exes, _c, _cxx)

    def build(self):
        self._ensure_writable_tmp()
        apply_conandata_patches(self)
        self._append_lowmem_flags()

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        self._run_upstream_tests(cmake)

    def _append_lowmem_flags(self):
        # HMBS lowmem layer 2 (adapted from libarcus/5.0.0): append
        # -O1 -g0 to CMAKE_C/CXX_FLAGS at the end of the generated
        # conan_toolchain.cmake behind the idempotent HMBS_LOWMEM_FLAGS
        # marker, after any Release -O3/-g lines so the lower setting wins
        # per-TU. Additive only; bypasses -D/toolchain ordering. OHOS-only.
        if self.settings.os != "OHOS":
            return
        try:
            path = os.path.join(self.generators_folder,
                                "conan_toolchain.cmake")
        except Exception:
            return
        if not os.path.isfile(path):
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        if "HMBS_LOWMEM_FLAGS" in content:
            return
        content += (
            "\n# HMBS_LOWMEM_FLAGS: OOM mitigation "
            "(additive, no test skipped)\n"
            'string(APPEND CMAKE_C_FLAGS " -O1 -g0")\n'
            'string(APPEND CMAKE_CXX_FLAGS " -O1 -g0")\n'
        )
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
        except OSError as exc:
            self.output.warning(
                "HMBS lowmem flags: cannot write %s: %s" % (path, exc))
            return
        self.output.info("HMBS lowmem flags appended (-O1 -g0)")

    def _hmbs_emit_upstream(self, payload):
        line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
            payload, separators=(",", ":"))
        # Dual-channel: conan output + raw stdout so preflight catches it.
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                with open(os.path.join(bf, "hmbs_upstream.json"),
                          "w", encoding="utf-8") as f:
                    json.dump(payload, f)
        except Exception as e:
            self.output.warning("HMBS diag persist upstream failed: %s" % e)
        return line

    def _count_registered_ctest(self):
        count = 0
        try:
            bf = getattr(self, "build_folder", None) or ""
            for path in glob.glob(os.path.join(bf, "**", "CTestTestfile.cmake"),
                                  recursive=True):
                try:
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as f:
                        for line in f:
                            if "add_test(" in line:
                                count += 1
                except OSError:
                    continue
        except Exception as e:
            self.output.warning("HMBS diag count ctest failed: %s" % e)
        return count

    def _find_last_test_logs(self):
        # cmake_layout may place the real CTest tree one level below
        # self.build_folder (build/Release), so a single fixed path is
        # fail-open by construction. Primary first; walk capped at depth 6.
        bf = getattr(self, "build_folder", None) or ""
        candidates = [os.path.join(bf, "Testing", "Temporary",
                                   "LastTest.log")]
        try:
            if os.path.isdir(bf):
                base_depth = bf.count(os.sep)
                for cur, _dirs, files in os.walk(bf):
                    if "LastTest.log" in files:
                        full = os.path.join(cur, "LastTest.log")
                        if full not in candidates:
                            candidates.append(full)
                    if cur.count(os.sep) - base_depth > 6:
                        try:
                            _dirs[:] = []
                        except Exception:
                            pass
        except Exception:
            pass
        return candidates

    def _parse_ctest_lasttest(self):
        # Single deterministic source: Testing/Temporary/LastTest.log.
        # NOTE: ctest prints "N/M Test #K:" lines only on stdout;
        # LastTest.log carries per-test "N/M Testing:" headers plus verdict
        # footer lines ("Test Passed." / "***Test Failed." etc) and never
        # contains "Test #K" lines, so a stdout-style "Test #N ... Passed"
        # pattern matches nothing here (this round: 3/3 passed on stdout
        # yet parsed as 0/0). No stdout counting, no arithmetic patch-ups:
        #   discovered: M denominator of "N/M Testing:" / "N/M Test:" headers
        #     (every entry must agree, else honest failure)
        #   passed/failed/skipped: verdict phrases counted once each in a
        #     single pass ("***Test Failed." contains "Test Failed" but never
        #     "***Failed", so plain addition cannot double-count)
        # Falls back to honest failure marker when the log is absent.
        candidates = self._find_last_test_logs()
        existing = [p for p in candidates if os.path.isfile(p)]
        non_empty = []
        for path in existing:
            try:
                with open(path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    content = handle.read()
            except OSError:
                continue
            if content.strip():
                non_empty.append((path, content))
        if not non_empty:
            return (0, 0, 0, 0, [], candidates)
        # Prefer the log with the most test entries (real tree wins over
        # stale/empty ones).
        def _entries(item):
            _p, _c = item
            return len(re.findall(r"(?m)^\s*\d+/\d+\s+Test(?:ing)?:", _c))
        non_empty.sort(key=_entries)
        log_path, text = non_empty[-1]
        try:
            text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
        except Exception:
            pass
        sizes = set(
            int(m.group(1))
            for m in re.finditer(r"(?m)^\s*\d+/(\d+)\s+Test(?:ing)?:", text)
        )
        if len(sizes) != 1:
            self.output.warning(
                "HMBS diag LastTest denominators disagree %s in %s"
                % (sorted(sizes), log_path))
            return (0, 0, 0, 0, [], candidates)
        discovered = sizes.pop()
        passed = len(re.findall(r"Test Passed", text))
        failed = len(re.findall(r"Test Failed", text))
        failed += len(re.findall(r"Test Timeout", text))
        failed += len(re.findall(r"\*\*\*Failed", text))
        failed += len(re.findall(r"\*\*\*Timeout", text))
        skipped = len(re.findall(r"Test Skipped", text))
        skipped += len(re.findall(r"\*\*\*Skipped", text))
        executed = passed + failed
        self.output.info(
            "HMBS diag LastTest.log=%s discovered=%d executed=%d "
            "passed=%d failed=%d skipped=%d"
            % (log_path, discovered, executed, passed, failed, skipped))
        return (passed, failed, skipped, discovered, [log_path], candidates)

    def _run_upstream_tests(self, cmake):
        """Run the upstream ctest suite (L1) with a writable scratch directory.

        E002 family: HarmonyOS' root filesystem is read-only and `/var/tmp` may
        be absent.  7 io_tests cases round-trip a LAS/LAZ file through
        `makeTempFileName()`, which patch 0001 makes resolve `$TMPDIR`.  The
        upstream `add_test()` runs with `WORKING_DIRECTORY` that resolves to
        `/`, so an explicit writable TMPDIR is required for those cases; the
        same directory is also what a POSIX ctest run would use.
        """
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)

        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)   # Windows GetTempPath fallback
        env.define("TEMP", tmpdir)
        env.vars(self, scope="build").save_script("laz_perf_ctest_env")

        # `ctest` is launched by `CMake.ctest()` from `self.build_folder` (Conan
        # runs `build()` chdir'ed there), which is exactly where
        # `CTestTestfile.cmake` lands, so no `--test-dir` is needed.  Keep the
        # default conanbuild/conanrun scripts alongside ours so the runtime
        # library path survives in the shared build.
        test_error = None
        try:
            cmake.ctest(cli_args=["--output-on-failure"],
                        env=["laz_perf_ctest_env", "conanbuild", "conanrun"])
        except Exception as e:
            test_error = e
            self.output.warning(
                "ctest failed (will emit upstream marker before re-raise): %s"
                % e)
        registered = self._count_registered_ctest()
        passed, failed, skipped, discovered, found, searched = \
            self._parse_ctest_lasttest()
        self.output.info(
            "HMBS diag registered ctest entries=%d LastTest discovered=%d"
            % (registered, discovered))
        if not found:
            payload = {
                "status": "failed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": registered,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "LastTest.log not found or unparseable; searched: "
                          + "; ".join(searched),
            }
            self._hmbs_emit_upstream(payload)
            if test_error is not None:
                raise test_error
            raise RuntimeError(
                "upstream tests left no parseable LastTest.log: %s"
                % "; ".join(searched))
        # Self-check identities (diagnose only, never patch numbers):
        # passed + failed == executed; executed + skipped <= discovered.
        executed = passed + failed
        if not (passed + failed == executed
                and executed + skipped <= discovered
                and executed <= discovered):
            payload = {
                "status": "failed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "reason": "count identities violated "
                          "(discovered=%d executed=%d passed=%d failed=%d "
                          "skipped=%d) in %s"
                          % (discovered, executed, passed, failed,
                             skipped, "; ".join(found)),
            }
            self._hmbs_emit_upstream(payload)
            if test_error is not None:
                raise test_error
            raise RuntimeError("upstream test counts inconsistent: %s"
                               % payload)
        if registered > 0 and discovered != registered:
            self.output.warning(
                "HMBS diag ctest count drift: LastTest discovered(%d) != "
                "registered(%d)" % (discovered, registered))
        status = "passed" if (test_error is None and failed == 0
                              and skipped == 0 and discovered > 0
                              and executed == discovered) else "failed"
        payload = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if status != "passed":
            payload["reason"] = (
                "upstream ctest not fully green (discovered=%d executed=%d "
                "passed=%d failed=%d skipped=%d) in %s"
                % (discovered, executed, passed, failed, skipped,
                   "; ".join(found)))
        self._hmbs_emit_upstream(payload)
        if test_error is not None:
            raise test_error
        if status != "passed":
            raise RuntimeError("upstream tests failed: %s" % payload)

    def package(self):
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

        # Public headers: exactly the set upstream's install() ships.
        # Upstream installs lazperf_user_base.hpp *renamed* to
        # lazperf_base.hpp (the user-facing base header carrying the
        # LAZPERF_*_VERSION macros); mirror that, including the rename.
        #
        # One copy() per header rather than a "*.hpp" glob: conan.tools.files
        # .copy() 的签名是
        #   copy(conanfile, pattern, src, dst, keep_path, excludes,
        #        ignore_case, overwrite)
        # —— 没有 includes 参数（那是 CMake install() 的写法）。之前写成
        # copy(self, "*.hpp", src=..., dst=..., includes=[...]) 会在 package()
        # 阶段直接 TypeError: copy() got an unexpected keyword argument
        # 'includes'（构建与 3 个 ctest 用例都过了，倒在打包这一步）。
        # 也不能退回裸 "*.hpp"：它会连 cpp/lazperf/detail/*.hpp 一起拷进去，
        # 而上游 install() 只装这 7 个头。逐个点名最贴近上游语义。
        src_inc = os.path.join(self.source_folder, "cpp", "lazperf")
        dst_inc = os.path.join(self.package_folder, "include", "lazperf")
        for hdr in ("lazperf.hpp", "filestream.hpp", "header.hpp",
                    "readers.hpp", "vlr.hpp", "writers.hpp",
                    "lazperf_user_base.hpp"):
            copy(self, hdr, src=src_inc, dst=dst_inc, keep_path=False)
        os.rename(os.path.join(dst_inc, "lazperf_user_base.hpp"),
                  os.path.join(dst_inc, "lazperf_base.hpp"))

        # Library: taken from the build tree.  Upstream's install() ships only
        # the SHARED flavour of the target, so consuming it would leave the
        # default static build with no library at all; the on-disk names are
        # also the only stable contract between the two flavours.
        #
        # 每个 pattern 前面的 "*" 不是通配冗余，而是必须的：conan.tools.files
        # .copy() 用 fnmatch 拿 pattern 去匹配 **相对 src 的整条路径**，而不是
        # 文件名。产物在 build 树里位于子目录（cpp/liblazperf_s.a，因为
        # CMakeLists 对 cpp/ 用了 add_subdirectory），所以裸 "liblazperf_s.a"
        # 一个都匹配不上、package() 静默打包 0 个库文件，最后由 test_package
        # 的 CMakeDeps 报 "Library 'lazperf_s' not found in package"。
        # "*liblazperf_s.a" 让 "*" 吃掉 "cpp/" 这一段前缀。
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "*liblazperf.so*", src=self.build_folder, dst=libdir,
                 keep_path=False)
            copy(self, "*liblazperf.*dylib", src=self.build_folder, dst=libdir,
                 keep_path=False)
            copy(self, "*lazperf.dll", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)
            copy(self, "*lazperf.lib", src=self.build_folder, dst=libdir,
                 keep_path=False)
            copy(self, "*liblazperf.dll.a", src=self.build_folder, dst=libdir,
                 keep_path=False)
        else:
            copy(self, "*liblazperf_s.a", src=self.build_folder, dst=libdir,
                 keep_path=False)
            copy(self, "*lazperf_s.lib", src=self.build_folder, dst=libdir,
                 keep_path=False)
        # Carry the real upstream result into the package so cache-hit
        # test_package runs can re-emit without re-running the build.
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copyfile(src, os.path.join(dst_dir,
                                                  "hmbs_upstream.json"))
            else:
                self.output.warning(
                    "HMBS diag hmbs_upstream.json missing in package()")
        except Exception as e:
            self.output.warning("HMBS diag package upstream copy failed: %s"
                                % e)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "lazperf")
        self.cpp_info.set_property("cmake_target_name", "lazperf::lazperf")
        self.cpp_info.libs = ["lazperf"] if self.options.shared else ["lazperf_s"]
        self.cpp_info.includedirs = ["include"]
