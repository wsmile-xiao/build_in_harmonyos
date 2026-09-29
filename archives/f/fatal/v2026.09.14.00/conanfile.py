#!/usr/bin/env python3
"""Conan recipe for fatal v2026.09.14.00 — Facebook Template Library (header-only).

fatal is a header-only C++14/17 template-metaprogramming library: the
`fatal/` tree is installed as-is and consumers just add it to their include
path.  There is nothing to compile for the package itself.

Upstream test suite (rule 4 — executed for real in build()):
upstream ships its own harness (`test.sh` + `compile.sh` + `scripts.inc`)
which walks every `*_test.cpp` under `fatal/`, compiles it with
`-Wall -Werror -Wextra -O0 -g -pthread -ftemplate-depth-1024 -std=c++17`
and runs the resulting binary.  Each binary self-reports
`succeeded: passed <N>/<N>`.

  * test translation units : 67   (`find . -name '*_test.cpp'`)
  * declared cases         : 845  (`FATAL_TEST(` occurrences)
  * executable cases       : 839  — 6 `FATAL_TEST` starters live inside a
    `/* TODO: IMPLEMENT */` block comment in
    `fatal/string/test/rope_test.cpp`, upstream never compiles them.

OHOS adaptation notes:
  * upstream `compile.sh` stages objects in `/tmp/.build`; `/tmp` is a
    read-only erofs on HarmonyOS PC, so this recipe compiles straight into
    the Conan build folder instead.
  * `subprocess` does not resolve bare executable names through PATH on
    OHOS (posix_spawn), so the compiler is resolved to an absolute path.
  * two upstream sources need portability patches (see conandata.yml):
    a deprecated `std::iterator` base in `rope.h`, and a libc++
    `static_assert` inside `std::tuple_element` that turns an upstream
    SFINAE probe into a hard error.
"""
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get
)
from conan.tools.layout import basic_layout

# upstream test harness settings (mirror of test.sh / compile.sh)
CXX_FLAGS = [
    "-O0", "-g", "-pthread",
    "-ftemplate-depth-1024", "-ftemplate-backtrace-limit=0",
    "-ferror-limit=1",
    "-Wall", "-Werror", "-Wextra",
    "-std=c++17",
]
COMPILE_TIMEOUT = 2400
RUN_TIMEOUT = 900
JOBS = 4

CASES_RE = re.compile(r"^FATAL_TEST\(", re.M)
SUCCESS_RE = re.compile(r"passed\s+(\d+)\s*/\s*(\d+)")

CXX_CANDIDATES = [
    "/data/service/hnp/bin/clang++",
    "/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang++",
    "/usr/bin/clang++",
]


