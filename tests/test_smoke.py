#!/usr/bin/env python3
"""tests/test_smoke.py — 核心模块冒烟测试（v12.6 L5）

防回归底线：历史 P0（submit 路径静默坏）、编号碰撞、锁竞态等
一旦复发当场暴露。纯标准库 unittest，无外部依赖。

运行: python3 tests/test_smoke.py 或 ohc-run.py selftest
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))


class TestTaxonomy(unittest.TestCase):
    def test_normalize_variants(self):
        from ohc.kb_taxonomy import normalize_category as n
        self.assertEqual(n("ssl|asm")[0], "asm, security")
        self.assertEqual(n("platform-limitation")[0], "platform, limitation")
        self.assertEqual(n("autotools-config")[0], "autotools, configure")
        # 幂等
        self.assertEqual(n(n("ssl|asm")[0])[0], n("ssl|asm")[0])

    def test_no_alias_cycles(self):
        from ohc.kb_taxonomy import normalize_category
        for tok in ("llvm", "relocatable", "patch", "memory", "shell"):
            with self.subTest(tok=tok):
                norm, _ = normalize_category(tok)
                self.assertTrue(norm)


class TestEngineRegression(unittest.TestCase):
    """已知错误签名 → 期望命中（回归集）。"""

    CASES = [
        ("ld.lld: error: undefined symbol: jsimd_can_", "E100"),
        ("ln: failed to create symbolic link", None),  # 至少命中
    ]

    def test_known_signatures(self):
        from ohc.engine import run_engine
        for err, expect in self.CASES:
            with self.subTest(err=err[:40]):
                r = run_engine(err)
                self.assertTrue(r.matched, f"应命中: {err[:60]}")
                if expect:
                    self.assertEqual(r.match_id, expect)


class TestPrescan(unittest.TestCase):
    def test_scan_finds_known_risks(self):
        from ohc.pre_scan import PreScanner
        rules = str(REPO / "knowledge" / "graph" / "pre-scan-rules.yaml")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "Makefile").write_text("all:\n\tln -s foo bar\n")
            (t / "run.sh").write_text("#!/bin/bash\necho hi\n")
            (t / "test.c").write_text(
                '#include <dlfcn.h>\nvoid *h = dlopen("/usr/lib/libfoo.so.1");\n')
            sc = PreScanner(str(t), rules, writeback=False)
            rep = sc.scan()
        ids = {f["rule_id"] for f in rep["findings"]}
        self.assertIn("PSCAN-HMDFS-001", ids)
        self.assertIn("PSCAN-SHELL-002", ids)
        self.assertIn("PSCAN-LINK-001", ids)
        kb_hits = {i for i in ids if i.startswith("PSCAN-KB-")}
        self.assertTrue(kb_hits, "KB 动态派生规则应命中")
        self.assertGreaterEqual(rep.get("kb_rule_count", 0), 3)

    def test_writeback_increments(self):
        from ohc.pre_scan import PreScanner
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            rules = Path(td) / "rules.yaml"
            rules.write_text(
                "rules:\n  - id: PSCAN-T-001\n    severity: low\n"
                "    pattern: 'FOOMARKER'\n    scope_globs: ['*.txt']\n    hit_count: 0\n")
            (t / "a.txt").write_text("hello FOOMARKER\n")
            PreScanner(str(t), str(rules), kb_dir=None).scan()
            PreScanner(str(t), str(rules), kb_dir=None).scan()
            content = rules.read_text()
        self.assertIn("hit_count: 2", content)


class TestBuildTimeout(unittest.TestCase):
    def test_effective_timeout_lookup(self):
        """CI 同源超时查找 + env 覆盖优先级（用仓库真实配置）。"""
        from ohc.build_timeout import effective_timeout, load_entries, local_w3_timeout
        entries = load_entries()
        self.assertGreater(len(entries), 0, "build_timeouts.txt 应有条目")
        ref, secs, _ = entries[0]
        name, ver = ref.rsplit("/", 1)
        self.assertEqual(effective_timeout(name, ver), secs)
        # 未知包回落默认；OHC_W3_TIMEOUT env 覆盖最优先
        import os
        os.environ["OHC_W3_TIMEOUT"] = "123"
        try:
            self.assertEqual(local_w3_timeout("no", "such"), 123)
        finally:
            del os.environ["OHC_W3_TIMEOUT"]


class TestHandoffLock(unittest.TestCase):
    def test_concurrent_updates_no_loss(self):
        """两进程并发各写 30 次，最终 60 个键全部落盘（锁生效）。"""
        code = (
            "import sys; sys.path.insert(0, %r)\n"
            "from ohc.handoff import update_build_status\n"
            "for i in range(30):\n"
            "    update_build_status('sw%%d' %% i, '1.0', 'running', project_dir=%r)\n"
        ) % (str(REPO / "scripts"), "")
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ, OHC_PROJECT_DIR=td)
            # 直接用仓库 project_dir 会写真状态文件——用临时 repo 结构
            status = Path(td) / ".build-status.json"
            status.write_text("{}")
            code = (
                "import sys; sys.path.insert(0, %r)\n"
                "from ohc.handoff import _save_status_locked\n"
                "import os\n"
                "def mut(st): st['sw%%d_%%s' %% (i, os.environ['W'])] = 1\n"
                "for i in range(30):\n"
                "    _save_status_locked(%r, None, mutator=mut)\n"
            ) % (str(REPO / "scripts"), str(status))
            ps = [subprocess.Popen([sys.executable, "-c", code], env={**env, "W": w})
                  for w in ("A", "B")]
            for p in ps:
                p.wait(timeout=60)
            data = json.loads(status.read_text()) if False else None
            import json as _json
            data = _json.loads(status.read_text())
        self.assertEqual(len(data), 60, f"应 60 键，实际 {len(data)}（锁失效丢更新）")


class TestNoP0Regression(unittest.TestCase):
    def test_submit_paths(self):
        """防 P0 回归：submit 相关代码不得再引用不存在目录。"""
        src = (REPO / "scripts" / "ohc" / "submission.py").read_text(encoding="utf-8")
        self.assertNotIn('"knowledge/graph/draft"', src)
        self.assertIn("knowledge/drafts/", src)

    def test_rule_ids_unique(self):
        rp = REPO / "knowledge" / "graph" / "pre-scan-rules.yaml"
        ids = re.findall(r"^\s*-\s*id:\s*(\S+)", rp.read_text(encoding="utf-8"), re.M)
        self.assertEqual(len(ids), len(set(ids)), "规则 ID 重复")


class TestEditorAudit202609(unittest.TestCase):
    """v12.17 主编反馈审计批次的防回归（SKILL_FEEDBACK 20 份核验后落地）。"""

    def test_commit_nochange_wordings(self):
        """git 无变更的三种实测措辞都必须被 submission 容错识别。

        git 2.45 实测（2026-09-01）：
          干净树: "nothing to commit, working tree clean"
          仅未跟踪文件: "nothing added to commit but untracked files present"
          有未暂存修改: "no changes added to commit"
        反馈（websocketpp）引用的 "no changes added to commit" 并非
        未跟踪文件场景的实际措辞——以实测为准。
        """
        src = (REPO / "scripts" / "ohc" / "submission.py").read_text(encoding="utf-8")
        for wording in ("nothing to commit", "nothing added to commit",
                        "no changes added to commit"):
            self.assertIn(wording, src, f"commit 容错缺少措辞: {wording}")

    def test_ghfast_bak_guard(self):
        """陈旧 .bak 清理不覆盖；崩溃残留（当前含注入）才回滚。"""
        from ohc.conan_verify import _recover_ghfast_bak
        with tempfile.TemporaryDirectory() as d:
            cd = Path(d) / "conandata.yml"
            bak = Path(d) / "conandata.yml.ghfast-bak"
            # 场景 A: 陈旧 .bak（当前无注入）→ 清理且不覆盖
            cd.write_text("sources:\n  url: https://github.com/x/y.tar.gz\n")
            bak.write_text("sources:\n  url: https://OLD-STALE/v0.tar.gz\n")
            _recover_ghfast_bak(cd, bak)
            self.assertFalse(bak.exists(), "陈旧 .bak 应被清理")
            self.assertNotIn("OLD-STALE", cd.read_text(), "不应被陈旧 .bak 覆盖")
            # 场景 B: 崩溃残留（当前含注入）→ 回滚
            cd.write_text("sources:\n  url: https://ghfast.top/https://github.com/x/y.tar.gz\n")
            bak.write_text("sources:\n  url: https://github.com/x/y.tar.gz\n")
            _recover_ghfast_bak(cd, bak)
            self.assertNotIn("ghfast.top", cd.read_text(), "注入应被回滚")
            self.assertFalse(bak.exists())

    def test_preflight_accepts_str_repo_dir(self):
        """run_preflight 接受 str 输入（gitcode_pr._git_toplevel 返回 str）。

        修复前 str/str TypeError 被外层 except 捕获为 PF0 环境闸故障，
        迫使协作者 --no-preflight 绕行（3 份反馈）。
        """
        import shutil
        git = shutil.which("git")
        if not git:
            self.skipTest("git 不可用")
        import ohc.preflight as pf
        real_run = subprocess.run

        def git_abs_run(*a, **kw):
            cmd = a[0] if a else kw.get("args")
            if isinstance(cmd, list) and cmd and cmd[0] == "git":
                new_cmd = [git] + cmd[1:]
                if a:
                    a = (new_cmd,) + a[1:]
                else:
                    kw["args"] = new_cmd
            return real_run(*a, **kw)

        with tempfile.TemporaryDirectory() as d:
            subprocess.run([git, "init", "-q", d], check=True,
                           capture_output=True)
            # 直接调用：str 输入不得抛 TypeError
            ok, probs = pf.run_preflight(d, "main", "HEAD")
            self.assertIsInstance(ok, bool)
            self.assertIsInstance(probs, list)

    def test_writeback_submit_state(self):
        """create-pr 成功后回写 .submit-state.json（保留既有字段）。"""
        import shutil
        git = shutil.which("git")
        if not git:
            self.skipTest("git 不可用")
        from gitcode_pr import _writeback_submit_state
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([git, "init", "-q", d], check=True,
                           capture_output=True)
            real_run = subprocess.run

            def git_abs_run(*a, **kw):
                cmd = a[0] if a else kw.get("args")
                if isinstance(cmd, list) and cmd and cmd[0] == "git":
                    new_cmd = [git, "-C", d] + cmd[1:]
                    if a:
                        a = (new_cmd,) + a[1:]
                    else:
                        kw["args"] = new_cmd
                return real_run(*a, **kw)

            state_file = Path(d) / ".submit-state.json"
            state_file.write_text('{"software": "demo", "pr_number": null}',
                                  encoding="utf-8")
            import gitcode_pr as gp
            orig = gp.subprocess.run
            gp.subprocess.run = git_abs_run
            try:
                _writeback_submit_state({
                    "number": 4242,
                    "html_url": "https://gitcode.com/o/r/-/merge_requests/4242",
                    "head": {"ref": "feat/demo-1.0"},
                })
            finally:
                gp.subprocess.run = orig
            import json
            state = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(state["pr_number"], 4242)
            self.assertEqual(state["software"], "demo", "既有字段必须保留")


if __name__ == "__main__":
    unittest.main(verbosity=2)
