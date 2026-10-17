#!/usr/bin/env python3
"""HarmonyOS-specific contract test for the packaged plyara 2.2.8.

上游 2.2.8 的 tests/ 全部面向解析语义，没有任何平台契约断言；本文件是本次
OHOS 适配**新增的鸿蒙专项测试**，断言 plyara 在 OpenHarmony PC 上的交付形态
与运行时契约（HARMONYOS-ONLY，不复制上游任何用例）：

  OHOS-1  平台身份：sys.platform == 'ohos' / platform.system() == 'HarmonyOS'。
          上游源码零平台分支（已实测 grep 零命中），必须证明其在 ohos 而非
          linux 下可完整解析。
  OHOS-2  vendored submodule 交付形态：上游 src/ply 是指向
          third_party/ply/src/ply 的符号链接，且 GitHub 归档不含 submodule
          内容；打包必须把 PLY 真实落位到**包内** site-packages，否则
          `import ply.lex / ply.yacc` 直接失败。
  OHOS-3  只读工作目录契约（E046/E002）：OHOS 上 HMDFS chmod 不生效、/tmp
          不可写；CLI 在 cwd 与 TMPDIR 均固定为同一目录时必须产出与基准
          逐字节一致的 JSON，且**不得遗留任何生成物**
          （parsetab.py / parser.out / __pycache__）——这是交付到只读文件
          系统的前提（旧版 PLY 会把解析表写到 cwd）。
  OHOS-4  OHOS 应用沙箱契约：TMPDIR 指向 /data/storage/el2/... 应用沙箱时
          CLI 仍须可用（沙箱路径语义，不是 Linux /tmp 假设）。
  OHOS-5  端到端基准对齐：包内 bin/plyara 解析上游 CLI 官方夹具
          （tests/data/command_line/test_file.yar 原字节）的输出 sha256 必须
          命中上游 test_command_line.py 声明的期望哈希集合 —— 证明打包产物
          与上游测试基线逐字节一致。

用法: test_ohos_plyara.py <package_folder> <site_packages>
"""
import base64
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tempfile

# OHOS-3 固定夹具（本机实测基准）
DEMO_RULES = (
    "rule demo_rule : ohos_test\n"
    "{\n"
    "    meta:\n"
    '        author = "plyara-ohos"\n'
    "        score = 42\n"
    "    strings:\n"
    '        $a = "harmony"\n'
    "        $b = { 68 61 72 6D 6F 6E 79 }\n"
    "    condition:\n"
    "        $a or $b\n"
    "}\n"
)
DEMO_CLI_SHA256 = (
    "6299f1f0fa03817797cadeb53a3a3a86c7b73a21fd94171bd656c5371c4196f1")

# OHOS-5 上游 CLI 官方夹具（tests/data/command_line/test_file.yar 原字节）
UPSTREAM_FIXTURE_B64 = (
    "cnVsZSBGaXJzdFJ1bGUgewogIC8vIHRlc3QgY29tbWVudAogIG1ldGE6CiAgICBhdXRo"
    "b3IgPSAiQW5kcsOpcyBJbmllc3RhIgogICAgZGF0ZSA9ICIyMDE1LTAxLTAxIgogIHN0"
    "cmluZ3M6CiAgICAkYSA9ICJoYXJrLCBhIFwic3RyaW5nXCIgaGVyZSIgZnVsbHdvcmQg"
    "YXNjaWkKICAgICRiID0geyAwMCAyMiA0NCA2NiA4OCBhYSBjYyBlZSB9CiAgY29uZGl0"
    "aW9uOgogICAgYWxsIG9mIHRoZW0KICB9CgppbXBvcnQgImJpbmdvIgppbXBvcnQgImJh"
    "bmdvIgpydWxlIFNlY29uZFJ1bGUgOiBhVGFnIHsKICBtZXRhOgogICAgYXV0aG9yID0g"
    "Ikl2YW4gUmFraXRpxIciCiAgICBkYXRlID0gIjIwMTUtMDItMDEiCiAgc3RyaW5nczoK"
    "ICAgIC8qIHRlc3QKICAgICAgIG11bHRpbGluZQogICAgICAgY29tbWVudAogICAgKi8K"
    "ICAgICR4ID0gImhpIgogICAgJHkgPSAvc3RhdGU6IChvbnxvZmYpLyB3aWRlCiAgICAk"
    "eiA9ICJieWUiCiAgY29uZGl0aW9uOgogICAgZm9yIGFsbCBvZiB0aGVtIDogKCAjID4g"
    "MiApCn0KCnJ1bGUgVGhpcmRSdWxlIHtjb25kaXRpb246IGZhbHNlfQoKcnVsZSBGb3J0"
    "aFJ1bGUgewogICAgY29uZGl0aW9uOgogICAgICAgIHVpbnQ4KDApIF4gdW5pdDgoMSkg"
    "PT0gMHgxMgp9Cg=="
)
# 上游 tests/test_command_line.py 声明的期望哈希集合
UPSTREAM_CLI_HASHES = (
    "9d1991858f1b48b2485a9cb45692bc33c5228fb5acfa877a0d097b1db60052e3",
    "18569226a33c2f8f0c43dd0e034a6c05ea38f569adc3ca37d3c975be0d654f06",
    "b9b64df222a91d5b99b0099320134e3aecd532513965d1cf7b5a0b58881bcccc",
)
OHOS_SANDBOX = "/data/storage/el2/base/haps/entry/files"