class FatalConan(ConanFile):
    name = "fatal"
    version = "v2026.09.14.00"
    description = ("fatal — Facebook Template Library, header-only C++ "
                   "template metaprogramming toolkit")
    license = "BSD-3-Clause"
    homepage = "https://github.com/facebook/fatal"
    url = ""

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def package_id(self):
        self.info.clear()

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # 官方辅助：按 conandata.yml 的 patch_file 路径逐文件精确复制到
        # export_sources_folder（不要用 copy("patches/*.patch", dst=…/patches)，
        # copy 默认 keep_path=True 会把 "patches/" 相对路径再拼一次，
        # 产生 patches/patches/ 双层嵌套，导致 build() 期 apply 找不到补丁）
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._run_upstream_tests()

    # ── upstream official test suite ────────────────────────────────────
    def _find_cxx(self):
        for candidate in CXX_CANDIDATES:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        found = shutil.which("clang++")
        if found:
            return found
        raise ConanException(
            "fatal: no C++ compiler found (looked for %s and clang++ in PATH)"
            % ", ".join(CXX_CANDIDATES)
        )

    def _discover(self):
        tests = []
        for dirpath, _dirnames, filenames in os.walk(self.source_folder):
            for name in filenames:
                if name.endswith("_test.cpp"):
                    full = os.path.join(dirpath, name)
                    tests.append(os.path.relpath(full, self.source_folder))
        return sorted(tests)

    def _count_declared_cases(self, rel):
        with open(os.path.join(self.source_folder, rel),
                  encoding="utf-8", errors="replace") as handle:
            return len(CASES_RE.findall(handle.read()))

    def _build_and_run(self, rel, cxx, out_dir):
        tag = rel.replace("/", "__")[:-len(".cpp")]
        binary = os.path.join(out_dir, tag)

        cmd = [cxx] + CXX_FLAGS + ["-I", ".", rel, "-o", binary]
        try:
            proc = subprocess.run(cmd, cwd=self.source_folder,
                                  capture_output=True, text=True,
                                  timeout=COMPILE_TIMEOUT)
        except subprocess.TimeoutExpired:
            return {"file": rel, "compile": "timeout", "run": "-",
                    "passed": 0, "total": 0, "note": "compile timeout"}

        if proc.returncode != 0 or not os.path.exists(binary):
            tail = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
            return {"file": rel, "compile": "FAIL", "run": "-",
                    "passed": 0, "total": 0, "note": " | ".join(tail)}

        try:
            run = subprocess.run([binary], cwd=self.source_folder,
                                 capture_output=True, text=True,
                                 timeout=RUN_TIMEOUT,
                                 env={**os.environ, "LC_ALL": "C"})
        except subprocess.TimeoutExpired:
            return {"file": rel, "compile": "ok", "run": "timeout",
                    "passed": 0, "total": 0, "note": "run timeout"}

        output = (run.stdout or "") + (run.stderr or "")
        match = SUCCESS_RE.search(output)
        passed = int(match.group(1)) if match else 0
        total = int(match.group(2)) if match else 0
        state = "ok" if (run.returncode == 0 and match and passed == total) \
            else "FAIL"
        note = ""
        if state != "ok":
            note = " | ".join(
                line for line in output.strip().splitlines()[-3:] if line.strip()
            )
        return {"file": rel, "compile": "ok", "run": state,
                "passed": passed, "total": total, "note": note}

    def _run_upstream_tests(self):
        """Compile + run every upstream `*_test.cpp` derived test binary."""
        cxx = self._find_cxx()
        tests = self._discover()
        out_dir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(out_dir, exist_ok=True)

        declared = sum(self._count_declared_cases(rel) for rel in tests)
        self.output.info(
            "[fatal upstream tests] upstream official tests via ./test.sh "
            "(fatal's make check / ctest equivalent; header-only harness)"
        )
        self.output.info(
            "[fatal upstream tests] harness=test.sh+compile.sh TUs=%d "
            "declared_cases=%d compiler=%s jobs=%d"
            % (len(tests), declared, cxx, JOBS)
        )

        with ThreadPoolExecutor(max_workers=JOBS) as pool:
            results = list(pool.map(
                lambda rel: self._build_and_run(rel, cxx, out_dir), tests
            ))

        for res in results:
            self.output.info(
                "[fatal upstream tests] %-56s compile=%-7s run=%-7s %s/%s%s"
                % (res["file"], res["compile"], res["run"], res["passed"],
                   res["total"],
                   ("  << " + res["note"]) if res["note"] else "")
            )

        compiled = sum(1 for r in results if r["compile"] == "ok")
        executed = sum(r["total"] for r in results)
        passed = sum(r["passed"] for r in results)
        broken = [r for r in results
                  if r["compile"] != "ok" or r["run"] != "ok"]
        rate = (100.0 * passed / executed) if executed else 0.0

        self.output.info(
            "[fatal upstream tests] SUMMARY: TUs=%d compiled=%d "
            "executed_cases=%d passed=%d failed=%d skipped=0 pass_rate=%.1f%%"
            % (len(tests), compiled, executed, passed, len(broken), rate)
        )

        if broken or compiled != len(tests) or executed != passed:
            details = "\n".join(
                "  - %s compile=%s run=%s %s/%s %s"
                % (r["file"], r["compile"], r["run"], r["passed"], r["total"],
                   r["note"])
                for r in broken
            )
            raise ConanException(
                "fatal upstream test suite FAILED: %d/%d TUs compiled, "
                "%d/%d cases passed\n%s"
                % (compiled, len(tests), passed, executed, details)
            )

    # ── packaging ───────────────────────────────────────────────────────
    def package(self):
        # header-only: install the whole `fatal/` include tree so consumers
        # use `#include <fatal/...>` with `<pkg>/include` on their path.
        # NOTE: Conan 2 copy() does NOT resolve a relative dst against
        # package_folder — dst must be an absolute path, otherwise files
        # land in the process CWD and the package ends up empty.
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "fatal"),
             dst=os.path.join(self.package_folder, "include", "fatal"))
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "fatal"),
             dst=os.path.join(self.package_folder, "include", "fatal"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
