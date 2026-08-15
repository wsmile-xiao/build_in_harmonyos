#!/usr/bin/env python3
"""tccutil 1.5.1 test_package 断言脚本（test_package 测试源，L0c 要求）。

由 test_package/conanfile.py 的 test() 调用：python3 test_tccutil.py <package_folder>

真实调用被测包（R34，非空壳）：
  1. bin/tccutil --version：真实执行 CLI main()/display_version()，断言
     输出含 "1.5.1" 且退出码 0（CLI 可执行路径）
  2. bin/tccutil --help：真实执行 argparse 帮助路径，断言退出码 0
  3. 模块 API：SourceFileLoader 加载 bin/tccutil（该文件无 .py 后缀，
     spec_from_file_location 无法推断 loader 会返回 None，故显式指定
     加载器），断言 util_version == '1.5.1' 且 display_version/
     display_help 可调用

断言结果自行计数并输出 HMBS_TEST_PACKAGE_RESULT 标记（discovered 为
上述真实用例数，passedCount 为通过的用例数，非硬编码）。上游无测试
套件（审计见 test_package/MANIFEST.yml），输出 HMBS_UPSTREAM_TEST_RESULT
no_tests 标记。
"""
import importlib.machinery
import importlib.util
import os
import subprocess
import sys

pkg = sys.argv[1]
cli = os.path.join(pkg, "bin", "tccutil")

failures = []


def run(args):
    """Run a CLI command, return (exit_code, stdout_text)."""
    proc = subprocess.run(args, capture_output=True, text=True)
    return proc.returncode, proc.stdout


# ---- 用例 1：--version 输出含 1.5.1，退出码 0 ----
rc, out = run([sys.executable, cli, "--version"])
if rc == 0 and "1.5.1" in out:
    print("PASS cli --version (exit 0, output: {!r})".format(out.strip()))
else:
    failures.append("cli --version: rc={} out={!r}".format(rc, out))

# ---- 用例 2：--help 退出码 0 ----
rc, out = run([sys.executable, cli, "--help"])
if rc == 0 and "usage:" in out:
    print("PASS cli --help (exit 0)")
else:
    failures.append("cli --help: rc={} out={!r}".format(rc, out))

# ---- 用例 3：模块 API 断言 ----
try:
    # bin/tccutil 无 .py 后缀：spec_from_file_location 无法从扩展名推断
    # loader，会返回 spec=None（或 loader=None），直接 spec.loader 访问
    # 即报 'NoneType' object has no attribute 'loader'。显式指定
    # SourceFileLoader 加载扩展名无关的 Python 脚本。
    loader = importlib.machinery.SourceFileLoader("tccutil", cli)
    spec = importlib.util.spec_from_loader("tccutil", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    assert mod.util_version == "1.5.1", "util_version={}".format(mod.util_version)
    assert callable(mod.display_version) and callable(mod.display_help)
    print("PASS module API (util_version=1.5.1, display_version/display_help callable)")
except Exception as exc:
    failures.append("module API: {}".format(exc))

discovered = 3
passed = discovered - len(failures)
if failures:
    for item in failures:
        print("FAIL:", item)
    print('HMBS_TEST_PACKAGE_RESULT={{"executed":true,"passed":false,'
          '"command":"python3 test_tccutil.py <pkg>","discovered":{},'
          '"passedCount":{}}}'.format(discovered, passed))
    sys.exit(1)

print("ALL test_package assertions passed")
print('HMBS_TEST_PACKAGE_RESULT={{"executed":true,"passed":true,'
      '"command":"python3 test_tccutil.py <pkg>","discovered":{},'
      '"passedCount":{}}}'.format(discovered, passed))
# 上游无测试套件（审计见 test_package/MANIFEST.yml）：no_tests 标记。
# 注意：本 print 不调用 .format()，字符串中的大括号必须是单层字面量；
# 若沿用 {{/}} 转义会原样输出 {{...}} 双括号，JSON 非法、hmbs 无法解析。
print('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none",'
      '"command":"N/A (upstream has no test suite)","discovered":0,'
      '"executed":0,"passed":0,"failed":0,"skipped":0,'
      '"reason":"audit: v1.5.1 source tree contains only tccutil.py/README.md/'
      'LICENSE/.github (workflow python-app.yml runs flake8 lint only, pytest '
      'step commented out); no tests/, no test_*.py, no Makefile check target"}')
