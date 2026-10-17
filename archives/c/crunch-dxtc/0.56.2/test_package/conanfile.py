#!/usr/bin/env python3
"""Conan test_package — crunch-dxtc 0.56.2.

Consumer-side verification (R34), two halves:
- library: compile + run test_crn.cpp (8 real libcrn API checks: string
  helpers, format queries, one-block DXT1 compress/decompress round-trip,
  TGA fixture generation).
- tool: run the packaged `crunch` binary (`--help`, plus a real
  TGA -> CRN conversion of the fixture written by test_crn).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class CrunchDxtcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def _ensure_writable_tmp(self):
        # 真机 /tmp 只读：复用 HMBS 注入的可写 TMPDIR，透传给编译与运行子进程。
        cand = []
        hmbs_tmp = os.environ.get("HMBS_TMPDIR", "")
        if hmbs_tmp:
            cand.append(hmbs_tmp)
        caps = os.environ.get("HMBS_PLATFORM_CAPABILITIES", "")
        if caps:
            try:
                cand.append(json.loads(caps).get("tmpdir", ""))
            except Exception:
                pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key, "")
            if val:
                cand.append(val)
        fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
        if fallback:
            cand.append(fallback)
        for d in cand:
            if not d:
                continue
            try:
                os.makedirs(d, exist_ok=True)
                if os.path.isdir(d):
                    for key in ("TMPDIR", "TMP", "TEMP"):
                        os.environ[key] = d
                    return d
            except Exception:
                continue
        return os.environ.get("TMPDIR", "")

    def _existing_file(self, p):
        return bool(p) and os.path.isfile(p) and os.access(p, os.X_OK)

    def _resolve_cxx(self):
        # 与主配方 _find_compiler 同策略的存在性校验：profile 的陈旧绝对
        # 路径（如 /data/service/hnp/bin/clang++ 在预检沙箱不存在）不可
        # 直接使用，否则 sh 报 inaccessible or not found (127)。优先用
        # 存在且可执行的 profile 值，否则回退到 PATH 中的可用 clang++。
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        prof = comp.get("cpp", "")
        if self._existing_file(prof):
            return prof
        if prof and os.path.isfile(prof):
            return prof
        for cand in (shutil.which("clang++"), shutil.which("c++"),
                     shutil.which("clang"), shutil.which("cc")):
            if cand and os.path.isfile(cand):
                return cand
        import glob
        for pat in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang++",
                    "/data/service/hnp/*/llvm/bin/clang++"):
            try:
                hits = sorted(glob.glob(pat))
            except Exception:
                continue
            for h in hits:
                if os.path.isfile(h):
                    return h
        return prof or "clang++"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        self._ensure_writable_tmp()
        dep = self.dependencies["crunch-dxtc"].cpp_info
        # R34/L1e guard: make sure we link the packaged libcrn, not anything
        # else that might shadow it on the build machine.
        for p in dep.includedirs:
            if not os.path.isdir(p):
                raise ConanException(f"crunch-dxtc package include dir missing: {p}")
        libdir = dep.libdirs[0]
        if not os.path.isdir(libdir):
            raise ConanException(f"crunch-dxtc package lib dir missing: {libdir}")
        inc = " ".join("-I" + p for p in dep.includedirs)
        # R33: compiler comes from Conan conf with existence check; stale
        # absolute paths fall back to PATH clang++ (主配方 _find_compiler
        # 同策略，经验1适配到直接编译模式）。
        cxx = self._resolve_cxx()
        self.output.info("test_package CXX=%s" % cxx)
        self.run(f'"{cxx}" test_crn.cpp -o test_crn -std=c++11 {inc} -L{libdir} -lcrn -pthread')

    def test(self):
        self._ensure_writable_tmp()
        if cross_building(self):
            self.output.info("cross-building: compile+link only")
            return
        discovered = 10  # 8 libcrn checks + crunch --help + TGA->CRN conversion
        passed = 0
        dep = self.dependencies["crunch-dxtc"]
        bindir = dep.cpp_info.bindirs[0]
        if not os.path.isabs(bindir):
            bindir = os.path.join(dep.package_folder, bindir)
        crunch = os.path.join(bindir, "crunch")
        try:
            # 8 libcrn API checks; exit 0 only if all of them ran green.
            # The binary also writes the test_input.tga fixture for step 3.
            self.run("./test_crn", env="conanrun")
            passed = 8
            # The packaged CLI tool reports its help text.
            self.run(f"{crunch} --help", env="conanrun")
            passed = 9
            # A real end-to-end conversion with the packaged tool.
            self.run(
                f"{crunch} -noTitle -nostats -noprogress "
                f"-file test_input.tga -out test_output.crn",
                env="conanrun",
            )
            out_path = os.path.join(self.build_folder, "test_output.crn")
            if not os.path.isfile(out_path) or os.path.getsize(out_path) == 0:
                raise ConanException("crunch produced an empty test_output.crn")
            passed = 10
        except Exception as exc:
            self.output.error(f"test_package failed: {exc}")

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "./test_crn + crunch --help + crunch TGA->CRN conversion",
            "discovered": discovered,
            "passedCount": passed,
        }
        tp_marker = f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}"
        self.output.info(tp_marker)
        print(tp_marker, flush=True)
        # 重发上游实测结果（双通道），内容源自包内持久化文件并校验合法性。
        try:
            pkg_folder = self.dependencies["crunch-dxtc"].package_folder
            uj_path = os.path.join(pkg_folder, "hmbs_upstream_test_result.json")
            if os.path.isfile(uj_path):
                with open(uj_path, "r", encoding="utf-8") as f:
                    udata = json.load(f)
                # 合法性校验：字段齐全且口径一致（executed>0、无失败/跳过）。
                ok = (
                    isinstance(udata, dict)
                    and udata.get("status") == "passed"
                    and isinstance(udata.get("discovered"), int) and udata["discovered"] > 0
                    and udata.get("executed") == udata.get("discovered")
                    and udata.get("failed", 0) == 0
                    and udata.get("skipped", 0) == 0
                    and udata.get("passed") == udata.get("executed")
                )
                if ok:
                    up_marker = f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(udata)}"
                    self.output.info(up_marker)
                    print(up_marker, flush=True)
                else:
                    self.output.warning(f"upstream result json invalid, skip re-emit: {udata}")
            else:
                self.output.warning(f"upstream result json missing: {uj_path}")
        except Exception as exc2:
            self.output.warning(f"re-emit upstream result failed: {exc2}")

        if passed != discovered:
            raise ConanException("test_package checks failed")
