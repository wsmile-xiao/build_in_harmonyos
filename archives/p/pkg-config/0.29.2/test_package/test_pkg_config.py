#!/usr/bin/env python3
"""pkg-config 消费者功能测试 —— 真实执行 pkg-config 并完成一次 .pc 查询往返。

由 test_package/conanfile.py 的 test() 调用：

    python3 test_pkg_config.py <pkg-config-prefix>

pkg-config 是编译期辅助工具（消费方 autotools 通过它取 CFLAGS/LIBS），
它的价值只能通过「真跑起来 + 真查一次 .pc」验证，所以本脚本不做
文件存在性打转：

  1. 可执行性    --version 必须输出 0.29.2
  2. 查询往返    自造 probe.pc，验证 --modversion/--libs/--cflags/--variable，
                 以及 ${prefix} → ${exec_prefix} → ${libdir} 的递归展开
  3. 错误语义    查询不存在的模块必须以非 0 退出（工具契约，而非打印完即通过）
  4. 鸿蒙特有    triplet wrapper（补丁 0010：HMDFS 不支持硬链接，改为脚本转发参数）
  5. 鸿蒙特有    share/aclocal/pkg.m4 随包分发（消费方 autoreconf 才能展开
                 PKG_CHECK_MODULES）
  6. 鸿蒙特有    产物为 aarch64 小端 ELF 且非空（内嵌 glib 已静态并入）

退出码 0 表示全部断言通过；末尾打印 "N checks, M failures"。
"""
import os
import shutil
import subprocess
import sys
import tempfile

PASSED = 0
FAILED = 0


def check(cond, ok_msg, fail_msg):
    """记录一条断言并打印结果。"""
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print("  [ok] %s" % ok_msg)
    else:
        FAILED += 1
        print("  [FAIL] %s" % fail_msg)
    return bool(cond)


def run(cmd, env):
    """执行一条 shell 命令，返回 (returncode, stdout+stderr)。

    统一经 /bin/sh 执行：pkg-config 是 CLI 工具，要验证的正是它在 shell 下的
    命令行行为；二进制本身用绝对路径传入，避免 OHOS 的 python3 走
    os.posix_spawn 时不搜 PATH（裸名命令 FileNotFoundError）。
    """
    proc = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env
    )
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def make_env(bindir):
    """消费方视角的环境：把工具的 bin/ 挂上 PATH（tool_requires 的实际语义）。

    triplet wrapper 内部是 `exec pkg-config "$@"`，按设计依赖 PATH 解析；
    这里显式把 bindir 前置，保证断言的是「正确消费时可用」，而不是
    碰巧继承了某个 PATH。
    """
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([bindir, env.get("PATH", "")])
    return env


