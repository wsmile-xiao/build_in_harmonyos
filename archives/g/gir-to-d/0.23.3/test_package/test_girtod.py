#!/usr/bin/env python3
"""test_girtod.py — L0c-visible consumer test for gir-to-d 0.23.3 (R34 真实调用).

把真实的最小 GObject-Introspection 输入（.gir + APILookup.txt）喂给**打包出来
的** girtod，校验它真的生成了预期的 D 绑定源码。

断言依据来自实测（不是猜测）：
  - `girtod --version` 输出 `GIR to D vX.Y.Z`（版本经 -J./ 从生成的 VERSION 文件
    编译进二进制）；
  - 调用形式 `girtod -i <inputDir> -g <girDir> -o <outputDir>`；gir 文件需用
    `-g` 指明搜索目录，否则报 "Couldn't find the gir file"；
  - APILookup.txt 中 `file:` 必须出现在 `wrap:` **之后**（否则报
    "Found: 'file' before wrap."），且不存在 `pkg:` 键（报 "Unknown key"）；
  - 输出布局为 `<srcDir>/<Class>.d`、`<srcDir>/c/functions.d`、`<srcDir>/c/types.d`。

Usage: test_girtod.py <package_folder>
"""
import os
import shutil
import subprocess
import sys
import tempfile

FIXTURE_FILES = ("Test-1.0.gir", "GObject-2.0.gir", "APILookup.txt")


def run_girtod(binary, input_dir, gir_dir, output_dir):
    return subprocess.run(
        [binary, "-i", input_dir, "-g", gir_dir, "-o", output_dir],
        capture_output=True, text=True,
    )


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_girtod.py <package_folder>")
    pkg = sys.argv[1]

    binary = os.path.join(pkg, "bin", "girtod")
    if not os.path.isfile(binary):
        raise AssertionError(f"packaged binary missing: {binary}")
    if not os.access(binary, os.X_OK):
        raise AssertionError(f"packaged binary is not executable: {binary}")

    here = os.path.dirname(os.path.abspath(__file__))
    fixtures = os.path.join(here, "fixtures")
    for name in FIXTURE_FILES:
        path = os.path.join(fixtures, name)
        if not os.path.isfile(path):
            raise AssertionError(f"fixture missing: {path}")

    checks = []

    # ① 二进制可执行且自报版本（无 LD_LIBRARY_PATH 依赖，NEEDED 仅 libc）
    #    精确断言到具体版本号：若配方漏传 GIR_TO_D_VERSION，GNUmakefile 会回退到
    #    上游写死的 v0.23.1，此处必须失败（仅断言前缀会漏掉该回归）。
    r = subprocess.run([binary, "--version"], capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(
            f"--version failed (rc={r.returncode}): {r.stderr.strip()}")
    version_out = (r.stdout or "").strip()
    checks.append(("--version reports exactly 'GIR to D v0.23.3'",
                   version_out == "GIR to D v0.23.3", version_out))

    with tempfile.TemporaryDirectory() as work:
        in_dir = os.path.join(work, "in")
        out_dir = os.path.join(work, "out")
        os.makedirs(in_dir)
        for name in FIXTURE_FILES:
            shutil.copy2(os.path.join(fixtures, name),
                         os.path.join(in_dir, name))

        r = run_girtod(binary, in_dir, in_dir, out_dir)
        if r.returncode != 0:
            raise AssertionError(
                f"girtod failed (rc={r.returncode}): "
                f"{(r.stdout or '') + (r.stderr or '')}".strip())
        noise = ((r.stdout or "") + (r.stderr or "")).strip()
        checks.append(("girtod runs cleanly on a real .gir (no error output)",
                       "Error" not in noise and "Unknown key" not in noise,
                       noise or "(no output)"))

        # ② 输出布局（实测：srcDir=<wrap 名> → test/…）
        module_file = os.path.join(out_dir, "test", "Widget.d")
        c_functions = os.path.join(out_dir, "test", "c", "functions.d")
        c_types = os.path.join(out_dir, "test", "c", "types.d")
        for path, label in ((module_file, "class module"),
                            (c_functions, "c/functions.d"),
                            (c_types, "c/types.d")):
            checks.append((f"generated {label}",
                           os.path.isfile(path), path))

        if os.path.isfile(module_file):
            text = open(module_file, encoding="utf-8").read()
            checks.append(("class module declares the right D module",
                           "module test.Widget;" in text,
                           "module test.Widget;"))
            checks.append(("class derives from the GObject base wrapper",
                           "class Widget : ObjectG" in text, "class Widget : ObjectG"))
            checks.append(("class exposes the C struct accessor",
                           "getWidgetStruct" in text, "getWidgetStruct"))
            checks.append(("class exposes the wrapped C type",
                           "TestWidget*" in text, "TestWidget*"))

        if os.path.isfile(c_functions):
            text = open(c_functions, encoding="utf-8").read()
            checks.append(("extern(C) block declares the introspected get_type",
                           "GType test_widget_get_type();" in text,
                           "GType test_widget_get_type();"))
            checks.append(("extern(C) block declares the introspected constructor",
                           "TestWidget* test_widget_new();" in text,
                           "TestWidget* test_widget_new();"))
            checks.append(("shared library name taken from the .gir",
                           '"libtest.so"' in text, '["libtest.so"]'))

        if os.path.isfile(c_types):
            text = open(c_types, encoding="utf-8").read()
            checks.append(("c/types.d re-exports the GObject c types",
                           "public import gobject.c.types;" in text,
                           "public import gobject.c.types;"))
            checks.append(("c/types.d declares the opaque struct",
                           "struct TestWidget;" in text, "struct TestWidget;"))

    failed = [c for c in checks if not c[1]]
    for label, ok, detail in checks:
        print(f"{'ok  ' if ok else 'FAIL'} - {label}" + ("" if ok else f"  [{detail}]"))
    print(f"1..{len(checks)}")
    if failed:
        raise SystemExit(f"FAIL: {len(failed)}/{len(checks)} checks failed")
    print("OK: gir-to-d 0.23.3 girtod-driven consumer check")


if __name__ == "__main__":
    main()
