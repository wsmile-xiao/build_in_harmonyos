#!/usr/bin/env python3
"""test_package — piler (PILER 1.0) 消费者侧验证 / Conan L1 测试。

两类用例：
  1) 功能回归（16 项）：由 test.sh 执行，覆盖上游 User Guide 记载的全部
     命令行工作流，即 `main.cpp` 分派的每个子命令
     （-trs / -trs2fasta / -tr / -tan / -tanmotif2fasta / -cons /
       -annot / -annotedge / -crisp / -help / -version）+ 2 项负向用例。
     上游 tarball 不含任何自动化测试与样例数据，故由本套件补全。
  2) OHOS 适配专项（2 项）：本文件内纯 Python stdlib 解析 ELF
     （不依赖 readelf），验证鸿蒙适配后的产物属性：
     - ohos_elf_hardening          : PIE(ET_DYN) + GNU_RELRO/BIND_NOW + NX
     - ohos_selfcontained_no_libcxx: DT_NEEDED=0，且在清空 LD_LIBRARY_PATH
                                     时仍可执行（OHOS CLI 不保证共享 libc++）

任一用例失败 → ConanException（CI L1 失败）。
"""
import json
import os
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run

# ── ELF 常量 ────────────────────────────────────────────────────────────────
PT_DYNAMIC = 2
PT_GNU_STACK = 0x6474E551
PT_GNU_RELRO = 0x6474E552
PF_X = 0x1
DT_NEEDED = 1
DT_FLAGS = 30
DT_FLAGS_1 = 0x6FFFFFFB
DF_BIND_NOW = 0x8
DF_1_NOW = 0x1
ET_DYN = 3


def _elf_facts(path):
    """解析 ELF64 头/程序头/动态段，返回硬化相关事实（纯 stdlib，无外部工具）。"""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF":
        raise ConanException("%s is not an ELF file" % path)
    if data[4] != 2:
        raise ConanException("%s is not ELF64 (class=%d)" % (path, data[4]))
    (e_type,) = struct.unpack_from("<H", data, 16)
    (e_phoff,) = struct.unpack_from("<Q", data, 32)
    (e_phentsize,) = struct.unpack_from("<H", data, 54)
    (e_phnum,) = struct.unpack_from("<H", data, 56)

    facts = {"e_type": e_type, "relro": False, "nx": None, "needed": 0,
             "bind_now": False, "dynamic": False}
    dyn_off = None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, p_flags, p_offset = struct.unpack_from("<IIQ", data, off)
        if p_type == PT_GNU_RELRO:
            facts["relro"] = True
        elif p_type == PT_GNU_STACK:
            facts["nx"] = (p_flags & PF_X) == 0
        elif p_type == PT_DYNAMIC:
            facts["dynamic"] = True
            dyn_off = p_offset
    if dyn_off is not None:
        off = dyn_off
        while True:
            d_tag, d_val = struct.unpack_from("<qQ", data, off)
            off += 16
            if d_tag == 0:
                break
            if d_tag == DT_NEEDED:
                facts["needed"] += 1
            elif d_tag == DT_FLAGS and (d_val & DF_BIND_NOW):
                facts["bind_now"] = True
            elif d_tag == DT_FLAGS_1 and (d_val & DF_1_NOW):
                facts["bind_now"] = True
    return facts


class PilerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ── 路径辅助 ────────────────────────────────────────────────────────────
    def _test_root(self):
        cands = [os.path.dirname(os.path.abspath(__file__)),
                 getattr(self, "recipe_folder", ""),
                 getattr(self, "build_folder", ""),
                 getattr(self, "source_folder", "")]
        for c in cands:
            if c and os.path.isfile(os.path.join(c, "test.sh")):
                return c
        raise ConanException("cannot locate test.sh (looked in: %s)" % cands)

    def _bash(self):
        for c in (os.environ.get("CONFIG_SHELL"), "/data/service/hnp/bin/bash"):
            if c and os.path.isfile(c):
                return c
        return "bash"

    def _piler_bin(self):
        folder = self.dependencies[self.tested_reference_str].package_folder
        exe = os.path.join(folder, "bin", "piler2")
        if not os.path.isfile(exe):
            found = []
            for root, _dirs, files in os.walk(folder):
                for f in files:
                    if f == "piler2":
                        found.append(os.path.join(root, f))
            if not found:
                raise ConanException("piler2 not found under %s" % folder)
            exe = found[0]
        return exe

    def _make_outdir(self):
        """临时输出目录（不落在 archives/ 源码树内，避免污染 PR 文件集）。"""
        import tempfile
        base = os.environ.get("TMPDIR") or os.environ.get("TMP") or tempfile.gettempdir()
        try:
            return tempfile.mkdtemp(prefix="piler-test-", dir=base)
        except OSError:
            return tempfile.mkdtemp(prefix="piler-test-")

    # ── 测试入口 ────────────────────────────────────────────────────────────
    def test(self):
        root = self._test_root()
        exe = self._piler_bin()
        outdir = self._make_outdir()
        log = os.path.join(outdir, "functional-suite.log")
        rcfile = os.path.join(outdir, "functional-suite.rc")

        # OHOS 无 /bin/sh（mksh 不能执行 ELF），显式用 bash 包装；
        # env="conanrun" 由 VirtualRunEnv 把包的 bin/ 注入 PATH，
        # 使 test.sh 里的 `piler2` 解析到被测包产物。
        cmd = ('"%s" "%s" "%s" "%s" > "%s" 2>&1; echo $? > "%s"'
               % (self._bash(), os.path.join(root, "test.sh"),
                  os.path.join(root, "data"), outdir, log, rcfile))
        self.run(cmd, cwd=root, env="conanrun", ignore_errors=True)

        if os.path.isfile(log):
            with open(log, errors="replace") as fh:
                self.output.info("--- test.sh output ---\n" + fh.read())
        if os.path.isfile(rcfile):
            with open(rcfile) as fh:
                try:
                    suite_rc = int(fh.read().strip())
                except ValueError:
                    suite_rc = 1
        else:
            suite_rc = 1

        cases = self._parse_summary(outdir, suite_rc)
        cases += self._run_ohos_cases(exe, outdir)
        self._report(cases, outdir)

    # 1) 功能回归：读取 test.sh 产出的 SUMMARY.tsv
    def _parse_summary(self, outdir, suite_rc):
        cases = []
        summary = os.path.join(outdir, "SUMMARY.tsv")
        if os.path.isfile(summary):
            with open(summary, errors="replace") as fh:
                for line in fh:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) >= 2:
                        cases.append({"name": parts[0],
                                      "status": parts[1].strip().lower(),
                                      "detail": parts[2] if len(parts) > 2 else "",
                                      "log": os.path.join(outdir, parts[0] + ".log")})
        if not cases:
            cases.append({"name": "functional_suite", "status": "fail",
                          "detail": "test.sh produced no SUMMARY.tsv (rc=%s)" % suite_rc,
                          "log": os.path.join(outdir, "functional-suite.log")})
        return cases

    # 2) OHOS 适配专项
    def _run_ohos_cases(self, exe, outdir):
        cases = []
        facts = _elf_facts(exe)
        detail = ("e_type=%s PIE=%s RELRO=%s BIND_NOW=%s NX=%s DT_NEEDED=%d"
                  % (facts["e_type"], facts["e_type"] == ET_DYN, facts["relro"],
                     facts["bind_now"], facts["nx"], facts["needed"]))
        facts_log = os.path.join(outdir, "ohos_elf_facts.json")
        with open(facts_log, "w") as fh:
            json.dump(facts, fh, indent=1, sort_keys=True)

        hardening = (facts["e_type"] == ET_DYN and facts["relro"]
                     and facts["bind_now"] and facts["nx"] is True)
        cases.append({
            "name": "ohos_elf_hardening",
            "status": "pass" if hardening else "fail",
            "detail": ("PIE + full RELRO + NX" if hardening
                       else "hardening incomplete: " + detail),
            "log": facts_log,
        })

        if not can_run(self):
            cases.append({"name": "ohos_selfcontained_no_libcxx",
                          "status": "skip",
                          "detail": "cross-building: binary cannot run here",
                          "log": facts_log})
            return cases
        env = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
        proc = subprocess.run([exe, "-version"], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=120,
                              env=env)
        ran = proc.returncode == 0 and "PILER v1.0" in (proc.stdout or "")
        ok = facts["needed"] == 0 and ran
        log = os.path.join(outdir, "ohos_selfcontained.log")
        with open(log, "w") as fh:
            fh.write("$ env -u LD_LIBRARY_PATH %s -version\nrc=%d\n%s"
                     % (exe, proc.returncode, proc.stdout or ""))
        cases.append({
            "name": "ohos_selfcontained_no_libcxx",
            "status": "pass" if ok else "fail",
            "detail": ("DT_NEEDED=0 and runs without LD_LIBRARY_PATH" if ok else
                       "DT_NEEDED=%d, ran=%s (rc=%s)"
                       % (facts["needed"], ran, proc.returncode)),
            "log": log,
        })
        return cases

    # 3) 汇总 + 机器可读结果
    def _report(self, cases, outdir):
        counts = {"pass": 0, "fail": 0, "skip": 0}
        for c in cases:
            counts[c["status"]] = counts.get(c["status"], 0) + 1
        result = {
            "status": "passed" if counts["fail"] == 0 else "failed",
            "framework": "custom-bash-suite + stdlib-elf-probe",
            "command": "test.sh <data> <out> ; ELF probe on bin/piler2",
            "discovered": len(cases),
            "executed": counts["pass"] + counts["fail"],
            "passed": counts["pass"],
            "failed": counts["fail"],
            "skipped": counts["skip"],
            "ohos_specific": [c["name"] for c in cases
                              if c["name"].startswith("ohos_")],
            "cases": cases,
        }
        with open(os.path.join(outdir, "piler-test-result.json"), "w") as fh:
            json.dump(result, fh, indent=1, ensure_ascii=False)
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        print(line)
        self.output.info(line)
        if counts["fail"]:
            raise ConanException(
                "piler test_package failed: %d/%d cases failed: %s"
                % (counts["fail"], len(cases),
                   [c["name"] for c in cases if c["status"] == "fail"]))
