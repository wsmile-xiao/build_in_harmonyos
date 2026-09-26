#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""parse 1.22.2 — HarmonyOS 专项测试用例（真实业务场景验证）

在 OHOS PC 环境（aarch64, python3.12）下运行，通过 parse 已安装产物的
公开 API 验证三方库在鸿蒙平台上的可用性。与上游 pytest 套件、test_package
消费者用例分别计数。

覆盖业务场景：
  1. format 反向解析（配置文件/日志行解析类业务）
  2. 类型转换（int/float/date）与命名/位置字段混合
  3. 多行多记录解析（日志流逐行解析）
  4. 自定义类型转换器（with_pattern）
  5. 无匹配场景与容错（None 返回值）
"""

import datetime
import sys

EXPECTED_VERSION = "1.22.2"


def main():
    import parse

    failures = []

    def check(name, cond, detail=""):
        if cond:
            print(f"[PASS] {name}")
        else:
            print(f"[FAIL] {name} {detail}")
            failures.append(name)

    check("version", parse.__version__ == EXPECTED_VERSION,
          parse.__version__)

    # 1. 业务：解析配置行 "key = value"
    line = "max_connections = 128"
    r = parse.parse("{key} = {value:d}", line)
    check("config line parse",
          r is not None and r["key"] == "max_connections"
          and r["value"] == 128, repr(r))

    # 2. 业务：时间戳 + 级别 + 消息（日志行）
    log = "2026-09-21 10:30:00 ERROR disk full"
    r = parse.parse("{date} {time} {level} {msg}", log)
    check("log line parse",
          r is not None and r["level"] == "ERROR"
          and r["msg"] == "disk full", repr(r))

    # 3. 业务：日期字段提取（ISO 日期 "ti" 类型转换为 datetime）
    r = parse.parse("expires={:ti}", "expires=2026-12-31")
    check("date conversion",
          r is not None
          and r[0] == datetime.datetime(2026, 12, 31, 0, 0, 0), repr(r))

    # 4. 多行日志流逐行解析（findall，字段显式用 w 词类型——
    #    parse 默认 {} 是非贪婪 .+?，只匹配 1 字符）
    stream = "id=1 status=ok\nid=2 status=warn\nid=3 status=ok"
    rows = [{k: v for k, v in r.named.items()}
            for r in parse.findall("id={id:d} status={status:w}",
                                   stream)]
    check("multi-line findall",
          rows == [{"id": 1, "status": "ok"},
                   {"id": 2, "status": "warn"},
                   {"id": 3, "status": "ok"}], repr(rows))

    # 5. 自定义类型：版本号解析（语义化版本比较）
    @parse.with_pattern(r"\d+\.\d+\.\d+")
    def ver(text):
        return tuple(int(x) for x in text.split("."))

    r = parse.parse("ver={v:ver}", "ver=1.22.2", {"ver": ver})
    check("semver custom type",
          r is not None and r["v"] == (1, 22, 2), repr(r))

    # 6. 无匹配容错
    r = parse.parse("key={key:d}", "key=abc")
    check("no-match returns None", r is None, repr(r))

    # 7. 完整 format 反向对齐：parse(format(值)) 还原
    original = {"name": "parse-lib", "count": 7}
    fmt = "name={name}, count={count:d}"
    rendered = fmt.format(**original)
    back = parse.parse(fmt, rendered)
    check("format round-trip",
          back is not None and back["name"] == original["name"]
          and back["count"] == original["count"], repr(back))

    if failures:
        print(f"OHOS TEST FAILED: {len(failures)}: {failures}")
        sys.exit(1)
    print("ALL OHOS-specific tests passed")


if __name__ == "__main__":
    main()