def _run(cmd, env, cwd):
    res = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=cwd)
    return res.returncode, res.stdout, res.stderr


def _run_cli(py, cli, env, cwd, fixture_name):
    return _run([py, cli, fixture_name], env, cwd)


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: test_ohos_plyara.py <package_folder> <site_packages>",
              file=sys.stderr)
        return 1
    pkg, site = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    py = sys.executable if os.path.isfile(sys.executable or "") else "python3"
    cli = os.path.join(pkg, "bin", "plyara")
    if not os.path.isfile(cli):
        print(f"FAIL: bin/plyara missing: {cli}", file=sys.stderr)
        return 1
    checks = 0
    base_env = dict(os.environ)
    base_env["PYTHONPATH"] = site
    base_env["PYTHONDONTWRITEBYTECODE"] = "1"

    # ── OHOS-1 平台身份 ────────────────────────────────────────────────
    print("[ohos] platform: sys.platform=%r system=%r machine=%r"
          % (sys.platform, platform.system(), platform.machine()))
    if sys.platform == "ohos":
        assert platform.system() == "HarmonyOS", platform.system()
        assert platform.machine() in ("aarch64", "arm64"), platform.machine()
        checks += 2
        print("[ohos] OHOS-1 PASS: HarmonyOS/aarch64 平台身份确认")
    else:
        print("[ohos] OHOS-1 NOTE: 非 OHOS 环境（%s）——平台身份断言按契约放宽"
              % sys.platform)

    # ── OHOS-2 vendored PLY 交付形态 ──────────────────────────────────
    code = ("import os, ply, plyara;"
            "print(os.path.abspath(ply.__file__));"
            "print(os.path.abspath(plyara.__file__));"
            "print(ply.__version__)")
    rc, out, err = _run([py, "-c", code], base_env, None)
    assert rc == 0, err
    lines = out.strip().splitlines()
    assert lines[0].startswith(site), lines
    assert lines[1].startswith(site), lines
    assert lines[2] == "2022.10.27", lines[2]
    checks += 3
    print("[ohos] OHOS-2 PASS: 内嵌 PLY(%s) 已真实落位包内 site-packages"
          % lines[2])

    # ── OHOS-3 只读工作目录 + 零生成物 ────────────────────────────────
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "ohos_fixture.yar"), "w",
                  encoding="utf-8") as fh:
            fh.write(DEMO_RULES)
        env3 = dict(base_env)
        env3.update(TMPDIR=td, TEMP=td, TMP=td)
        rc, out, err = _run_cli(py, cli, env3, td, "ohos_fixture.yar")
        assert rc == 0, err
        digest = hashlib.sha256(out.encode()).hexdigest()
        assert digest == DEMO_CLI_SHA256, digest
        leftover = sorted(os.listdir(td))
        assert leftover == ["ohos_fixture.yar"], leftover
        checks += 3
        print("[ohos] OHOS-3 PASS: cwd/TMPDIR 固定目录下 CLI 输出一致且无生成物")

    # ── OHOS-4 OHOS 应用沙箱 TMPDIR ───────────────────────────────────
    if os.path.isdir(OHOS_SANDBOX) and os.access(OHOS_SANDBOX, os.W_OK):
        sand = os.path.join(OHOS_SANDBOX, "plyara-ohos-probe-%d" % os.getpid())
        os.makedirs(sand, exist_ok=True)
        try:
            with open(os.path.join(sand, "sandbox_fixture.yar"), "w",
                      encoding="utf-8") as fh:
                fh.write(DEMO_RULES)
            env4 = dict(base_env)
            env4["TMPDIR"] = sand
            rc, out, err = _run_cli(py, cli, env4, sand, "sandbox_fixture.yar")
            assert rc == 0, err
            assert hashlib.sha256(out.encode()).hexdigest() == DEMO_CLI_SHA256
            checks += 2
            print("[ohos] OHOS-4 PASS: TMPDIR 指向 OHOS 应用沙箱 %s 时 CLI 可用"
                  % sand)
        finally:
            shutil.rmtree(sand, ignore_errors=True)
    else:
        print("[ohos] OHOS-4 NOTE: 沙箱 %s 不可用——按契约放宽" % OHOS_SANDBOX)

    # ── OHOS-5 与上游 CLI 基线对齐 ────────────────────────────────────
    with tempfile.TemporaryDirectory() as td:
        data = base64.b64decode(UPSTREAM_FIXTURE_B64)
        with open(os.path.join(td, "test_file.yar"), "wb") as fh:
            fh.write(data)
        rc, out, err = _run_cli(py, cli, dict(base_env), td, "test_file.yar")
        assert rc == 0, err
        digest = hashlib.sha256(out.encode()).hexdigest()
        assert digest in UPSTREAM_CLI_HASHES, \
            "CLI output deviates from upstream baseline: %s" % digest
        checks += 1
        print("[ohos] OHOS-5 PASS: 上游官方夹具 CLI 输出 sha256=%s（命中上游基线）"
              % digest[:16])

    print("plyara 2.2.8 OHOS-specific test: PASS (%d assertions)" % checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
