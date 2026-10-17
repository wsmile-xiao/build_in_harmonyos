#!/usr/bin/env python3
"""HarmonyOS 专项测试 — pyjson5 0.15.0。

在 OHOS 设备 python3.12 上运行，使用**已安装**的 pyjson5 包（PYTHONPATH 指向
site-packages）。覆盖真实业务场景：解析带中文注释/尾逗号/单引号/十六进制/
Infinity 的 JSON5 配置文件（鸿蒙应用常见配置形态），校验字段；执行真实文件
IO（HMDFS 文件系统读写，TMPDIR 可写目录）与 dump/loads round-trip。
任一断言失败即非零退出。全部通过打印 PASS 标记。
"""
import os
import sys
import tempfile

import json5  # 已安装包（test_package 注入 PYTHONPATH）


def main():
    # 1) loads 公开 API：JSON5 语法全覆盖（注释/尾逗号/单引号/十六进制/Infinity）
    src = """
    {
      // 鸿蒙场景配置示例（行注释）
      app: "settings",  /* 块注释 */
      version: 0x15,
      features: ['a', 'b',],
      unicode: "中文内容",
      ratio: Infinity,
    }
    """
    data = json5.loads(src)
    assert data["app"] == "settings", data
    assert data["version"] == 21, data
    assert data["features"] == ["a", "b"], data
    assert data["unicode"] == "中文内容", data
    assert data["ratio"] == float("inf"), data

    # 2) 真实文件 IO：写入 JSON5 配置并重新读取（OHOS 文件系统）
    tmpdir = os.environ.get("TMPDIR", tempfile.gettempdir())
    path = os.path.join(tmpdir, "pyjson5_ohos_test_config.json5")
    with open(path, "w", encoding="utf-8") as f:
        json5.dump({"name": "ohos-app", "count": 3, "tags": ["a", "b"]}, f)
    with open(path, encoding="utf-8") as f:
        reloaded = json5.load(f)
    os.unlink(path)
    assert reloaded == {"name": "ohos-app", "count": 3, "tags": ["a", "b"]}, reloaded

    # 3) dumps 公开 API round-trip（sort_keys/indent；JSON5 默认键不加引号）
    s = json5.dumps({"b": 1, "a": [True, None]}, indent=2, sort_keys=True)
    assert "a: [" in s and "b: 1" in s, s
    parsed = json5.loads(s)
    assert parsed == {"a": [True, None], "b": 1}, parsed

    print("HARMONYOS-SPECIFIC-TEST PASS: json5.loads/dump/dumps/file-io/round-trip ok")
    print("json5 version:", json5.__version__)
    print("python:", sys.version.split()[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
