#!/usr/bin/env python3
"""消费测试：验证 canvec 1.0.0 安装布局 + 真实运行 usage。

canvec 是纯 Python 单文件脚本——运行时需要外部 shp2pgsql（PostGIS）
执行数据提取，沙箱无此工具（系统级阻塞，如实记录）；本测试验证：
1. bin/canvec 可执行文件存在
2. lib/canvec.py 模块存在
3. bin/canvec 无参数真实运行 → 打印 usage（上游 __main__ len(args)<4 分支）
4. 上游无测试套件（0/0 如实）——本消费测试为独立用例
"""
import subprocess
import sys

PASS = "PASS:"
NOTE = "NOTE:"


def main():
    pkg_folder = sys.argv[1]

    import os
    bin_canvec = os.path.join(pkg_folder, "bin", "canvec")
    lib_canvec = os.path.join(pkg_folder, "lib", "canvec.py")

    # 1. bin/canvec 存在且可执行
    if not os.path.isfile(bin_canvec) or not os.access(bin_canvec, os.X_OK):
        print("FAIL: bin/canvec 不存在或不可执行")
        sys.exit(1)
    print(f"{PASS} bin/canvec 可执行文件存在")

    # 2. lib/canvec.py 模块存在
    if not os.path.isfile(lib_canvec):
        print("FAIL: lib/canvec.py 模块缺失")
        sys.exit(1)
    print(f"{PASS} lib/canvec.py 模块存在")

    # 3. 真实运行 usage（无参数——上游 __main__ len(args)<4 打印 usage）
    r = subprocess.run([sys.executable, bin_canvec], capture_output=True, text=True,
                       timeout=30)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        print(f"FAIL: bin/canvec 无参数运行退出码 {r.returncode}")
        print(out[:400])
        sys.exit(1)
    if "Usage: python canvec.py" not in out:
        print("FAIL: usage 输出缺少 'Usage: python canvec.py'")
        print(out[:400])
        sys.exit(1)
    print(f"{PASS} canvec 无参数真实运行输出 usage")

    # 4. 运行阻塞披露（系统级阻塞——外部 shp2pgsql 缺失）
    print(f"{NOTE} 运行阻塞（系统级）：数据提取需外部 shp2pgsql（PostGIS），"
          f"OHOS 沙箱无此工具——usage/布局验证不受影响，如实记录")

    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
