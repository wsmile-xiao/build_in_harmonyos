#!/usr/bin/env python3
"""
HarmonyOS 子进程兼容层测试脚本

验证 Python 3.9.0 鸿蒙适配版本的 subprocess 兼容层是否正确工作。

运行方式:
    cd ~/python/Python-3.9.0
    export LD_LIBRARY_PATH=.
    ./python3.9 test_subprocess_compat.py
"""

import os
import sys
import subprocess


def test_platform():
    """测试1: 平台检测"""
    print("\n[测试1] 平台检测")
    print(f"  sys.platform = {sys.platform}")
    
    is_harmonyos = 'ohos' in sys.platform.lower() or 'harmonyos' in sys.platform.lower()
    if is_harmonyos:
        print("  ✅ 检测到 HarmonyOS")
        return True
    print("  ⚠️ 非 HarmonyOS 系统")
    return True


def test_compat_module():
    """测试2: 兼容层模块加载"""
    print("\n[测试2] 兼容层模块加载")
    try:
        import _harmonyos_compat
        print("  ✅ _harmonyos_compat 模块已加载")
        return True
    except ImportError:
        print("  ❌ _harmonyos_compat 模块未找到")
        return False


def test_os_system_wrapped():
    """测试3: os.system 包装"""
    print("\n[测试3] os.system 包装检测")
    func_name = os.system.__name__
    is_wrapped = '_wrapped' in func_name
    print(f"  函数名: {func_name}")
    print(f"  {'✅ 已包装' if is_wrapped else '⚠️ 未包装'}")
    return True


def test_os_system_exec():
    """测试4: os.system 执行"""
    print("\n[测试4] os.system 执行")
    ret = os.system("echo 'Hello'")
    print(f"  返回值: {ret}")
    print(f"  {'✅ 成功' if ret == 0 else '❌ 失败'}")
    return ret == 0


def test_subprocess_run():
    """测试5: subprocess.run 执行"""
    print("\n[测试5] subprocess.run 执行")
    r = subprocess.run(['echo', 'Hello'], capture_output=True, text=True)
    print(f"  stdout: {r.stdout.strip()}")
    print(f"  returncode: {r.returncode}")
    print(f"  {'✅ 成功' if r.returncode == 0 else '❌ 失败'}")
    return r.returncode == 0


def test_sdk_tool():
    """测试6: SDK 工具执行（关键测试）"""
    print("\n[测试6] SDK 工具执行（clang）")
    r = subprocess.run(['clang', '--version'], capture_output=True, text=True)
    print(f"  returncode: {r.returncode}")
    if r.stdout:
        print(f"  stdout: {r.stdout[:50]}...")
    print(f"  {'✅ 成功' if r.returncode == 0 else '❌ 失败'}")
    return r.returncode == 0


def main():
    print("=" * 60)
    print("HarmonyOS 子进程兼容层测试")
    print("=" * 60)
    
    tests = [
        test_platform,
        test_compat_module,
        test_os_system_wrapped,
        test_os_system_exec,
        test_subprocess_run,
        test_sdk_tool,
    ]
    
    results = []
    for test in tests:
        try:
            results.append((test.__name__, test()))
        except Exception as e:
            print(f"  ❌ 异常: {e}")
            results.append((test.__name__, False))
    
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    for name, ok in results:
        print(f"  {'✅' if ok else '❌'} {name}")
    
    print(f"\n通过: {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())