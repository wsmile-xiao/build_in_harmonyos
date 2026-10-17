#!/usr/bin/env python3
"""Conan recipe — libblobmsg 2026.02.13 (OpenWrt blobmsg slice of libubox, CMake)."""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class LibblobmsgConan(ConanFile):
    name = "libblobmsg"
    version = "2026.02.13"
    description = "OpenWrt blobmsg data container library (blob/blobmsg attribute handling plus blobmsg<->json conversion, split from libubox)"
    license = "ISC"
    homepage = "https://github.com/openwrt/libubox"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("json-c/0.18")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Upstream PKG_SEARCH_MODULE(JSONC json-c REQUIRED) needs json-c.pc
        PkgConfigDeps(self).generate()
        # json-c headers live in include/json-c/ but PkgConfigDeps emits
        # -I${includedir}; patch it to -I${includedir}/json-c
        pc = os.path.join(self.generators_folder, "json-c.pc")
        if os.path.exists(pc):
            with open(pc, "r", encoding="utf-8") as f:
                data = f.read()
            fixed = data.replace('-I"${includedir}"', '-I"${includedir}/json-c"')
            if fixed != data:
                with open(pc, "w", encoding="utf-8") as f:
                    f.write(fixed)
        tc = CMakeToolchain(self)
        # E092: OHOS has no CMake platform module -> map to Linux
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch))
        tc.variables["BUILD_LUA"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        # Build the upstream C unit tests (tests/test-*.c) so build() can
        # execute them for the HMBS_UPSTREAM_TEST_RESULT evidence marker.
        tc.variables["UNIT_TESTING"] = "ON"
        # Skip install-time RPATH rewriting: CMake RPATH_CHANGE rewrites
        # .so files linked against json-c into artifacts the OHOS musl
        # loader cannot load (same platform issue as libubox/20260222).
        tc.cache_variables["CMAKE_SKIP_INSTALL_RPATH"] = "TRUE"
        tc.generate()

    # ------------------------------------------------------------------
    # OHOS-unsupported test targets
    #
    # Upstream tests/CMakeLists.txt unconditionally adds:
    #   * *-san variants (-fsanitize=address,leak,undefined — unsupported
    #     by the OHOS clang in CI/preflight),
    #   * cram/ (creates a python venv and `pip install cram` — needs
    #     network at build time),
    #   * shunit2/ (shell harness, driven via ctest, not a compiled test),
    #   * fuzz/ (Clang-only, -fsanitize=fuzzer — unsupported on OHOS),
    # and the top-level CMakeLists adds a jshn-san target likewise.
    # The 14 plain (non-san) C unit binaries are fully buildable and are
    # executed below with cram-equivalent invocation/output checks.
    # ------------------------------------------------------------------
    def _disable_ohos_unsupported_tests(self):
        tests_cmake = os.path.join(self.source_folder, "tests", "CMakeLists.txt")
        if os.path.isfile(tests_cmake):
            with open(tests_cmake, "r", encoding="utf-8") as f:
                data = f.read()
            orig = data
            data = data.replace("ADD_SUBDIRECTORY(cram)",
                                "# HMBS-OHOS: cram needs pip network at build time\n#ADD_SUBDIRECTORY(cram)")
            data = data.replace("ADD_SUBDIRECTORY(shunit2)",
                                "# HMBS-OHOS: shunit2 shell harness not executed on OHOS\n#ADD_SUBDIRECTORY(shunit2)")
            data = data.replace("ADD_SUBDIRECTORY(fuzz)",
                                "# HMBS-OHOS: fuzz needs -fsanitize=fuzzer, unsupported\n#ADD_SUBDIRECTORY(fuzz)")
            data = data.replace("  ADD_UNIT_TEST_SAN(${test_case})",
                                "  # HMBS-OHOS: -san needs address/leak sanitizer, unsupported\n  #ADD_UNIT_TEST_SAN(${test_case})")
            if data != orig:
                with open(tests_cmake, "w", encoding="utf-8") as f:
                    f.write(data)
                self.output.info("[upstream] disabled OHOS-unsupported test targets in tests/CMakeLists.txt")
        top_cmake = os.path.join(self.source_folder, "CMakeLists.txt")
        if os.path.isfile(top_cmake):
            with open(top_cmake, "r", encoding="utf-8") as f:
                data = f.read()
            orig = data
            data = data.replace("ADD_UNIT_TEST_SAN(jshn)",
                                "# HMBS-OHOS: jshn-san needs sanitizers, unsupported\n#ADD_UNIT_TEST_SAN(jshn)")
            if data != orig:
                with open(top_cmake, "w", encoding="utf-8") as f:
                    f.write(data)
                self.output.info("[upstream] disabled jshn-san in top CMakeLists.txt")

    def build(self):
        self._disable_ohos_unsupported_tests()
        # CMakeToolchain does not inject PKG_CONFIG_PATH -> add generators dir
        prev = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = f"{self.generators_folder}:{prev}".rstrip(":")
        try:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
        finally:
            if prev:
                os.environ["PKG_CONFIG_PATH"] = prev
            else:
                os.environ.pop("PKG_CONFIG_PATH", None)
        self._run_upstream_tests()

    # ------------------------------------------------------------------
    # Upstream tests (openwrt/libubox tests/test-*.c, 14 binaries).
    #
    # Upstream drives these via cram .t files (needs pip-installed cram +
    # valgrind, both unavailable on OHOS). Each case below mirrors the
    # corresponding tests/cram/test_*.t invocation and expected output
    # fragment, so the check is output-content based, not exit-code-only:
    # an exit-0 stub or empty-fixture run cannot pass the fragment match
    # (toybox-tar lesson). Negative tests (test-b64_decode/encode) assert
    # upstream: they must abort with an Assertion message, exactly as the
    # .t file expects.
    # ------------------------------------------------------------------
    def _emit_upstream(self, result):
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        # Dual-channel emit: HMBS preflight scrapes raw stdout.
        print(marker, flush=True)
        self.output.info(marker)
        try:
            with open(os.path.join(str(self.build_folder), "hmbs_upstream_result.json"),
                      "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    def _fail_upstream(self, reason, executed=0, passed_count=0, failed_count=0):
        result = {
            "status": "failed",
            "framework": "custom-c-unit",
            "command": "upstream libubox C unit suite (15 invocations over 14 test-* binaries)",
            "discovered": 15,
            "executed": executed,
            "passed": passed_count,
            "failed": failed_count,
            "skipped": 0,
            "reason": reason,
        }
        self._emit_upstream(result)
        raise ConanException(f"upstream libubox test suite setup failed: {reason}")

    def _run_upstream_tests(self):
        try:
            bindir = self._locate_test_bindir()
        except ConanException as exc:
            self._fail_upstream(str(exc))
        src_tests = os.path.join(self.source_folder, "tests")
        cram_inputs = os.path.join(src_tests, "cram", "inputs")
        fuzz_corpus = os.path.join(src_tests, "fuzz", "corpus")
        # valid-blobmsg.bin is the stable positive fixture; fall back to the
        # first corpus file if the fixture set ever changes upstream.
        parse_fixture = os.path.join(fuzz_corpus, "valid-blobmsg.bin")
        if not os.path.isfile(parse_fixture):
            try:
                names = sorted(os.listdir(fuzz_corpus))
            except OSError:
                names = []
            parse_fixture = os.path.join(fuzz_corpus, names[0]) if names else parse_fixture
        cases = [
            {"name": "test-avl", "args": [], "expect": "test_basics:"},
            {"name": "test-b64", "args": [], "expect": "Zm9vYmFy"},
            {"name": "test-b64_decode", "args": [], "expect_abort": "Assertion"},
            {"name": "test-b64_encode", "args": [], "expect_abort": "Assertion"},
            {"name": "test-blob-buflen", "args": [], "expect": "SUCCESS"},
            {"name": "test-blob-parse", "args": [os.path.join(cram_inputs, "key-build.ucert")],
             "expect": "CHAIN ELEMENT"},
            {"name": "test-blob-parse-invalid", "bin": "test-blob-parse",
             "args": [os.path.join(cram_inputs, "invalid.ucert")], "expect": "cannot parse cert"},
            {"name": "test-blobmsg", "args": [], "expect": "Hello, world!"},
            {"name": "test-blobmsg-parse", "args": [parse_fixture],
             "expect": "blobmsg_parse:"},
            {"name": "test-blobmsg-types", "args": [], "expect": "blobmsg dump"},
            {"name": "test-blobmsg_check_array", "args": [], "expect": "test passed"},
            {"name": "test-blobmsg-procd-instance",
             "args": [os.path.join(cram_inputs, "procd-instance-nlbwmon.bin")], "expect": ": OK"},
            {"name": "test-json-script", "args": [os.path.join(cram_inputs, "json-script.json")],
             "expect": "exec"},
            {"name": "test-list", "args": [], "expect": "test_basics:"},
            {"name": "test-runqueue", "args": [], "expect": "All done!", "timeout": 180},
        ]
        for c in cases:
            for p in c["args"]:
                if p and not os.path.isfile(p):
                    self._fail_upstream(f"upstream test input missing: {p}")

        env = os.environ.copy()
        libdirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                d = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(d):
                    libdirs.append(d)
        libdirs.append(bindir)
        libdirs.append(str(self.build_folder))
        prev_ld = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = ":".join(libdirs + ([prev_ld] if prev_ld else []))

        passed = 0
        failed = []
        inv_labels = []
        for c in cases:
            exe = os.path.join(bindir, c.get("bin", c["name"]))
            if not os.path.isfile(exe):
                self._fail_upstream(f"upstream test binary not built: {exe} (UNIT_TESTING=ON expected)")
            label = " ".join([c["name"]] + [os.path.basename(a) for a in c["args"]])
            inv_labels.append(label)
            try:
                proc = subprocess.run(
                    [exe] + c["args"], cwd=bindir, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    timeout=c.get("timeout", 60),
                )
                out = (proc.stdout or b"").decode("utf-8", "replace")
                rc = proc.returncode
            except subprocess.TimeoutExpired as exc:
                raw = exc.stdout or b""
                out = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
                rc = 124
            if "expect_abort" in c:
                ok = (rc != 0) and (c["expect_abort"] in out)
            else:
                ok = (rc == 0) and (c["expect"] in out) and (out.strip() != "")
            self.output.info(f"[upstream] {label}: rc={rc} ok={ok}")
            self.output.info(f"[upstream] {label} output tail: {(out.strip().splitlines() or ['<empty>'])[-3:]}")
            if ok:
                passed += 1
            else:
                failed.append(f"{label}: rc={rc}, expected fragment {c.get('expect', c.get('expect_abort'))!r}, "
                              f"tail: {chr(10).join(out.strip().splitlines()[-8:])}")

        discovered = len(cases)
        executed = len(cases)
        nfailed = len(failed)
        status = "passed" if (nfailed == 0 and passed == discovered and discovered > 0) else "failed"
        result = {
            "status": status,
            "framework": "custom-c-unit",
            "command": " && ".join(inv_labels),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": nfailed,
            "skipped": 0,
        }
        self._emit_upstream(result)
        if status != "passed":
            raise ConanException(
                f"upstream libubox test suite did not fully pass: "
                f"{passed}/{executed} passed, {nfailed} failed\n" + "\n---\n".join(failed[:5]))

    def _locate_test_bindir(self):
        candidates = []
        for root, dirs, files in os.walk(str(self.build_folder)):
            dirs[:] = [d for d in dirs if d not in ("CMakeFiles", ".cmake")]
            for name in files:
                if name.startswith("test-") and "." not in name and not name.endswith("-san"):
                    candidates.append(root)
        if not candidates:
            raise ConanException(
                f"no upstream test binaries found under {self.build_folder} (UNIT_TESTING=ON expected)")
        # Prefer the directory holding the most test binaries.
        by_dir = {}
        for d in candidates:
            by_dir[d] = by_dir.get(d, 0) + 1
        return sorted(by_dir, key=lambda d: -by_dir[d])[0]

    def package(self):
        CMake(self).install()
        # OHOS musl loader compat: overwrite install-tree .so files that
        # link json-c with the pristine build-tree artifacts.
        build_dir = os.path.join(self.build_folder, str(self.settings.build_type))
        if not os.path.isdir(build_dir):
            build_dir = self.build_folder
        for name in ("libubox.so", "libblobmsg_json.so", "libjson_script.so"):
            hits = glob.glob(os.path.join(build_dir, "**", name), recursive=True)
            if not hits:
                continue
            src = hits[0]
            dst = os.path.join(self.package_folder, "lib", name)
            if os.path.exists(dst):
                shutil.copy2(src, dst)
        # libblobmsg is a pure library package: drop the jshn CLI and
        # helper scripts so no bin/ remains (R38: library must not ship bin/).
        for sub in ("bin", "share"):
            d = os.path.join(self.package_folder, sub)
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)
        # Persist the upstream test verdict for test_package re-emit on
        # Conan cache hits (build() is skipped then, its log lines vanish).
        src_result = os.path.join(str(self.build_folder), "hmbs_upstream_result.json")
        if os.path.isfile(src_result):
            shutil.copy2(src_result, os.path.join(self.package_folder, "hmbs_upstream_result.json"))

    def package_info(self):
        # blobmsg core (blobmsg_buf_init/add_*/parse) lives in ubox;
        # blobmsg<->json conversion lives in blobmsg_json.
        self.cpp_info.libs = ["ubox", "blobmsg_json", "json_script"]
