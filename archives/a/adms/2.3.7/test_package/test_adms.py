#!/usr/bin/env python3
"""test_package for adms 2.3.7 — 真实调用 admsXml/admsCheck 二进制。

用例（每个用例断言输出文件非空，不轻信 exit 0）：
  1. admsXml --version 输出版本号
  2. admsCheck 生成 dummy.va / dummy.xml（非空）
  3. admsXml dummy.va -e dummy.xml → dummy.net（非空）
"""

import json
import os
import subprocess
import sys
import tempfile

MARKER_PREFIX = "HMBS_TEST_PACKAGE_RESULT="


def run(cmd, cwd):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def main():
    adms_xml = sys.argv[1]
    adms_check = sys.argv[2]

    executed = 0
    passed = 0
    failed = 0
    failures = []

    # 用例 1: 版本号
    executed += 1
    rc, out, err = run([adms_xml, "--version"], cwd=os.getcwd())
    if rc == 0 and "2.3.7" in (out + err):
        passed += 1
        print(f"[test] admsXml --version: PASS ({out.strip()})")
    else:
        failed += 1
        failures.append(f"admsXml --version rc={rc} out={out!r} err={err!r}")

    with tempfile.TemporaryDirectory() as tmp:
        # 用例 2: admsCheck 生成上游示例文件
        executed += 1
        rc, out, err = run([adms_check], cwd=tmp)
        va_ok = os.path.isfile(os.path.join(tmp, "dummy.va")) and os.path.getsize(os.path.join(tmp, "dummy.va")) > 0
        xml_ok = os.path.isfile(os.path.join(tmp, "dummy.xml")) and os.path.getsize(os.path.join(tmp, "dummy.xml")) > 0
        if rc == 0 and va_ok and xml_ok:
            passed += 1
            print("[test] admsCheck (dummy.va/dummy.xml): PASS")
        else:
            failed += 1
            failures.append(f"admsCheck rc={rc} va_ok={va_ok} xml_ok={xml_ok}")

        # 用例 3: admsXml 转换 dummy.va → dummy.net
        executed += 1
        rc, out, err = run([adms_xml, "dummy.va", "-e", "dummy.xml"], cwd=tmp)
        net_path = os.path.join(tmp, "dummy.net")
        net_ok = os.path.isfile(net_path) and os.path.getsize(net_path) > 0
        if rc == 0 and net_ok:
            passed += 1
            print(f"[test] admsXml dummy.va -e dummy.xml: PASS (dummy.net {os.path.getsize(net_path)} bytes)")
        else:
            failed += 1
            failures.append(f"admsXml transform rc={rc} net_ok={net_ok} err={err[:300]!r}")

    result = {
        "executed": True,
        "passed": failed == 0 and passed > 0,
        "command": f'"{adms_xml}" --version && admsCheck && admsXml dummy.va -e dummy.xml',
        "discovered": 3,
        "passedCount": passed,
    }
    print(MARKER_PREFIX + json.dumps(result, ensure_ascii=False))
    for f in failures:
        print(f"[test] FAILED: {f}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
