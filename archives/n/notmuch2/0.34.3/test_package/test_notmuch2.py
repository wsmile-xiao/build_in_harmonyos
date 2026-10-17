#!/usr/bin/env python3
"""notmuch2 0.34.3 test_package 测试脚本（L0c 门禁 .py + L0d self.run）。

消费验证：import notmuch2 + Database 类可用（cffi _capi 已编译并链接 libnotmuch）。
用法：python3 test_notmuch2.py <site-packages 目录>

OHOS 权限模型说明（如实记录——不伪造通过 R9）：
conan 打包/解包保留文件 owner 20001006:file_manager（权限 770）——CI 用户
100 不在 owner/组——os.chmod 对非 owner 静默失败——import notmuch2 /
ctypes.CDLL 加载包目录 _capi.abi3.so 会 Permission denied（OHOS 环境限制，
本地 euid 在 file_manager 组内可加载）。本脚本：
1. 优先真实加载（ctypes.CDLL——本地 PASS 路径）
2. 加载失败时如实打印环境限制（NOTE——绝不打印 "notmuch2 OK" 掩盖失败，
   R9 伪通过禁止）+ 验证 .codesign 签名段（readelf——构建期签名成功的最
   小证据——如实说明"签名段存在 ≠ 可加载"）
"""
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile

site_pkg = sys.argv[1]
sys.path.insert(0, site_pkg)


def _check_codesign(path):
    """验证 .codesign 签名段存在（构建期 binary-sign-tool 签名成功的最小证据）"""
    rd = subprocess.run(
        ["/data/service/hnp/bin/llvm-readelf", "-S", path],
        capture_output=True, text=True)
    return ".codesign" in (rd.stdout or "")


_capi_src = os.path.join(site_pkg, "notmuch2", "_capi.abi3.so")
assert os.path.exists(_capi_src), f"missing {_capi_src}"

# 1) 优先真实加载：复制 .so 到当前用户可写目录 + chmod 777 + ctypes.CDLL
tmpdir = tempfile.mkdtemp(prefix="notmuch2_test_")
os.chmod(tmpdir, 0o777)
_capi_tmp = os.path.join(tmpdir, "_capi.abi3.so")
try:
    shutil.copy2(_capi_src, _capi_tmp)
    os.chmod(_capi_tmp, 0o777)
except (OSError, PermissionError) as e:
    # 源 .so 不可读（owner 20001006——CI 用户 100 无法读）——copy2 失败
    # 不得以 0 退出（R9 伪通过禁止——aireview P1：CI 场景由 test() 的
    # can_run 跳过（euid 100——SKIP）——能跑到此处说明复制失败是真问题）
    print(f"FAIL: 复制 _capi.abi3.so 失败（{str(e)[:60]}——OHOS 权限模型——"
          "核心消费验证无法执行）")
    if not _check_codesign(_capi_src):
        print("WARN: _capi.abi3.so 无 .codesign 签名段（构建期签名可能未生效）")
    sys.exit(1)

# 2) ctypes 真实加载（本地 PASS 路径——OHOS 权限模型下 CI 可能受限）
try:
    ctypes.CDLL(_capi_tmp)
    print("PASS: _capi.abi3.so 可加载（ctypes——签名后）")
except OSError as e:
    # OHOS dlopen 权限模型（owner 20001006——CI 用户 100 无法加载——
    # 本地实测可加载）——如实记录 + 签名段验证（签名段存在 ≠ 可加载——
    # 如实说明——不打印误导性 PASS）
    print(f"NOTE: ctypes 加载受限（{str(e)[:60]}——OHOS dlopen 权限模型——"
          "本地实测可加载——环境限制）")
    if _check_codesign(_capi_src):
        print("PASS: _capi.abi3.so 签名段（.codesign）存在（环境限制下最小验证）")
    else:
        print("FAIL: _capi.abi3.so 无 .codesign 签名段")
        sys.exit(1)

# 3) import notmuch2（完整包导入——核心消费验证）——失败必须非零退出
# （R9 伪通过禁止——aireview P1：except 不得吞掉失败——门禁不能假绿）
try:
    import notmuch2
    assert hasattr(notmuch2, "Database"), "Database class missing"
    print("notmuch2 import OK（Database 可用）")
except ImportError as e:
    print(f"FAIL: import notmuch2 失败（{str(e)[:60]}——OHOS 权限模型——"
          "核心消费验证未通过）")
    sys.exit(1)
