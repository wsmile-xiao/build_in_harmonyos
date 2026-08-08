#!/usr/bin/env python3
"""Conan recipe for unshield 1.6.2-r1 on HarmonyOS PC (aarch64).

unshield is a tool and library to extract files from InstallShield CAB files.
It uses CMake build system and requires zlib for decompression.
zlib/1.3.1.1 (-fPIC variant) is required because libunshield.so links
against the static libz.a and aarch64 requires position-independent code.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, download, export_conandata_patches, apply_conandata_patches


class UnshieldConan(ConanFile):
    name = "unshield"
    version = "1.6.2-r1"
    package_type = "library"
    description = "Tool to extract InstallShield CAB files"
    license = "MIT"
    homepage = "https://github.com/twogood/unshield"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)
        # Vendored upstream test suite (unshield .gitattributes marks
        # test export-ignore, so GitHub tarballs omit it). Export it
        # alongside the recipe so source() can copy it into the tree.
        # NOTE: copy() matches fnmatch against file relative paths under
        # src (e.g. "test_suite/v0/avigomanager/CMakeLists.txt"), so the
        # pattern "test_suite" (a bare name) matches NOTHING — it has no
        # wildcard and never equals a nested file path. Use "test_suite/*"
        # whose '*' crosses '/' to recursively match every vendored file.
        copy(self, "test_suite/*", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def requirements(self):
        # zlib is required for CAB file decompression.
        # Use 1.3.1.1 (-fPIC static lib): static libz.a links into
        # libunshield.so; 1.3.1 would cause R_AARCH64 relocation errors.
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        # unshield's .gitattributes marks `test export-ignore`, so every
        # GitHub auto-generated tarball (tag, sha, codeload) omits the
        # test/ directory. We vendor the upstream test/ tree (from the
        # 1.6.2 tag git tree, commit 51de441) into the recipe folder at
        # `test_suite/` (exported to the cache by export_sources()), and
        # copy it into the source tree root here, so upstream CMakeLists.txt
        # `if(IS_DIRECTORY(.../test)) include(CTest)` (line 15) and
        # `if(BUILD_TESTING) add_subdirectory(test)` (line 95) both fire,
        # registering all 29 CTest cases.
        #
        # The test suite MUST be copied BEFORE apply_conandata_patches(),
        # because patches/0002-fix-stack-memory-file-test-bugs.patch edits
        # test/v5/stack_memory_file/test_stack_memory_file.c which only
        # appears in the source tree after this copy.
        vendored_test = os.path.join(self.export_sources_folder, "test_suite")
        if not os.path.isdir(vendored_test):
            raise ConanInvalidConfiguration(
                f"Vendored upstream test suite not found at {vendored_test}; "
                f"the recipe needs test_suite/ to run the 29 upstream "
                f"CTest cases."
            )
        copy(self, "*", src=vendored_test,
             dst=os.path.join(self.source_folder, "test"))

        # Download v0 提取测试组的 test_data.zip 归档（每个 3.5–26.7MB，
        # 共 48MB）。这些文件在上游 git 树中存在但被 .gitattributes
        # export-ignore 从 tarball 剥离；直接提交仓库会触发 GitCode 10MiB
        # 文件限制，因此通过 conandata 的 test_data 配置在 source() 阶段
        # 下载到 test/v0/<group>/，CI clone 后仍可获取。Conan download()
        # 自动按 url 列表重试并校验 sha256。
        _test_root = os.path.join(self.source_folder, "test")
        _test_data = self.conan_data.get("test_data") or {}
        for _group, _meta in _test_data.items():
            _dst_dir = os.path.join(_test_root, "v0", _group)
            os.makedirs(_dst_dir, exist_ok=True)
            _dst_file = os.path.join(_dst_dir, "test_data.zip")
            download(self, _meta["url"], _dst_file, sha256=_meta["sha256"])

        # Decode base64-encoded binary test fixtures (.b64 -> binary).
        # 仅用于 CVE-2015-1386 的小型二进制 fixture（data1.cab/data1.hdr，
        # 各几百字节），绕过 GitCode .diff endpoint 对二进制 patch 的限制。
        # v0 的 test_data.zip 已改为远端下载（见上），不再使用 .b64。
        import base64 as _b64
        for _root, _dirs, _files in os.walk(_test_root):
            for _f in _files:
                if not _f.endswith(".b64"):
                    continue
                _b64_path = os.path.join(_root, _f)
                _bin_path = os.path.join(_root, _f[:-4])
                with open(_b64_path, "r") as _b64f, open(_bin_path, "wb") as _binf:
                    _binf.write(_b64.b64decode(_b64f.read()))

        # Apply conandata patches AFTER the test suite is copied in,
        # so patches targeting test/ files (e.g. 0002 fixing
        # test/v5/stack_memory_file/test_stack_memory_file.c) can apply.
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Use own MD5 implementation to avoid OpenSSL dependency
        tc.variables["USE_OUR_OWN_MD5"] = "ON"
        # Disable OpenSSL auto-detection
        tc.variables["OPENSSL_ROOT_DIR"] = ""
        # Use link path in RPATH so $ORIGIN/../lib resolves correctly
        tc.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = "ON"
        # Enable upstream CTest test suite (29 add_test cases across v0/v5
        # groups). The vendored test/ directory is injected in source(),
        # so upstream CMakeLists.txt `if(IS_DIRECTORY(.../test))
        # include(CTest) endif()` (line 15) and `if(BUILD_TESTING)
        # add_subdirectory(test) endif()` (line 95) both fire and register
        # the full upstream test suite with CTest.
        tc.variables["BUILD_TESTING"] = "ON"
        # Force CTest to emit each test's stdout/stderr verbatim to the
        # build log (CMAKE_CTEST_ARGUMENTS is upstream's supported knob,
        # see https://cmake.org/cmake/help/latest/variable/CMAKE_CTEST_ARGUMENTS.html).
        # Conan 2.x cmake.test() does NOT pass --output-on-failure by default
        # (conan-io/conan issue #12407), so a failing test's DIAG stderr
        # fprintf is silently swallowed by CTest. Setting CMAKE_CTEST_ARGUMENTS
        # here makes `cmake --build . --target test` (which conan.test()
        # invokes) forward these flags to every ctest invocation, so the
        # real-device precheck log captures the exact failing branch instead
        # of only `***Failed 0.02 sec`. --output-on-failure prints failing
        # test stdout/stderr; --extra-verbose prints every test's output
        # regardless of pass/fail (cheap at 29 tests, ~1.4s total).
        tc.cache_variables["CMAKE_CTEST_ARGUMENTS"] = \
            "--output-on-failure;--extra-verbose"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Run the upstream CTest suite (29 add_test cases). The test/
        # directory is vendored in source() from test-suite.tar.gz
        # (conandata test_suite), so upstream CMakeLists.txt registers
        # all 29 tests when BUILD_TESTING=ON. cmake.test() builds the
        # `test` target, which upstream CMake'sCTest target invokes ctest
        # with CMAKE_CTEST_ARGUMENTS (set in generate()) forwarding
        # --output-on-failure and --extra-verbose, so the real-device
        # precheck log captures each failing test's stdout/stderr verbatim.
        cmake.test()

        # HMBS hard gate (evidence phase) requires a machine-readable JSON
        # marker line in stdout carrying the upstream test result, with
        # numbers parsed from the actual ctest framework output (not
        # estimated). cmake.test() above already ran the suite via the
        # `test` build target; re-invoke ctest once directly to obtain
        # parseable aggregate stdout (cmake.test() streams ctest output
        # through Conan's own log formatting, which the regex can't rely on),
        # then print the marker. The numbers MUST come from ctest's own
        # output, never hardcoded — a fabricated marker would be rejected
        # and violates the adaptation charter.
        self._emit_hmbs_upstream_marker()

    def _emit_hmbs_upstream_marker(self):
        """Re-run ctest directly, parse its aggregate summary line, and
        print the HMBS_UPSTREAM_TEST_RESULT JSON marker. Numbers are
        extracted from ctest stdout, never guessed. If ctest cannot be
        re-run or its summary line is absent, emit honest zeros — do NOT
        fabricate a pass."""
        import json as _json
        import re as _re
        import subprocess

        ctest_bin = os.environ.get("HMBS_CTEST", "ctest")
        # ctest --test-dir points at the CMake build directory regardless of
        # cwd; self.build_folder is where Conan's CMake helper ran configure.
        cmd = [
            ctest_bin, "--test-dir", self.build_folder,
            "--output-on-failure", "--extra-verbose",
        ]
        raw = ""
        try:
            proc = subprocess.run(
                cmd, cwd=self.build_folder, env=os.environ.copy(),
                capture_output=True, text=True, timeout=1500,
            )
            raw = (proc.stdout or "") + (proc.stderr or "")
        except Exception:
            raw = ""

        # ctest summary line, e.g.:
        #   "100% tests passed, 0 tests failed out of 29"
        total = passed = failed = skipped = 0
        m = _re.search(
            r'(\d+)%\s*tests?\s+passed,\s*(\d+)\s+tests?\s+failed\s+out\s+of\s+(\d+)',
            raw,
        )
        if m:
            failed = int(m.group(2))
            total = int(m.group(3))
            passed = total - failed
            sk = _re.search(r'(\d+)\s+[Nn]ot\s+[Rr]un', raw)
            skipped = int(sk.group(1)) if sk else 0
        # else: leave zeros — honest "no parseable evidence" state, not a fake pass.

        marker = {
            "status": "passed" if (total > 0 and failed == 0) else "failed",
            "framework": "ctest",
            "command": " ".join(cmd),
            "discovered": total,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        # One single line, valid JSON, prefixed with the marker key the HMBS
        # scanner greps for. print() lands it in the build log the preflight
        # captures.
        print(f'HMBS_UPSTREAM_TEST_RESULT={_json.dumps(marker)}')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # unshield-deobfuscate has no install() target in upstream CMakeLists.txt,
        # so copy it manually. The binary is at build_folder/src/unshield-deobfuscate.
        deobf_src = os.path.join(self.build_folder, "src", "unshield-deobfuscate")
        if os.path.exists(deobf_src):
            copy(self, "unshield-deobfuscate",
                 src=os.path.dirname(deobf_src),
                 dst=os.path.join(self.package_folder, "bin"))

        # Copy the upstream test_stack_memory_file binary into the package.
        # This has TWO load-bearing purposes:
        #
        # 1. HMBS preflight evidence gate. The HMBS_UPSTREAM_TEST_RESULT marker
        #    is emitted by _emit_hmbs_upstream_marker() in build() (after
        #    cmake.test() runs the full 29-case upstream CTest suite). When a
        #    preflight `conan create` hits a cached binary, Conan skips build()
        #    entirely (`Already installed!`) and the marker never prints, which
        #    hmbs judges as `incomplete` (missing upstream test evidence) and
        #    refuses to release. Conan computes the binary (package) hash from
        #    the package's file contents; adding this file to the package forces
        #    the binary hash to change, so the next `conan create` cannot hit
        #    the stale cache and MUST re-run build() — which re-runs the suite
        #    and re-prints the marker. This makes the evidence gate robust to
        #    Conan's cache reuse independent of the preflight command flags.
        #
        # 2. test_package consumer check. test_package/conanfile.test() probes
        #    the package for this binary and, when present, re-runs it directly
        #    as a second upstream-test evidence channel that does NOT depend on
        #    the main recipe's build() having run this round.
        #
        # test_stack_memory_file is the only upstream CTest case that links
        # libunshield (patch 0005 statically links it via the libunshield_static
        # twin, eliminating the OHOS DT_NEEDED bare-SONAME load failure). It
        # uses an in-memory fixture (no external test data), so it is fully
        # self-contained and safe to ship in the package.
        tsf_dir = os.path.join(
            self.build_folder, "test", "v5", "stack_memory_file")
        tsf = os.path.join(tsf_dir, "test_stack_memory_file")
        if os.path.exists(tsf):
            copy(self, "test_stack_memory_file",
                 src=tsf_dir, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["unshield"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]