def main():
    if len(sys.argv) != 2:
        print("usage: test_pkg_config.py <pkg-config-prefix>")
        return 2

    prefix = sys.argv[1]
    bindir = os.path.join(prefix, "bin")
    pc_bin = os.path.join(bindir, "pkg-config")
    env = make_env(bindir)
    print("pkg-config consumer test — prefix: %s" % prefix)

    # ── 1. 可执行性 ────────────────────────────────────────────────
    rc, out = run('"%s" --version' % pc_bin, env)
    check(rc == 0, "--version 可执行（exit 0）", "--version 失败: %s" % out.strip())
    check("0.29.2" in out, "--version => 0.29.2", "--version 未输出 0.29.2，实测: %r" % out)

    work = tempfile.mkdtemp(prefix="pkgconfig-selftest-")
    try:
        # ── 2. 真实功能往返：自造 .pc 文件并查询 ────────────────────
        pc_dir = os.path.join(work, "pc")
        os.makedirs(pc_dir, exist_ok=True)
        pc_file = os.path.join(pc_dir, "probe.pc")
        with open(pc_file, "w", encoding="utf-8") as f:
            f.write(
                "prefix=/usr/local\n"
                "exec_prefix=${prefix}\n"
                "libdir=${exec_prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "\n"
                "Name: probe\n"
                "Description: pkg-config self-test dummy module\n"
                "Version: 1.2.3\n"
                "Libs: -L${libdir} -lprobe\n"
                "Cflags: -I${includedir}\n"
            )
        check(os.path.isfile(pc_file), "probe.pc 已写入 %s" % pc_dir, "probe.pc 写入失败")

        query_env = dict(env)
        query_env["PKG_CONFIG_PATH"] = pc_dir

        rc, out = run('"%s" --modversion probe' % pc_bin, query_env)
        check(
            rc == 0 and out.strip() == "1.2.3",
            "--modversion probe => 1.2.3",
            "--modversion probe 期望 1.2.3（exit 0），实测 rc=%d: %r" % (rc, out),
        )

        rc, out = run('"%s" --libs probe' % pc_bin, query_env)
        check(
            rc == 0 and "-lprobe" in out,
            "--libs probe => %s" % out.strip(),
            "--libs probe 期望含 -lprobe，实测 rc=%d: %r" % (rc, out),
        )

        rc, out = run('"%s" --cflags probe' % pc_bin, query_env)
        check(
            rc == 0 and "-I/usr/local/include" in out,
            "--cflags probe => %s" % out.strip(),
            "--cflags probe 期望含 -I/usr/local/include，实测 rc=%d: %r" % (rc, out),
        )

        # 变量递归展开（pkg-config 的核心能力：${prefix} → ${exec_prefix} → ${libdir}）
        rc, out = run('"%s" --variable=libdir probe' % pc_bin, query_env)
        check(
            rc == 0 and out.strip() == "/usr/local/lib",
            "--variable=libdir => /usr/local/lib（变量递归展开正确）",
            "--variable=libdir 期望 /usr/local/lib，实测 rc=%d: %r" % (rc, out),
        )

        rc, out = run('"%s" --variable=prefix probe' % pc_bin, query_env)
        check(
            rc == 0 and out.strip() == "/usr/local",
            "--variable=prefix => /usr/local",
            "--variable=prefix 期望 /usr/local，实测 rc=%d: %r" % (rc, out),
        )

        # ── 3. 错误语义：查不存在的模块必须非 0 退出 ────────────────
        rc, out = run('"%s" --exists nosuchmodule-pkgconfig-selftest' % pc_bin, query_env)
        check(
            rc != 0,
            "--exists 未知名模块 => 非 0 退出（错误语义正确）",
            "--exists 未知名模块竟然 exit 0，工具契约错误",
        )

        # ── 4. 鸿蒙特有：triplet wrapper 可用 ──────────────────────
        # OHOS 上上游原本用 `ln -f` 建 triplet 硬链接，HMDFS 不允许，
        # 改为 wrapper 脚本（补丁 0010）。此处验证它真的能被 exec 并正确转发参数。
        wrapper = os.path.join(bindir, "aarch64-unknown-linux-ohos-pkg-config")
        check(os.path.isfile(wrapper), "triplet wrapper 已安装", "triplet wrapper 未安装: %s" % wrapper)
        if os.path.isfile(wrapper):
            rc, out = run('"%s" --variable=prefix probe' % wrapper, query_env)
            check(
                rc == 0 and out.strip() == "/usr/local",
                "triplet wrapper 正确转发参数（鸿蒙特有：脚本替代硬链接）",
                "triplet wrapper 转发失败，实测 rc=%d: %r" % (rc, out),
            )

        # ── 5. 鸿蒙特有：pkg.m4 随包分发 ───────────────────────────
        m4 = os.path.join(prefix, "share", "aclocal", "pkg.m4")
        check(os.path.isfile(m4), "pkg.m4 随包分发", "pkg.m4 未随包分发: %s" % m4)
        if os.path.isfile(m4):
            with open(m4, encoding="utf-8", errors="ignore") as f:
                m4_text = f.read()
            check(
                "PKG_CHECK_MODULES" in m4_text,
                "pkg.m4 含 PKG_CHECK_MODULES 宏（鸿蒙特有：aclocal 宏随包分发）",
                "pkg.m4 不含 PKG_CHECK_MODULES 宏定义",
            )

        # ── 6. 鸿蒙特有：产物是真实 OHOS ELF 且非空 ────────────────
        size = os.path.getsize(pc_bin) if os.path.isfile(pc_bin) else 0
        check(size > 0, "bin/pkg-config 非空（%d 字节）" % size, "bin/pkg-config 缺失或为空")
        if size > 0:
            with open(pc_bin, "rb") as f:
                head = f.read(20)
            is_elf = head[:4] == b"\x7fELF"
            is64 = head[4] == 2
            is_le = head[5] == 1
            machine = int.from_bytes(head[18:20], "little")
            check(
                is_elf,
                "bin/pkg-config 是 ELF 文件",
                "bin/pkg-config 不是 ELF 文件，头部: %r" % head[:4],
            )
            check(
                is64 and is_le and machine == 183,  # EM_AARCH64
                "bin/pkg-config 是 aarch64 小端 ELF（鸿蒙特有）",
                "bin/pkg-config 非 OHOS 形态 ELF（64=%s, LE=%s, machine=%d）"
                % (is64, is_le, machine),
            )
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print("pkg-config consumer test: %d checks, %d failures" % (PASSED, FAILED))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
