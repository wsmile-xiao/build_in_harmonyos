#!/usr/bin/env python3
"""python-dateutil consumer test (L0c + R34): standalone test source
executed via self.run from conanfile.py test().

R34: actually call the tested API — dateutil.parser.parse() + relativedelta
(pure user-space). six dependency is provided via PYTHONPATH.

Usage: test_dateutil.py <site-packages>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    # site 可能为 pathsep 拼接（自身 + 依赖 six）——按 pathsep 分割
    paths = [p for p in site.split(os.pathsep) if p]
    if not any(os.path.isdir(os.path.join(p, "dateutil")) for p in paths):
        raise AssertionError(f"dateutil package missing in {paths}")
    sys.path = paths + sys.path
    # R34: 真实调用被测库 API
    from dateutil.parser import parse
    from dateutil.relativedelta import relativedelta
    import datetime

    dt = parse("2024-01-15 10:30:00")
    if dt.year != 2024 or dt.month != 1 or dt.day != 15:
        raise AssertionError(f"unexpected parse result: {dt!r}")
    # relativedelta(dt1, dt2) 返回 dt1-dt2（实测参数顺序语义——
    # 传 (2024-01-15, 2024-02-20) 得 months=-1,days=-5）——交换参数
    # 使结果为正，断言 months=1, days=5
    rd = relativedelta(datetime.date(2024, 2, 20),
                       datetime.date(2024, 1, 15))
    if rd.months != 1 or rd.days != 5:
        raise AssertionError(f"unexpected relativedelta: {rd!r}")
    print("OK: python-dateutil 2.9.0.post0 (parse + relativedelta ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
