#!/usr/bin/env python3
"""消费测试：验证 cogl 1.22.8 安装布局 + 库可用 + 纯 CPU 上游测试。

cogl（GNOME）是低层 OpenGL 图形库（library 包）。本测试验证：
1. lib/libcogl.so 库文件存在
2. include/cogl/cogl.h 头文件存在（上游实际装到 include/cogl/cogl/cogl.h）
3. 编译链接并运行 consumer.c（解析 cogl_get_proc_address 符号）——
   证明库可被实际链接和加载，避免空壳测试（R34/R40）
4. 编译并实跑上游纯 CPU 测试子集（upstream_unit/ 3 用例，逐个
   PASS/FAIL 汇总）——真实本地运行结果（OHOS 无 GL 渲染环境：
   /dev/dri 不存在，cogl_context_new(NULL) 直接 segfault，全部
   GL 路径测试不可运行，见 test_package/notes.md 上游测试分析）
终态由各检查结果推导：任一 FAIL 即 exit 1，全部 PASS 才 "ALL PASS"。
"""
import os
import shutil
import subprocess
import sys
import tempfile

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"

# 上游纯 CPU 测试子集（逐用例：main 文件 -> 测试名 -> 是否需 verbose 桩）
UPSTREAM_TESTS = [
    ("up_uu_color_hsl.c", "test_color_hsl", "verbose"),
    ("up_uu_no_gl_header.c", "test_no_gl_header", "none"),
    ("up_uu_version.c", "test_version", "verbose"),
]


def find_clang():
    cc = ""
    for cand in ("/data/service/hnp/bin/clang",
                 "/storage/Users/currentUser/usr/local/bin/clang",
                 os.environ.get("CC") or "",
                 shutil.which("clang") or ""):
        if cand and os.path.isfile(cand):
            cc = cand
            break
    return cc


