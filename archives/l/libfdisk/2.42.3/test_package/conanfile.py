#!/usr/bin/env python3
"""Conan test_package — libfdisk 2.42.3 L1 test.

Compiles test_libfdisk.c against the packaged libfdisk (+ bundled libuuid)
and runs it. Emits HMBS_TEST_PACKAGE_RESULT with deterministic counts
(14 CHECKs in the C source) and re-emits the persisted upstream marker so
Conan cache hits still carry upstream evidence.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


# Number of CHECK() assertions in test_libfdisk.c — must stay in sync.
# 14 CHECKs: version-code(1) + version-substr(1) + parse(1) + features(1)
# + new_context(1) + nlabels(1) + next_label(1) + new_partition(1)
# + part set(1) + part start(1) + part size(1) + new_table(1)
# + table_empty(1) + new_script(1).
TEST_CHECKS = 14


class LibfdiskTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = compilers.get("c")
        if cand and os.path.isabs(str(cand)) and os.path.isfile(str(cand)):
            return str(cand)
        for tool_name in ("clang", "cc"):
            found = shutil.which(tool_name)
            if found and os.path.isfile(found):
                return found
        cxx = os.environ.get("CC", "")
        if cxx and shutil.which(cxx):
            return cxx
        return "clang"

    def build(self):
        incs, libdirs = [], []
        for _r, _d in self.dependencies.items():
            try:
                incs += list(_d.cpp_info.includedirs)
            except Exception:
                pass
            try:
                libdirs += list(_d.cpp_info.libdirs)
            except Exception:
                pass
        # Deduplicate while keeping order.
        inc = " ".join("-I" + p for p in dict.fromkeys(incs) if p and os.path.isdir(p))
        link_dirs = [p for p in dict.fromkeys(libdirs) if p and os.path.isdir(p)]
        link = " ".join(
            ["-L" + p for p in link_dirs]
            + ["-lfdisk", "-luuid"]
            + (["-Wl,-rpath," + p for p in link_dirs] if link_dirs else [])
        )
        cc = self._resolve_cc()
        self.output.info("test_package CC={}".format(cc))
        src = os.path.join(self.source_folder, "test_libfdisk.c")
        out_bin = os.path.join(self.build_folder, "test_libfdisk")
        # -I for generated libfdisk.h (build include dir is packaged).
        self.run("{} {} test_libfdisk.c -o test_libfdisk {}".format(cc, inc, link),
                 cwd=self.source_folder if os.path.isfile(src) else self.build_folder,
                 env="conanbuild")
        # Normalize binary location for test().
        for cand in (
            os.path.join(self.source_folder, "test_libfdisk"),
            os.path.join(self.build_folder, "test_libfdisk"),
        ):
            if os.path.isfile(cand):
                out_bin = cand
                break

    def _reemit_upstream_result(self):
        """Re-emit upstream evidence persisted in package res/.

        No synthesis: missing or non-passed content fails the test.
        """
        from conan.errors import ConanException

        cands = []
        try:
            for _, dep in self.dependencies.items():
                try:
                    cands.append(os.path.join(dep.package_folder, "res",
                                              "upstream_test_result.json"))
                except Exception:
                    continue
        except Exception:
            pass
        try:
            ref_name = self.tested_reference_str.split("/")[0]
            dep = self.dependencies[ref_name]
            cands.append(os.path.join(dep.package_folder, "res",
                                      "upstream_test_result.json"))
        except Exception:
            pass
        for cand in cands:
            if cand and os.path.isfile(cand):
                try:
                    with open(cand, encoding="utf-8") as f:
                        data = json.load(f)
                    line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data)
                    self.output.info(line)
                    print(line)
                    if data.get("status") != "passed":
                        raise ConanException(
                            "upstream tests not passed: {}".format(data))
                    discovered = int(data.get("discovered", 0))
                    executed = int(data.get("executed", 0))
                    passed = int(data.get("passed", 0))
                    if discovered <= 0 or executed != discovered or passed != discovered:
                        raise ConanException(
                            "upstream tests incomplete: discovered={} executed={} passed={}".format(
                                discovered, executed, passed))
                    if int(data.get("failed", 0)) != 0 or int(data.get("skipped", 0)) != 0:
                        raise ConanException(
                            "upstream tests have failures/skips: {}".format(data))
                    self.output.info("re-emitted upstream result from {}".format(cand))
                    return
                except ConanException:
                    raise
                except Exception as e:
                    raise ConanException("HMBS upstream re-emit failed: {}".format(e))
        raise ConanException(
            "upstream_test_result.json not found in package res/ -- "
            "build() may have been skipped without persistence")

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: build verified, runtime test skipped")
            self._reemit_upstream_result()
            return
        test_bin = None
        cands = [
            os.path.join(self.source_folder, "test_libfdisk"),
            os.path.join(self.build_folder, "test_libfdisk"),
        ]
        # Recipe sets bindirs=[] (library view, no executables shipped), so
        # self.cpp.build.bindir raises ConanException when accessed. Only
        # probe it when the property is actually defined.
        try:
            _bindir = self.cpp.build.bindir
        except Exception:
            _bindir = None
        if _bindir:
            cands.append(os.path.join(_bindir, "test_libfdisk"))
        for cand in cands:
            if cand and os.path.isfile(cand):
                test_bin = cand
                break
        if test_bin is None:
            # Fallback: search build folder.
            for root, _dirs, files in os.walk(self.build_folder):
                if "test_libfdisk" in files:
                    test_bin = os.path.join(root, "test_libfdisk")
                    break
        if test_bin is None or not os.path.isfile(test_bin):
            raise Exception("test_libfdisk binary not found")
        # OHOS executables need signing + staging to an executable mount.
        runtime_dir = None
        executable = test_bin
        try:
            if str(self.settings.os) == "OHOS":
                import tempfile
                runtime_dir = tempfile.mkdtemp(
                    prefix="libfdisk-test-", dir="/data/storage/el2/base/cache"
                )
                staged = os.path.join(runtime_dir, "test_libfdisk")
                shutil.copy2(test_bin, staged)
                self._sign_ohos_elf(staged)
                executable = staged
            try:
                proc = subprocess.run(
                    [executable],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=120,
                    universal_newlines=True,
                )
                out = proc.stdout or ""
                for line in out.strip().splitlines()[-12:]:
                    self.output.info("test_libfdisk: {}".format(line))
                # Deterministic count: CHECK lines emitted by the binary.
                passed_lines = sum(
                    1 for l in out.splitlines() if l.startswith("PASS: ")
                )
                fail_lines = sum(
                    1 for l in out.splitlines() if l.startswith("FAIL: ")
                )
                if proc.returncode == 0 and passed_lines == TEST_CHECKS and fail_lines == 0:
                    marker = {
                        "executed": True,
                        "passed": True,
                        "command": "test_libfdisk",
                        "discovered": TEST_CHECKS,
                        "passedCount": TEST_CHECKS,
                    }
                    line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
                    self.output.info(line)
                    print(line)
                else:
                    marker = {
                        "executed": True,
                        "passed": False,
                        "command": "test_libfdisk",
                        "discovered": TEST_CHECKS,
                        "passedCount": passed_lines,
                    }
                    line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
                    self.output.info(line)
                    print(line)
                    try:
                        self._reemit_upstream_result()
                    except Exception as e:
                        self.output.warning("upstream re-emit failed: {}".format(e))
                    raise Exception(
                        "test_libfdisk failed: rc={} passed {}/{} lines".format(
                            proc.returncode, passed_lines, TEST_CHECKS
                        )
                    )
            except Exception:
                # Ensure failure marker path also emits before raising.
                raise
            self._reemit_upstream_result()
        finally:
            if runtime_dir is not None:
                shutil.rmtree(runtime_dir, ignore_errors=True)

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise Exception("required OHOS signing tools are missing")
        temporary = "{}.signed".format(path)
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise Exception("signed consumer has invalid .codesign: {}".format(path))
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)
