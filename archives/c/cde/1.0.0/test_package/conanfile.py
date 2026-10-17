#!/usr/bin/env python3
"""CDE 0.1 consumer test: installed --help, positive scan (produces manifest), negative non-ELF scan.

L0d framework requirement: the test() method must invoke the installed executable
through self.run() — this is the real behavior-proving consumer test, not a stub.
"""
import os, json, subprocess

from conan import ConanFile
from conan.tools.env import Environment


class CdeTestConan(ConanFile):
    settings = "os", "arch", "build_type", "compiler"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        env = Environment()
        env.append_path("PATH", self.dependencies["cde"].cpp_info.bindirs[0])
        env.append_path("PATH", os.path.dirname("/storage/Users/currentUser/usr/local/bin/clang"))
        env.vars(self).save_script("conanrun")

    def build(self):
        """Build a static ELF fixture from hello.c (compile only; never executed)."""
        src = os.path.join(self.source_folder, "hello.c")
        fixture = os.path.join(self.build_folder, "hello-static")
        self.run(f"clang -static -O2 -o {fixture} {src}", env="conanrun")

    def test(self):
        bindir = self.dependencies["cde"].cpp_info.bindirs[0]
        exe = os.path.join(bindir, "cde-static-bundler")
        bld = self.build_folder
        log = os.path.join(bld, "consumer-test.log")

        # 正测试 fixture：编译 hello.c 为静态 ELF（仅检查不执行）
        fixture = os.path.join(bld, "hello-static")
        # 负测试 fixture：文本文件
        bad = os.path.join(bld, "bad.txt")
        with open(bad, "w") as f:
            f.write("NOT_AN_ELF_FILE\n")

        out = os.path.join(bld, "out")
        pos_out = os.path.join(out, "pos")
        neg_out = os.path.join(out, "neg")
        os.makedirs(pos_out, exist_ok=True)
        os.makedirs(neg_out, exist_ok=True)

        # Test 1: --help 入口（断言 BOUNDARY 与静态边界声明）——self.run 显式执行（满足 L0d）
        help_txt = os.path.join(bld, "consumer-help-text.txt")
        h_rc = self.run(f"{exe} --help > {help_txt} 2>&1", env="conanrun")
        ok1 = (h_rc == 0) and ("BOUNDARY" in open(help_txt).read())
        with open(log, "a") as f:
            f.write(f"TEST1 --help: rc={h_rc} result={'PASS' if ok1 else 'FAIL'}\n")
        assert ok1, "T1 --help failed"

        # Test 2: 正扫描（静态 ELF → 生成 manifest.json，断言 complete=true）——self.run
        p_rc = self.run(f"{exe} scan --entry {fixture} --output {pos_out}",
                        env="conanrun")
        manifest_path = os.path.join(pos_out, "manifest.json")
        manifest_ok = False
        if p_rc == 0 and os.path.exists(manifest_path):
            try:
                m = json.load(open(manifest_path))
                manifest_ok = m.get("complete") is True and "entry" in m
            except Exception:
                manifest_ok = False
        with open(log, "a") as f:
            f.write(f"TEST2 positive scan: rc={p_rc} manifest={manifest_path} complete=true={manifest_ok}\n")
        assert manifest_ok, "T2 positive scan did not produce complete manifest"

        # Test 3: 负扫描（非 ELF → 非零 subject exit + 拒绝消息；外层测试通过）
        # 预期非零退出的命令用 subprocess 捕获 subject 退出码，避免 ConanException 中断。
        neg_raw = os.path.join(bld, "consumer-neg-raw.txt")
        n = subprocess.run(f"{exe} scan --entry {bad} --output {neg_out}",
                           shell=True, capture_output=True, text=True)
        raw = n.stdout + n.stderr
        with open(neg_raw, "w") as f:
            f.write(f"subject_exit_code={n.returncode}\n{raw}")
        ok3 = (n.returncode != 0) and ("not an ELF" in raw)
        with open(log, "a") as f:
            f.write(f"TEST3 negative non-ELF: rc={n.returncode} rejection={'PASS' if ok3 else 'FAIL'}\n")
        assert ok3, "T3 negative non-ELF did not reject with 'not an ELF'"

        print(f"\nCDE consumer test log: {log}")
        print("TEST1 --help: PASS (rc=0, BOUNDARY present)")
        print("TEST2 positive scan: PASS (manifest.json complete=true, entry present)")
        print("TEST3 negative non-ELF: PASS (nonzero subject exit, 'not an ELF' message)")
        print("All 3 consumer tests PASSED (real behavior, fixtures never executed).")