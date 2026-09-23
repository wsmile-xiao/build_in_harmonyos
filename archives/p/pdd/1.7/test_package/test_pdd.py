#!/usr/bin/env python3
"""pdd/1.7 OHOS 消费者测试（test_package，纯 stdlib，无 pytest 依赖）。

用法: python3 test_pdd.py <pdd_bin> <site_all> <site_deps> <dateutil_site>

覆盖两类：
1) 上游等价用例（期望值逐字取自上游 test.py 的 res 表——pytest 15 用例子集）
2) 鸿蒙消费者可行性用例（test_ohos_*，本仓库要求新增的 HarmonyOS 用例）：
   - test_ohos_platform: 断言运行平台确为 OHOS/HarmonyOS（防在其他平台假绿）
   - test_ohos_consumer_entrypoint: 不经 conanrun 的本体 site-packages，
     直接执行打包出的 bin/pdd launcher——验证 console_scripts 形态在
     OHOS musl python 下自定位可用
   - test_ohos_dateutil_from_conan: dateutil 只能来自 conan 交付的
     site-packages（OHOS 无系统 pip，证明依赖链真实可达）

输出约定: 每项打印 `ok: <name>` 或 `FAIL: <name>: ...`；全部通过才 exit 0。
"""
import os
import subprocess
import sys

PDD_BIN = sys.argv[1]
SITE_ALL = sys.argv[2]
SITE_DEPS = sys.argv[3]
DATEUTIL_SITE = sys.argv[4]

oks = 0
failures = []


def record(name, cond, detail=""):
    global oks
    if cond:
        oks += 1
        print(f"ok: {name}")
    else:
        failures.append(name)
        print(f"FAIL: {name}: {detail}")


def run_pdd(args, env=None):
    e = os.environ.copy()
    if env is None:
        e["PYTHONPATH"] = SITE_ALL
    else:
        e.update(env)
    p = subprocess.run([PDD_BIN] + args, capture_output=True, env=e)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


# ---------- 1) 上游等价用例（期望值 = 上游 test.py res 表） ----------

UPSTREAM_CASES = [
    ("upstream_date_diff",
     ("-d", "1983", "jul", "3", "2014", "1", "15"),
     "30y 6m 12d\n11154d\n"),
    ("upstream_date_diff_reverse",
     ("-d", "2014", "1", "15", "1983", "jul", "03"),
     "30y 6m 12d\n11154d\n"),
    ("upstream_time_diff",
     ("-t", "45:50", "6:17:33"),
     "05:31:43\n19903s\n"),
    ("upstream_time_add_overflow",
     ("-t", "47:71:37", "1:2:63", "--add"),
     "2 day(s) later, 01:14:40\n177280s\n"),
    ("upstream_date_add",
     ("-d", "2000", "FEB", "28", "3", "2", "1", "--add"),
     "Tue 2003 Apr 29\n"),
    ("upstream_date_sub_leap",
     ("-d", "2000", "Mar", "01", "0", "0", "1", "--sub"),
     "Tue 2000 Feb 29\n"),
]

for name, args, expected in UPSTREAM_CASES:
    got = run_pdd(list(args))
    record(name, got == expected, f"got {got!r}, want {expected!r}")

# ---------- 2) 鸿蒙消费者可行性用例 ----------

# 2a) 平台断言：确在 OHOS/HarmonyOS 上运行
uname_sys = os.uname().sysname
is_ohos = (sys.platform == "ohos") or ("HarmonyOS" in uname_sys) or ("OHOS" in uname_sys.upper())
record("test_ohos_platform", is_ohos,
       f"sys.platform={sys.platform!r}, uname={uname_sys!r} (期望 OHOS/HarmonyOS)")

# 2b) launcher 直调：PYTHONPATH 只含依赖 site（不含本体 site），
#     本体 pdd.py 必须由 bin/pdd 的自定位逻辑找到——消费者真实用法
env_deps_only = {"PYTHONPATH": SITE_DEPS}
got = run_pdd(["-d", "1983", "jul", "3", "2014", "1", "15"], env=env_deps_only)
record("test_ohos_consumer_entrypoint",
       got == "30y 6m 12d\n11154d\n",
       f"got {got!r} (bin/pdd 自定位 site-packages 失败?)")

# 2c) 依赖经 conan 交付可达：dateutil 从 conan 包的 site-packages import
try:
    sys.path.insert(0, DATEUTIL_SITE)
    for stale in [m for m in list(sys.modules) if m.startswith("dateutil")]:
        del sys.modules[stale]
    import dateutil  # noqa: F401
    from dateutil.relativedelta import relativedelta  # noqa: F401
    ok = dateutil.__file__.startswith(DATEUTIL_SITE)
    record("test_ohos_dateutil_from_conan", ok,
           f"dateutil.__file__={getattr(dateutil, '__file__', None)!r} "
           f"应位于 {DATEUTIL_SITE}")
except Exception as exc:  # noqa: BLE001
    record("test_ohos_dateutil_from_conan", False, f"import dateutil 失败: {exc!r}")

# ---------- 汇总 ----------

total = oks + len(failures)
print(f"{total} check(s), {oks} passed, {len(failures)} failed")
if failures:
    print(f"{len(failures)} check(s) FAILED")
    sys.exit(1)
sys.exit(0)
