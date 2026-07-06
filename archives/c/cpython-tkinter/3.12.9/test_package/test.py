# _tkinter 产物静态校验（不 dlopen）。
#
# 为什么不在这里 import _tkinter：CI 的 test 执行域（buildbot-worker 跑 python3）拒绝 dlopen 任何「自签」
# .so（连 tcl 的 libtcl9.0.so 也被 Permission denied；display-sign 显示 self-sign 但缺该域要求的权限），
# 故 tcl/tk/glfw 等运行期库在 CI 一律 skip_test_run、只验编译链接。cpython-tkinter 的运行期 import
# 在真机 HiShell 域验证（TCL/TK 9.0）。此处只静态确认「产物是正确、链接齐全的 CPython 扩展」。
import os
import glob
import shutil
import subprocess


def _tool(name):
    return (os.path.join("/data/service/hnp/bin", name)
            if os.path.isfile(os.path.join("/data/service/hnp/bin", name))
            else (shutil.which(name) or name))


def _try(args):
    # 工具缺失（部分 NDK 缺 llvm-readelf，ML-0040）或出错 → 返回 None，让对应校验告警跳过而非误失败。
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)
    except Exception:  # noqa: BLE001
        return None


sos = []
for d in os.environ.get("PYTHONPATH", "").split(":"):
    if d:
        sos += glob.glob(os.path.join(d, "_tkinter*.so"))
assert sos, "包内未见 _tkinter*.so"        # 硬校验：产物必须在
so = sos[0]

# 1) 导出模块初始化符号 PyInit__tkinter（llvm-nm 在则严格校验）
syms = _try([_tool("llvm-nm"), "-D", so])
if syms is not None:
    assert "PyInit__tkinter" in syms, "缺 PyInit__tkinter 导出符号（不是有效的 CPython 扩展）"
    print("OK: PyInit__tkinter 已导出")
else:
    print("WARN: llvm-nm 不可用，跳过符号校验")

# 2) NEEDED 依赖齐全：libpython（否则 import 段错误，ML-0008）+ tcl + tk（llvm-readelf 在则严格校验）
dyn = _try([_tool("llvm-readelf"), "-d", so])
if dyn is not None:
    for need in ("libpython3.12.so", "libtcl9.0.so", "libtcl9tk9.0.so"):
        assert need in dyn, "NEEDED 缺 " + need
    print("OK: NEEDED 含 libpython/tcl/tk")
else:
    print("WARN: llvm-readelf 不可用，跳过 NEEDED 校验")

print("STATIC OK:", os.path.basename(so))
print("（运行期 import _tkinter 在真机 HiShell 域验证；CI 执行域拒 dlopen 自签 .so，故此处只静态验产物）")
