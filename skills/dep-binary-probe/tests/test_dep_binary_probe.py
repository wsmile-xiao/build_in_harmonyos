#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dep-binary-probe 离线测试。

不访问网络、不依赖真实 conan：通过 tests/fake_conan.py 注入 stub，
覆盖三态判定（BINARY_OK / RECIPE_ONLY / RECIPE_MISSING）、通道故障
（REMOTE_ERROR）、源码兜底工具缺口（BUILD_TOOL_GAP）与退出码契约。

运行：
    python3 skills/dep-binary-probe/tests/test_dep_binary_probe.py
    python3 -m unittest discover -s skills/dep-binary-probe/tests -p "test_*.py"
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
SCRIPT = os.path.join(SKILL_DIR, "scripts", "dep_binary_probe.py")
SHIM = os.path.join(HERE, "fake_conan.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("dep_binary_probe", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe = _load_module()


class ProbeTestCase(unittest.TestCase):
    """为每个用例准备仓库内可写的临时工作目录（鸿蒙 PC 上 /tmp 常只读）。"""

    def setUp(self):
        self.work = tempfile.mkdtemp(prefix=".ohc-test-", dir=HERE)
        src_home = os.path.join(self.work, "src-conan-home")
        os.makedirs(src_home, exist_ok=True)
        with open(os.path.join(src_home, "settings.yml"), "w", encoding="utf-8") as fh:
            fh.write("os: [Linux, OHOS]\n")
        self.env = dict(os.environ)
        self.env["OHC_TMPDIR"] = self.work
        self.env["FAKE_CONAN_HOME"] = src_home

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def run_probe(self, args):
        cmd = [sys.executable, SCRIPT, "--conan", "%s %s" % (sys.executable, SHIM)]
        cmd += ["--timeout", "30"]
        cmd += args
        return subprocess.run(
            cmd,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_probe_json(self, args):
        proc = self.run_probe(["--json"] + args)
        payload = json.loads(proc.stdout.decode("utf-8"))
        return proc.returncode, payload


class TestClassify(ProbeTestCase):
    """classify_output：conan 输出 → 状态（纯函数，无副作用）。"""

    def test_missing_binary_is_recipe_only(self):
        text = (
            "ERROR: Missing binary: wayland/1.24.0:50c1715c9d6630244edc1e29caf86880dfcc7907\n"
            "ERROR: Missing prebuilt package for 'wayland/1.24.0'\n"
        )
        status, package_id, evidence = probe.classify_output(1, text)
        self.assertEqual(status, probe.RECIPE_ONLY)
        self.assertEqual(package_id, "50c1715c9d6630244edc1e29caf86880dfcc7907")
        self.assertIn("Missing binary", evidence)

    def test_recipe_missing(self):
        status, _, evidence = probe.classify_output(1, "ERROR: Unable to find package 'dssi/1.0.0'")
        self.assertEqual(status, probe.RECIPE_MISSING)
        self.assertIn("Unable to find package", evidence)

    def test_recipe_missing_real_wording(self):
        """实测形态：not resolved: Unable to find '<ref>' in remotes（并非 'Unable to find package'）。"""
        text = (
            "ERROR: Package 'dssi/1.0.0' not resolved: Unable to find 'dssi/1.0.0' in remotes. "
            "Required by 'cli'"
        )
        status, _, evidence = probe.classify_output(1, text)
        self.assertEqual(status, probe.RECIPE_MISSING)
        self.assertIn("in remotes", evidence)

    def test_recipe_missing_version_range_wording(self):
        """版本区间无候选（cmake/[>=3.18]）同属配方缺失，不能落到 UNKNOWN。"""
        text = (
            "ERROR: Package 'cmake/[>=3.18]' not resolved: Version range '>=3.18' from "
            "requirement 'cmake/[>=3.18]' required by 'None' could not be resolved. Required by 'cli'"
        )
        status, _, evidence = probe.classify_output(1, text)
        self.assertEqual(status, probe.RECIPE_MISSING)
        self.assertIn("could not be resolved", evidence)

    def test_remote_error_is_not_missing(self):
        text = "ERROR: Failed checking for binary 'x/1.0.0' in remote 'ohpcd': remote not available"
        status, _, _ = probe.classify_output(1, text)
        self.assertEqual(status, probe.REMOTE_ERROR)

    def test_cnb_search_api_limitation_is_remote_error(self):
        status, _, _ = probe.classify_output(1, "ERROR: system acceleration policy not enabled")
        self.assertEqual(status, probe.REMOTE_ERROR)

    def test_ok_and_unknown(self):
        self.assertEqual(probe.classify_output(0, "Downloading package revision...")[0], probe.BINARY_OK)
        status, _, evidence = probe.classify_output(1, "ERROR: 无法归类的古怪报错")
        self.assertEqual(status, probe.UNKNOWN)
        self.assertIn("古怪报错", evidence)

    def test_unexecutable_conan_is_env_error(self):
        """HMDFS 权限位问题会让裸名查找失败（rc=127 → OSError），必须归为环境错误。"""
        text = "OSError: [Errno 2] No such file or directory: 'conan' (conan install --requires=x/1.0.0)"
        status, _, evidence = probe.classify_output(127, text)
        self.assertEqual(status, probe.ENV_ERROR)
        self.assertIn("conan", evidence)

    def test_missing_binary_wins_over_remote_noise(self):
        """同一份日志里既提到远端又给出 Missing binary 时，判缺失（远端只是旁证）。"""
        text = (
            "ERROR: Failed checking for binary 'b/1.0.0:aaa' in remote 'conancenter': remote not available\n"
            "ERROR: Missing binary: b/1.0.0:50c1715c9d6630244edc1e29caf86880dfcc7907\n"
        )
        self.assertEqual(probe.classify_output(1, text)[0], probe.RECIPE_ONLY)


class TestHelpers(ProbeTestCase):

    def test_extract_requires(self):
        text = (
            "class Pkg(ConanFile):\n"
            "    requires = \"goodlib/1.0.0\"\n"
            "    def requirements(self):\n"
            "        self.requires(\"badlib/1.0.0\")\n"
            "        self.tool_requires(\"cmake/[>=3.18]\")\n"
            "        self.requires(\"goodlib/1.0.0\")\n"
        )
        self.assertEqual(
            probe.extract_requires(text),
            ["goodlib/1.0.0", "badlib/1.0.0", "cmake/[>=3.18]"],
        )

    def test_parse_json_payload_skips_log_noise(self):
        """profile 回显里的 {'c': '/path'} 也是花括号，不能当成 JSON 起点。"""
        text = (
            "======== Input profiles ========\n"
            "[conf]\ntools.build:compiler_executables={'c': '/data/service/hnp/bin/clang'}\n"
            "\n"
            '{"graph": {"nodes": {"0": {"ref": "cmake/4.4.3", "context": "build"}}}}'
        )
        data, err = probe.parse_json_payload(text)
        self.assertEqual(err, "")
        self.assertIn("graph", data)

    def test_parse_json_payload_tolerates_trailing_log(self):
        """JSON 之后混入日志行（stderr 合并）时仍应解析成功。"""
        text = '{"a": 1}\nWARN: something happened afterwards\n'
        data, err = probe.parse_json_payload(text)
        self.assertEqual(err, "")
        self.assertEqual(data, {"a": 1})

    def test_parse_json_payload_pretty_printed_after_brace_log(self):
        """真实场景：日志行含花括号 + JSON 首行是裸 "{"，必须按行偏移定位。"""
        text = (
            "======== Input profiles ========\n"
            "[conf]\ntools.build:compiler_executables={'c': '/data/service/hnp/bin/clang'}\n"
            "======== Computing dependency graph ========\n"
            "{\n    \"graph\": {\n        \"nodes\": {\"0\": {\"ref\": \"cmake/4.4.3\"}}\n    }\n}\n"
        )
        data, err = probe.parse_json_payload(text)
        self.assertEqual(err, "")
        self.assertEqual(data["graph"]["nodes"]["0"]["ref"], "cmake/4.4.3")

    def test_parse_json_payload_reports_error_for_pure_log(self):
        data, err = probe.parse_json_payload("ERROR: boom")
        self.assertIsNone(data)
        self.assertTrue(err)

    def test_summarize_and_evidence(self):
        results = [
            probe.ProbeResult("goodlib/1.0.0", probe.BINARY_OK, "rc=0"),
            probe.ProbeResult("badlib/1.0.0", probe.RECIPE_ONLY, "Missing binary: badlib/1.0.0:abc", "abc"),
            probe.ProbeResult("nosuchlib/1.0.0", probe.RECIPE_MISSING, "Unable to find package"),
        ]
        summary = probe.summarize(results, tool_gaps=["cmake/4.4.3"])
        self.assertEqual(summary["verdict"], "BLOCKED")
        self.assertEqual(summary["binary_missing"], ["badlib/1.0.0"])
        self.assertEqual(summary["recipe_missing"], ["nosuchlib/1.0.0"])
        text = probe.build_evidence(results, ["cmake/4.4.3"])
        self.assertIn("badlib/1.0.0", text)
        self.assertIn("cmake/4.4.3", text)

        summary["evidence"] = text
        cmd = probe.suggested_result_command("wev", "1.1.0", summary)
        self.assertIn("--status dependency_missing", cmd)
        self.assertIn("--missing \"badlib,nosuchlib\"", cmd)
        self.assertIn("--missing-evidence", cmd)

    def test_verdict_needs_review_only_for_channel_faults(self):
        summary = probe.summarize([probe.ProbeResult("flaky/1.0.0", probe.REMOTE_ERROR, "remote not available")])
        self.assertEqual(summary["verdict"], "NEEDS_REVIEW")
        self.assertEqual(summary["binary_missing"], [])

    def test_conan_cmd_resolves_absolute_path(self):
        """首段必须解析为绝对路径：鸿蒙上裸名经 PATH 查找会失败，绝对路径才可执行。"""
        ctx = type("Ctx", (), {"conan": "%s %s" % (sys.executable, SHIM)})()
        cmd = probe.conan_cmd(ctx)
        self.assertTrue(os.path.isabs(cmd[0]))
        self.assertEqual(cmd[1:], [SHIM])

    def test_resolve_work_root_falls_back_when_tmpdir_unwritable(self):
        original = dict(os.environ)
        try:
            os.environ["OHC_TMPDIR"] = "/proc/self/definitely-not-writable"
            os.environ["TMPDIR"] = "/proc/self/definitely-not-writable"
            root = probe.resolve_work_root()
        finally:
            os.environ.clear()
            os.environ.update(original)
        self.assertNotIn("/proc/self/definitely-not-writable", root)
        self.assertTrue(os.path.isdir(root))


class TestEndToEnd(ProbeTestCase):
    """端到端：脚本进程 + stub conan，验证分类、退出码与 JSON 契约。"""

    def test_all_ok_exit_zero(self):
        rc, payload = self.run_probe_json(["--requires", "goodlib/1.0.0"])
        self.assertEqual(rc, 0)
        self.assertEqual(payload["verdict"], "OK")
        self.assertEqual(payload["results"][0]["status"], probe.BINARY_OK)
        self.assertEqual(payload["suggested_result_command"], "")

    def test_blocked_exit_two_with_stop_loss_command(self):
        rc, payload = self.run_probe_json(
            [
                "--requires", "goodlib/1.0.0", "badlib/1.0.0", "nosuchlib/1.0.0",
                "--package", "wev", "--version", "1.1.0",
            ]
        )
        self.assertEqual(rc, 2)
        self.assertEqual(payload["verdict"], "BLOCKED")
        statuses = {item["ref"]: item["status"] for item in payload["results"]}
        self.assertEqual(statuses["goodlib/1.0.0"], probe.BINARY_OK)
        self.assertEqual(statuses["badlib/1.0.0"], probe.RECIPE_ONLY)
        self.assertEqual(statuses["nosuchlib/1.0.0"], probe.RECIPE_MISSING)
        self.assertIn("--status dependency_missing", payload["suggested_result_command"])
        self.assertIn("badlib", payload["suggested_result_command"])
        self.assertTrue(payload["evidence"])

    def test_cross_version_same_package_id_is_visible(self):
        """跨版本同一 package_id → 判定为"整条版本线无二进制"的可复用证据。"""
        rc, payload = self.run_probe_json(["--requires", "badlib/1.0.0", "badlib/1.1.0"])
        self.assertEqual(rc, 2)
        package_ids = {item["package_id"] for item in payload["results"]}
        self.assertEqual(package_ids, {"50c1715c9d6630244edc1e29caf86880dfcc7907"})

    def test_check_fallback_detects_build_tool_gap(self):
        rc, payload = self.run_probe_json(["--requires", "badlib/1.0.0", "--check-fallback"])
        self.assertEqual(rc, 2)
        self.assertEqual(payload["build_tool_gaps"], ["cmake/4.4.3"])
        self.assertIn("cmake/4.4.3", payload["evidence"])

    def test_remote_error_alone_is_tool_error_exit_three(self):
        rc, payload = self.run_probe_json(["--requires", "flakylib/1.0.0"])
        self.assertEqual(rc, 3)
        self.assertEqual(payload["verdict"], "NEEDS_REVIEW")
        self.assertEqual(payload["summary"]["binary_missing"], [])
        self.assertEqual(payload["suggested_result_command"], "")

    def test_isolated_home_receives_settings(self):
        _, payload = self.run_probe_json(["--requires", "goodlib/1.0.0"])
        self.assertTrue(payload["conan_home"].startswith(self.work))
        self.assertTrue(os.path.isfile(os.path.join(payload["conan_home"], "settings.yml")))
        self.assertTrue(any("已从" in note for note in payload["notes"]))

    def test_from_conanfile_extracts_requires(self):
        conanfile = os.path.join(self.work, "conanfile.py")
        with open(conanfile, "w", encoding="utf-8") as fh:
            fh.write("class P(ConanFile):\n    def requirements(self):\n")
            fh.write("        self.requires(\"badlib/1.0.0\")\n")
            fh.write("        self.tool_requires(\"cmake/[>=3.18]\")\n")
        rc, payload = self.run_probe_json(["--from-conanfile", conanfile, "--check-fallback"])
        self.assertEqual(rc, 2)
        refs = [item["ref"] for item in payload["results"]]
        self.assertEqual(refs, ["badlib/1.0.0", "cmake/[>=3.18]"])

    def test_human_output_mentions_verdict(self):
        proc = self.run_probe(["--requires", "badlib/1.0.0"])
        self.assertEqual(proc.returncode, 2)
        out = proc.stdout.decode("utf-8")
        self.assertIn("verdict: BLOCKED", out)
        self.assertIn("配方在仓、二进制缺失", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
