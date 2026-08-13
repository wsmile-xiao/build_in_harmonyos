#!/usr/bin/env python3
"""test_package consumer test for pycairo 1.29.0 on HarmonyOS PC.

真实调用 cairo 库 API（非空壳）：7 个独立检查点 —
1. 版本/常量 API（cairo_version / CAIRO_VERSION / pycairo version）
2. ImageSurface + Context 绘制并写出 PNG（走 cairo 渲染栈 + png 后端）
3. Matrix 变换数值验证（translate + scale + transform_point）

任一检查失败即退出码 1；全部通过输出总结行。
"""

import os
import sys
import tempfile

import cairo

failures = []


def check(name, cond):
    if cond:
        print(f"PASS: {name}")
    else:
        print(f"FAIL: {name}")
        failures.append(name)


# 1. 版本/常量 API
check("cairo_version_int", cairo.cairo_version() == cairo.CAIRO_VERSION)
check("cairo_version_string", cairo.cairo_version_string() == cairo.CAIRO_VERSION_STRING)
check("pycairo_version", cairo.version == "1.29.0")

# 2. ImageSurface + Context 绘制 + PNG 写出
surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 128, 128)
ctx = cairo.Context(surface)
ctx.set_source_rgb(0.1, 0.5, 0.9)
ctx.rectangle(16, 16, 64, 64)
ctx.fill()
# v1.29.0 无 Surface.get_status()：cairo 状态经异常上报（上游 test_surface.py
# test_context_manager 同款模式：finish 后再操作抛 cairo.Error，status=SURFACE_FINISHED）
finished = cairo.ImageSurface(cairo.FORMAT_ARGB32, 8, 8)
finished.finish()
try:
    finished.show_page()
    check("error_status", False)
except cairo.Error as e:
    check("error_status", e.status == cairo.Status.SURFACE_FINISHED)
fd, png_path = tempfile.mkstemp(suffix=".png")
os.close(fd)
try:
    surface.write_to_png(png_path)
    check("write_to_png", os.path.getsize(png_path) > 0)
finally:
    os.unlink(png_path)

# 3. Matrix 变换数值验证
m = cairo.Matrix()
m.translate(10, 20)
m.scale(2, 2)
x, y = m.transform_point(5, 5)
check("matrix_transform", abs(x - 20.0) < 1e-9 and abs(y - 30.0) < 1e-9)

# 4. Pattern + Context 交互
pattern = cairo.SolidPattern(1.0, 0.0, 0.0, 0.5)
check("solid_pattern", pattern.get_rgba()[3] == 0.5)

if failures:
    print(f"test_pycairo: {len(failures)} FAILED: {failures}")
    sys.exit(1)
print("test_pycairo: ALL CHECKS PASSED")