def main():
    pkg_folder = sys.argv[1]
    failures = 0

    # 1. lib/libcogl.so 库文件存在（shared 库）
    libdir = os.path.join(pkg_folder, "lib")
    lib = os.path.join(libdir, "libcogl.so")
    if os.path.isfile(lib):
        print(f"{PASS} libcogl 库文件存在（libcogl.so）")
    else:
        print(f"{FAIL} libcogl 库文件缺失")
        failures += 1

    # 2. include/cogl/cogl.h 头文件存在（上游安装可能装到
    #    include/cogl/cogl/cogl.h——官方 cogl-1.0.pc 的 Cflags 正是
    #    -I${includedir}/cogl，两种布局都接受）
    hdr = os.path.join(pkg_folder, "include", "cogl", "cogl.h")
    hdr_nested = os.path.join(pkg_folder, "include", "cogl", "cogl", "cogl.h")
    if os.path.isfile(hdr) or os.path.isfile(hdr_nested):
        print(f"{PASS} include/cogl/cogl.h 头文件存在")
    else:
        print(f"{FAIL} cogl.h 头文件缺失")
        failures += 1

    # cogl.h 内部解析 glib 头（cogl 依赖 glib）——test() 已收集全部
    # 依赖（含传递）的 include/libdirs 写入 COGL_TEST_DEP_INCLUDES /
    # COGL_TEST_DEP_LIBDIRS（CONAN_CFLAGS 聚合环境变量在 Conan 2
    # 依赖 cpp_info 而非 env，实测为空不可靠，故走 test() 显式传递）
    dep_incs = [i for i in
                os.environ.get("COGL_TEST_DEP_INCLUDES", "").split() if i]
    dep_libdirs = [d for d in
                   os.environ.get("COGL_TEST_DEP_LIBDIRS", "").split()
                   if d]

    cc = find_clang()
    if not cc:
        print(f"{FAIL} clang 不在 PATH——编译检查跳过，核心链接检查未执行")
        failures += 1

    # 3. 编译链接并运行 consumer.c（解析 cogl_get_proc_address 符号）——
    #    证明 libcogl 可被实际链接和加载（R34 非空壳）。编译或运行任一
    #    失败即 FAIL，避免"坏包放行"的假阳性门禁。
    test_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(test_dir, "consumer.c")
    out_bin = os.path.join(tempfile.gettempdir(), "cogl_consumer.out")
    if cc:
        cmd = [cc, src, "-o", out_bin,
               "-I", os.path.join(pkg_folder, "include"),
               "-I", os.path.join(pkg_folder, "include", "cogl")]
        cmd += [f"-I{d}" for d in dep_incs]
        cmd += [f"-L{d}" for d in dep_libdirs]
        cmd += ["-L", libdir, os.path.join(libdir, "libcogl.so")]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            print(f"{FAIL} consumer 编译链接失败（rc={r.returncode}）")
            print((r.stderr or "")[:400])
            failures += 1
        else:
            # 运行需 libcogl.so 及其依赖（glib/gobject）——LD_LIBRARY_PATH
            # 追加本包 libdir + CONAN_LIBDIR（保留原路径不覆盖）
            env = dict(os.environ)
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                [libdir] + dep_libdirs +
                ([env["LD_LIBRARY_PATH"]] if env.get("LD_LIBRARY_PATH") else []))
            run = subprocess.run([out_bin], capture_output=True, text=True,
                                 timeout=30, env=env)
            if run.returncode == 0 and "resolved ok" in run.stdout:
                print(f"{PASS} consumer 编译链接并运行成功"
                      f"（符号可解析 + libcogl.so 可加载）")
                print(run.stdout.strip())
            else:
                print(f"{FAIL} consumer 运行失败（rc={run.returncode}）")
                print((run.stdout or "")[:200] + (run.stderr or "")[:200])
                failures += 1

    # 4. 上游纯 CPU 测试子集：编译并逐个实跑
    #    背景（真实测量，见 test_package/notes.md）：
    #    - /dev/dri 不存在，无 GL 渲染环境；cogl_context_new(NULL) 在本机
    #      直接 segfault（SIGSEGV，无输出），所有走 test_utils_init 的
    #      上游测试（conform 52 注册用例 + unit 7 例 + micro-perf 1）
    #      全部不可运行——如实记录省略，不冒充通过。
    #    - 纯 CPU 子集 = conform 中不碰 context/framebuffer/纹理渲染的
    #      3 个用例：test_color_hsl / test_no_gl_header / test_version。
    #    - 构建细节：test-version.c 经 <cogl/cogl-util.h> 内部头取
    #      _COGL_STATIC_ASSERT 宏——安装包只有公共头，按上游
    #      cogl-util.h 原样内联该宏（c11 _Static_assert）+ 空
    #      config.h 桩（版本宏由安装头 cogl-defines.h 提供）。
    #      test-color-hsl.c 的上游 fabsf(double) 告警非错误（-g3 -O0
    #      下按双精度比较通过），保持上游源文件零改动。
    if cc:
        updir = os.path.join(test_dir, "upstream_unit")
        workdir = tempfile.mkdtemp(prefix="cogl_upstream_")
        # 空 config.h 桩（必须放在搜索路径最前以遮蔽系统头）
        with open(os.path.join(workdir, "config.h"), "w") as f:
            f.write("/* stub config.h: 安装头自带版本宏，无需额外定义 */\n")
        # 内联 test_utils.h 的最小桩：cogl_test_verbose()（上游该函数
        # 定义于 test-fixtures/test-utils.c 测试基建，非库符号）
        main_tmpl = (
            "#include <glib.h>\n"
            "#include <cogl/cogl.h>\n"
            "extern CoglBool cogl_test_verbose (void);\n"
            "CoglBool cogl_test_verbose (void) { return TRUE; }\n"
            "#define _COGL_STATIC_ASSERT(EXPRESSION, MESSAGE) \\\n"
            "  _Static_assert (EXPRESSION, MESSAGE)\n"
            "extern void %s (void);\n"
            "int main (void) { %s (); return 0; }\n"
        )
        # 上游 test-*.c 头文件里引用 test-fixtures/test-utils.h（测试基建
        # 公共头，非库头）——按上游原样提供最小桩（只声明
        # cogl_test_verbose，main 桩里定义；test_ctx/test_fb 等不引用）
        with open(os.path.join(workdir, "test-utils.h"), "w") as f:
            f.write("/* stub test-utils.h: 最小桩，见上方注释 */\n"
                    "#ifndef _TEST_UTILS_H_\n#define _TEST_UTILS_H_\n"
                    "#include <glib.h>\n"
                    "#include <cogl/cogl.h>\n"
                    "CoglBool\ncogl_test_verbose (void);\n"
                    "#endif\n")
        # test-version.c 用 <cogl/cogl-util.h> 内部头取 _COGL_STATIC_ASSERT
        # ——按上游 cogl-util.h 原样提供最小 shim（c11 _Static_assert，
        # 上游 HAVE_STATIC_ASSERT 分支的展开式）
        shim_inc = os.path.join(workdir, "shim", "cogl")
        os.makedirs(shim_inc, exist_ok=True)
        with open(os.path.join(shim_inc, "cogl-util.h"), "w") as f:
            f.write("/* shim cogl-util.h: 最小桩，见上方注释 */\n"
                    "#ifndef __COGL_UTIL_H\n#define __COGL_UTIL_H\n"
                    "#include <glib.h>\n"
                    "#include <math.h>\n"
                    "#include <cogl/cogl-defines.h>\n"
                    "#define _COGL_STATIC_ASSERT(EXPRESSION, MESSAGE) \\\n"
                    "  _Static_assert (EXPRESSION, MESSAGE)\n"
                    "#endif\n")
        n_run = 0
        n_ok = 0
        for main_name, test_name, need_verbose in UPSTREAM_TESTS:
            src_c = os.path.join(updir, test_name.replace("_", "-") + ".c")
            if not os.path.isfile(src_c):
                print(f"{FAIL} 上游测试源文件缺失: {src_c}")
                failures += 1
                continue
            main_c = os.path.join(workdir, main_name)
            with open(main_c, "w") as f:
                f.write(main_tmpl % (test_name, test_name))
            bin_path = os.path.join(workdir, main_name.replace(".c", ".out"))
            cmd = [cc, main_c, src_c, "-o", bin_path, "-std=c11",
                   # 对齐上游 conform Makefile.am 的 AM_CPPFLAGS
                   "-DCOGL_DISABLE_DEPRECATED",
                   "-I", workdir,
                   # shim 先于安装头：cogl-util.h 只存在 shim 里（内部头
                   # 不随库安装），cogl-defines.h 等仍解析到安装头
                   "-I", os.path.join(workdir, "shim"),
                   "-I", os.path.join(pkg_folder, "include"),
                   "-I", os.path.join(pkg_folder, "include", "cogl")]
            cmd += [f"-I{d}" for d in dep_incs]
            cmd += [f"-L{d}" for d in dep_libdirs]
            cmd += ["-L", libdir, os.path.join(libdir, "libcogl.so")]
            # g_assert_cmpint/g_print 等断言/打印符号来自 glib——
            # 上游 Makefile 的 LDADD 是 libcogl.la + glib + -lm
            cmd += ["-lglib-2.0", "-lm"]
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=180)
            if r.returncode != 0:
                print(f"{FAIL} [upstream] {test_name} 编译失败"
                      f"（rc={r.returncode}）")
                print((r.stderr or "")[:400])
                failures += 1
                continue
            env = dict(os.environ)
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                [libdir] + dep_libdirs +
                ([env["LD_LIBRARY_PATH"]] if env.get("LD_LIBRARY_PATH") else []))
            run = subprocess.run([bin_path], capture_output=True, text=True,
                                 timeout=60, env=env)
            n_run += 1
            if run.returncode == 0:
                n_ok += 1
                print(f"{PASS} [upstream] {test_name} 实跑通过（rc=0）")
                if run.stdout.strip():
                    print("  " + run.stdout.strip().splitlines()[0][:120])
            else:
                print(f"{FAIL} [upstream] {test_name} 实跑失败"
                      f"（rc={run.returncode}）")
                print((run.stdout or "")[:200] + (run.stderr or "")[:200])
                failures += 1
        total = len(UPSTREAM_TESTS)
        print(f"NOTE: 上游纯 CPU 子集实跑汇总：运行 {n_run}/{total}，"
              f"通过 {n_ok}/{total}，失败 {n_run - n_ok}")
        print(f"NOTE: 上游 GL 路径测试（conform 其余 49 注册用例 + "
              f"unit 7 例 + micro-perf 1 + unported 12）需 GL 渲染环境"
              f"——OHOS 无 /dev/dri，cogl_context_new() 实测 segfault，"
              f"如实记录省略（0 运行，非失败）")
        shutil.rmtree(workdir, ignore_errors=True)
    else:
        print(f"{FAIL} 上游纯 CPU 子集未运行（无 clang）")
        failures += 1

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
