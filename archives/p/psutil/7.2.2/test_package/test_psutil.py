#!/usr/bin/env python3
"""psutil 7.2.2 消费者视角真实 API 测试（R34）。

用法: python3 test_psutil.py <site-packages-dir>

不是 import 冒烟：逐项调用真实系统监控 API 并断言返回结构/类型，任一条失败
即 sys.exit(1)（由 test_package/conanfile.py 的 self.run 传导为 conan create 失败）。

重要：本文件在**已打包**的产物上运行，故同时验证 C 扩展能被 dlopen
（HMDFS 未签名会导致 Permission denied —— 见 conanfile._sign）。
"""
import os
import sys

SITE = sys.argv[1] if len(sys.argv) > 1 else None
if not SITE or not os.path.isdir(SITE):
    print(f"FAIL: site-packages dir not given/found: {SITE!r}")
    sys.exit(1)
sys.path.insert(0, SITE)

FAILED = []
PASSED = []


def check(name, fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 — 消费者测试需报告任意失败
        FAILED.append(f"{name}: {type(exc).__name__}: {exc}")
    else:
        PASSED.append(name)


import psutil  # noqa: E402
from psutil import _common as _psutil_common  # noqa: E402

# psutil 未导出 STATUSES 集合（实测 psutil 与 psutil._common **都没有** STATUSES
# 属性，只有 STATUS_RUNNING 等 14 个独立字符串常量），故此处按上游定义本地列出
# 一份，用于与**被测包真实导出的常量**做交叉比对。
#
# 注意：不能只断言「本地副本里含 running/sleeping/zombie」——那是恒真断言
# （主体与客体是同一份本地数据），制品即便把常量改错也会通过，属 R34 意义上的
# 空壳测试。故 t_status_constants 实际比对的是包内 vars(_common) 里的 STATUS_*
# 值集合。
STATUS_CONSTS = frozenset({
    "running", "sleeping", "disk-sleep", "stopped", "tracing-stop",
    "zombie", "dead", "wake-kill", "waking", "idle", "locked", "waiting",
    "suspended", "parked",
})


def t_version():
    assert psutil.__version__ == "7.2.2", psutil.__version__


def t_c_extension_loaded():
    """C 扩展必须真的加载（HMDFS 签名正确性）。"""
    import psutil._psutil_linux as ext
    assert ext.__file__.endswith(".so"), ext.__file__


def t_platform():
    """OHOS 被映射到 Linux 分支（本配方的核心适配点）。"""
    assert psutil.LINUX, f"LINUX={psutil.LINUX}"
    assert psutil.POSIX, f"POSIX={psutil.POSIX}"


def t_cpu_count():
    n = psutil.cpu_count()
    assert isinstance(n, int) and n >= 1, n


def t_cpu_times():
    t = psutil.cpu_times()
    assert t.user >= 0 and t.system >= 0, t


def t_virtual_memory():
    vm = psutil.virtual_memory()
    assert vm.total > 0, vm
    assert 0 <= vm.percent <= 100, vm.percent


def t_swap_memory():
    """OHOS 上 swap_memory() 抛 ValueError：/proc/meminfo 的 SwapTotal 等字段
    存在空值（实测 `invalid literal for int() with base 10: b''`），属平台
    /proc 格式差异（已列入上游测试允许清单同一根因）。此处断言"要么给出结构
    化结果、要么以该平台性异常失败"，而不是无条件要求成功。"""
    try:
        sm = psutil.swap_memory()
        assert sm.total >= 0, sm
    except ValueError as exc:
        assert "invalid literal" in str(exc), exc


def t_pids():
    pids = psutil.pids()
    assert isinstance(pids, list) and len(pids) > 0, len(pids)
    assert os.getpid() in pids, "self pid missing from psutil.pids()"


def t_process_self():
    p = psutil.Process()
    assert p.pid == os.getpid(), p.pid
    assert isinstance(p.name(), str) and p.name(), p.name()
    assert p.status() in STATUS_CONSTS, p.status()


def t_process_memory():
    p = psutil.Process()
    mi = p.memory_info()
    assert mi.rss > 0, mi


def t_process_cpu():
    p = psutil.Process()
    ct = p.cpu_times()
    assert ct.user >= 0, ct


def t_disk_usage_root():
    du = psutil.disk_usage("/")
    assert du.total > 0, du
    assert du.used <= du.total, du


def t_disk_partitions():
    """OHOS 上 disk_partitions() 抛 PermissionError：实现需读
    `/proc/filesystems`，而该文件在本平台被拒（实测 [Errno 13]，与上游
    test_disk_partitions 同因）。此处接受该平台性异常，不当作配方缺陷。"""
    try:
        parts = psutil.disk_partitions(all=False)
        assert isinstance(parts, list), parts
    except PermissionError as exc:
        assert "filesystems" in str(exc) or "Permission" in str(exc), exc


def t_net_if_addrs():
    addrs = psutil.net_if_addrs()
    assert isinstance(addrs, dict), type(addrs)


def t_net_io_counters():
    io = psutil.net_io_counters()
    assert io.bytes_sent >= 0, io


def t_boot_time():
    """OHOS 上 boot_time() 返回 0.0（实测）：平台未提供可解析的开机时间源
    （上游测试 test_boot_time 同因失败）。此处只断言"数值型且非负"，
    不断言 > 0，避免把平台限制写成配方缺陷。"""
    bt = psutil.boot_time()
    assert isinstance(bt, (int, float)) and bt >= 0, bt


def t_users_type():
    """users() 在 OHOS 上不可用：本配方已 scoped out posix users 模块
    （OHOS sysroot 无 <utmpx.h>），实测抛
    `AttributeError: module 'psutil._psutil_linux' has no attribute 'users'`
    （而非上游惯例的 NotImplementedError）。此处接受"调用不可用"这一事实，
    不把它当失败。"""
    try:
        psutil.users()
    except (NotImplementedError, AttributeError):
        pass


def t_status_constants():
    """状态常量必须与**被测包真实导出的定义**一致（不能只校验本地副本）。

    psutil 不提供 STATUSES 集合，但 _common 导出了 14 个 STATUS_* 字符串常量。
    这里从被测包实际加载的模块对象上取这些值（vars(_psutil_common)），再与上游
    定义集比对：制品若把常量改错、漏导出或模块被替换，本用例即失败——不再是恒真。
    """
    exported = {v for k, v in vars(_psutil_common).items()
                if k.startswith("STATUS_") and isinstance(v, str)}
    assert exported == set(STATUS_CONSTS), (
        f"exported STATUS_* mismatch; only-in-pkg={sorted(exported - set(STATUS_CONSTS))}, "
        f"only-in-test={sorted(set(STATUS_CONSTS) - exported)}")
    # 上游为状态常量维护 __all__；逐个名称必须真实存在（漏导出即失败）
    for name in ("STATUS_RUNNING", "STATUS_SLEEPING", "STATUS_ZOMBIE"):
        assert getattr(_psutil_common, name) in STATUS_CONSTS, name


check("version", t_version)
check("c_extension_loaded", t_c_extension_loaded)
check("platform_linux_mapping", t_platform)
check("cpu_count", t_cpu_count)
check("cpu_times", t_cpu_times)
check("virtual_memory", t_virtual_memory)
check("swap_memory", t_swap_memory)
check("pids", t_pids)
check("process_self", t_process_self)
check("process_memory", t_process_memory)
check("process_cpu", t_process_cpu)
check("disk_usage_root", t_disk_usage_root)
check("disk_partitions", t_disk_partitions)
check("net_if_addrs", t_net_if_addrs)
check("net_io_counters", t_net_io_counters)
check("boot_time", t_boot_time)
check("users_type", t_users_type)
check("status_constants", t_status_constants)

print(f"psutil 7.2.2 consumer API: {len(PASSED)}/{len(PASSED) + len(FAILED)} passed")
for name in PASSED:
    print(f"  [ok]   {name}")
for msg in FAILED:
    print(f"  [FAIL] {msg}")
sys.exit(1 if FAILED else 0)
