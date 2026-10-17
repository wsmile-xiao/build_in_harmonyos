#!/usr/bin/env python3
"""消费测试驱动：验证 clutter 1.26.4 安装布局 + 库可用（R34/R40）。

检查项：
  1. lib/libclutter-1.0.so 存在（shared 库产物）
  2. include/clutter-1.0/clutter/clutter.h 存在（公共头）
  3. clutter-1.0.pc 已安装（下游 pkg-config 可解析）
  4. 编译链接并**运行** consumer.c：实质调用 Clutter 免显示 API
     （版本宏 / 颜色换算 / 单位换算 / Actor 生命周期与属性系统），
     证明库可被真实链接、加载并执行库内代码（非空壳测试）

编译参数优先走 pkg-config（真实消费者的标准路径，同时验证安装出的
.pc 元数据与 Requires 链可用）；pkg-config 不可用时回退到手工
-I/-L 拼接（依赖列表由 test_package/conanfile.py 经环境变量传入）。
任一检查失败即 exit 1；全部通过输出 ALL PASS。
"""
import os
import shutil
import subprocess
import sys
import tempfile

PASS = "PASS:"
FAIL = "FAIL:"


def find_clang():
    for cand in ("/data/service/hnp/bin/clang",
                 "/storage/Users/currentUser/usr/local/bin/clang",
                 os.environ.get("CC") or "",
                 shutil.which("clang") or ""):
        if cand and os.path.isfile(cand):
            return cand
    return ""


def find_pkg_config():
    for cand in ("/data/service/hnp/bin/pkg-config",
                 shutil.which("pkg-config") or ""):
        if cand and os.path.isfile(cand):
            return cand
    return ""


def pkg_config_flags(pc_bin, pkg_folder, dep_libdirs, kind):
    """取 clutter-1.0 的 cflags / libs（真实消费者路径）。

    PKG_CONFIG_PATH 先指向本包 lib/pkgconfig，再逐个追加依赖包的
    lib/pkgconfig——这样 cogl 等依赖解析到各包**自带**的 .pc（例如
    cogl-1.0.pc 的 Cflags 为 -I${includedir}/cogl，正是
    `#include <cogl/cogl.h>` 能命中所需）。
    """
    if not pc_bin:
        return []
    paths = [os.path.join(pkg_folder, "lib", "pkgconfig")]
    for d in dep_libdirs:
        p = os.path.join(d, "pkgconfig")
        if os.path.isdir(p):
            paths.append(p)
    env = dict(os.environ)
    env["PKG_CONFIG_PATH"] = os.pathsep.join(paths)
    try:
        r = subprocess.run([pc_bin, kind, "clutter-1.0"],
                           capture_output=True, text=True, timeout=60, env=env)
    except Exception:
        return []
    if r.returncode != 0:
        return []
    return r.stdout.split()


def main():
    pkg_folder = sys.argv[1]
    failures = 0

    libdir = os.path.join(pkg_folder, "lib")
    lib = os.path.join(libdir, "libclutter-1.0.so")
    if os.path.isfile(lib):
        print(f"{PASS} libclutter-1.0.so 存在")
    else:
        print(f"{FAIL} libclutter-1.0.so 缺失")
        failures += 1

    hdr_nested = os.path.join(pkg_folder, "include", "clutter-1.0",
                              "clutter", "clutter.h")
    hdr = os.path.join(pkg_folder, "include", "clutter", "clutter.h")
    if os.path.isfile(hdr_nested) or os.path.isfile(hdr):
        print(f"{PASS} clutter.h 头文件存在")
    else:
        print(f"{FAIL} clutter.h 头文件缺失")
        failures += 1

    pc = os.path.join(libdir, "pkgconfig", "clutter-1.0.pc")
    if os.path.isfile(pc):
        print(f"{PASS} clutter-1.0.pc 已安装（下游 pkg-config 可解析）")
    else:
        print(f"{FAIL} clutter-1.0.pc 缺失")
        failures += 1

    dep_incs = [i for i in
                os.environ.get("CLUTTER_TEST_DEP_INCLUDES", "").split() if i]
    dep_libdirs = [d for d in
                   os.environ.get("CLUTTER_TEST_DEP_LIBDIRS", "").split()
                   if d]

    cc = find_clang()
    if not cc:
        print(f"{FAIL} clang 不在 PATH —— 核心链接检查未执行")
        failures += 1
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)

    test_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(test_dir, "consumer.c")
    out_bin = os.path.join(tempfile.gettempdir(), "clutter_consumer.out")

    cmd = [cc, src, "-o", out_bin, "-std=c11"]
    pc_bin = find_pkg_config()
    pc_cflags = pkg_config_flags(pc_bin, pkg_folder, dep_libdirs, "--cflags")
    pc_libs = pkg_config_flags(pc_bin, pkg_folder, dep_libdirs, "--libs")
    if pc_cflags and pc_libs:
        print("NOTE: 使用 pkg-config 解析 clutter-1.0（消费者标准路径）")
        cmd += pc_cflags + pc_libs
    else:
        print("NOTE: pkg-config 不可用，回退手工 -I/-L 拼接")
        cmd += ["-I", os.path.join(pkg_folder, "include", "clutter-1.0"),
                "-I", os.path.join(pkg_folder, "include", "clutter-1.0",
                                   "clutter"),
                "-I", os.path.join(pkg_folder, "include")]
        cmd += [f"-I{d}" for d in dep_incs]
        # clutter.h/glib 头经依赖包解析；cogl 头在 <inc>/cogl 下
        for d in dep_incs:
            c = os.path.join(d, "cogl")
            if os.path.isdir(c):
                cmd.append(f"-I{c}")
        cmd += [f"-L{d}" for d in dep_libdirs]
        cmd += ["-L", libdir, "-lclutter-1.0",
                "-lglib-2.0", "-lgobject-2.0"]
    cmd += ["-lm"]

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        print(f"{FAIL} consumer 编译链接失败（rc={r.returncode}）")
        print((r.stderr or "")[:800])
        failures += 1
    else:
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [libdir] + dep_libdirs +
            ([env["LD_LIBRARY_PATH"]] if env.get("LD_LIBRARY_PATH") else []))
        run = subprocess.run([out_bin], capture_output=True, text=True,
                             timeout=120, env=env)
        for line in (run.stdout or "").splitlines():
            print("  " + line)
        if run.returncode == 0 and "SUMMARY:" in (run.stdout or ""):
            print(f"{PASS} consumer 编译链接并运行成功（Clutter API 实际调用通过）")
        else:
            print(f"{FAIL} consumer 运行失败（rc={run.returncode}）")
            print((run.stderr or "")[:400])
            failures += 1

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
