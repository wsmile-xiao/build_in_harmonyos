#!/usr/bin/env python3
"""kup-backup 消费者冒烟测试（L0c 测试源文件）。

上游 kup 0.10.0 无任何测试用例（无 tests/ 目录、CMakeLists 无 test 目标，
MANIFEST 如实申报 0）。本脚本为适配后补全的 smoke test：真实执行安装后的
三个二进制，验证 ELF 加载与 Qt6/KF6/libgit2 运行时依赖完整解析。

断言：
  1. kup-filedigger --version → 退出 0 且输出含 0.10.0
     （KAboutData/QCommandLineParser 在 GUI 创建前处理 --version；
      filedigger 链接 KIO/KXmlGui/libgit2 全家，动态加载完整走通）
  2. kup-purger --version → 同上
  3. kup-daemon → 退出 0 且输出含 "not enabled"
     （无 kuprc 时 Backups enabled 默认 false，daemon 在 AboutData/
      parser 之前早退——上游行为，如实断言；证明 QApplication 构造 +
      KSharedConfig/kconfig 读路径 + qCCritical 日志通道走通）

超时由 subprocess.run(timeout=60) 兜底（OHOS worker 无 shell timeout
命令，CI #60869 实测）。二进制路径经 KUP_BIN_DIR 传入（CI #60877 实测
conanrun PATH 不含被测试包 bin 目录）。
"""
import os
import subprocess
import sys


def run_bin(bin_path, args, expect_substr):
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        proc = subprocess.run(
            [bin_path] + args, env=env, capture_output=True,
            text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        print("[FAIL] %s 无法启动: %s" % (bin_path, exc))
        return 1
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        print("[FAIL] %s %s 退出码 %d" % (
            os.path.basename(bin_path), " ".join(args), proc.returncode))
        print(out)
        return 1
    if expect_substr.lower() not in out.lower():
        print("[FAIL] %s 输出未含 %r" % (
            os.path.basename(bin_path), expect_substr))
        print(out)
        return 1
    first_line = out.strip().splitlines()[0] if out.strip() else "(no output)"
    print("[PASS] %s %s → %s" % (
        os.path.basename(bin_path), " ".join(args), first_line))
    return 0


def main():
    bin_dir = os.environ.get("KUP_BIN_DIR", "")
    fails = 0
    for name, args, expect in (
        ("kup-filedigger", ["--version"], "0.10.0"),
        ("kup-purger", ["--version"], "0.10.0"),
        ("kup-daemon", [], "not enabled"),
    ):
        path = os.path.join(bin_dir, name) if bin_dir else name
        if not os.path.isfile(path):
            print("[FAIL] 二进制不存在: %s" % path)
            fails += 1
            continue
        fails += run_bin(path, args, expect)
    if fails:
        print("[FAIL] kup-backup 冒烟测试 %d 项失败" % fails)
        return 1
    print("[PASS] ALL kup-backup SMOKE ASSERTIONS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
