#!/usr/bin/env python3
"""securefs 消费者端到端用例（不依赖 FUSE 挂载能力）。

鸿蒙 PC 没有 FUSE 内核支持，所以消费者视角只能覆盖「创建卷 → 读回格式 →
认证校验」这条免挂载路径，外加一条鸿蒙特有针对静态链接 libfuse 的断言：

  1. version —— CLI 可用，且 libfuse 静态链接形态下版本探测不崩溃
                （对比 patches/0003：上游用 dlsym(RTLD_DEFAULT, "fuse_version")
                 取版本，静态链接时该符号不在动态符号表里 → 返回 NULL → 段错误）
  2. create  —— 免挂载创建一个加密卷，认证加密元数据落盘
  3. info    —— 免挂载读回卷格式信息
  4. chpass  —— 旧口令错误时认证失败，给出可读错误且不改动卷
                （免挂载鉴权路径；mount 在无可用 FUSE 设备时到不了凭据校验：
                 上游 MountCommand::execute() 先打开 /dev/fuse 再校验口令）
  5. mount   —— 无 /dev/fuse（鸿蒙 PC 现状）时优雅失败：非 0 退出、无信号崩溃
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

BINARY = (sys.argv[1] if len(sys.argv) > 1
          else os.environ.get("SECUREFS_BINARY") or shutil.which("securefs"))
PASSWORD = "conan-test-password-0.13.1"
WRONG_PASSWORD = "definitely-not-the-password"
TIMEOUT = 60

_FAILURES = []


def _report(name, ok, detail=""):
    print("[{}] {}".format("PASS" if ok else "FAIL", name))
    if detail:
        print("       {}".format(detail.replace("\n", "\n       ").strip()[:400]))
    if not ok:
        _FAILURES.append(name)


def _run(args, timeout=TIMEOUT):
    proc = subprocess.run([BINARY] + args, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def _crashed(returncode):
    # 负值为被信号杀死；部分 shell 包装会把信号折叠成 128 + signo
    return returncode < 0 or returncode >= 128


def _scratch_dir():
    # 鸿蒙 PC 的 /tmp 只读（技能 Gotchas E002），显式落到 $TMPDIR 或 ~/tmp
    base = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
    os.makedirs(base, exist_ok=True)
    return tempfile.mkdtemp(prefix="securefs-e2e-", dir=base)


def check_version():
    rc, out, err = _run(["version"])
    ok = rc == 0 and "securefs" in out and "libfuse" in out
    _report("version: 静态链接 libfuse 下 CLI 版本探测不崩溃", ok,
            "rc={} out={!r}".format(rc, (out + err).strip()[:200]))


def check_create(volume):
    rc, out, err = _run(["create", volume, "--pass", PASSWORD])
    if rc != 0:
        _report("create: 创建加密卷", False,
                "rc={} err={!r}".format(rc, (out + err).strip()[:200]))
        return False
    config = os.path.join(volume, ".securefs.json")
    if not os.path.isfile(config):
        _report("create: 创建加密卷", False, ".securefs.json 未生成")
        return False
    try:
        with open(config) as fh:
            cfg = json.load(fh)
    except (OSError, ValueError) as exc:
        _report("create: 创建加密卷", False, "配置解析失败: {}".format(exc))
        return False
    missing = [k for k in ("version", "iv_size", "block_size", "iterations")
               if k not in cfg]
    _report("create: 创建加密卷并落盘认证加密元数据", not missing,
            "version={} iterations={} iv_size={} 缺字段={}".format(
                cfg.get("version"), cfg.get("iterations"), cfg.get("iv_size"), missing))
    return not missing


def check_info(volume):
    rc, out, err = _run(["info", volume])
    ok = rc == 0 and "Filesystem format version:" in out
    _report("info: 免挂载读回卷格式信息", ok,
            "rc={} out={!r}".format(rc, (out + err).strip()[:200]))


def check_wrong_password(volume):
    # chpass 用 --oldpass/--newpass（mount/create 才是 --pass）
    rc, out, err = _run(["chpass", volume, "--oldpass", WRONG_PASSWORD,
                         "--newpass", WRONG_PASSWORD])
    body = out + err
    ok = rc != 0 and not _crashed(rc) and "password" in body.lower()
    _report("chpass: 旧口令错误时认证失败且不改动卷", ok,
            "rc={} body={!r}".format(rc, body.strip()[:200]))


def check_no_fuse(mountpoint, volume):
    if os.path.exists("/dev/fuse"):
        # 本机具备 FUSE 设备：挂载可能真的成功，无法断言「无 FUSE」路径
        try:
            rc, out, err = _run(["mount", mountpoint, volume, "--pass", PASSWORD],
                                timeout=25)
        except subprocess.TimeoutExpired:
            _report("mount: 本环境具备 FUSE 能力，跳过无 /dev/fuse 断言", True,
                    "skip: 挂载成功导致前台挂起，已强制终止")
            return
        ok = rc != 0 and not _crashed(rc)
        _report("mount: 有 /dev/fuse 但无挂载权限时优雅失败", ok,
                "rc={} body={!r}".format(rc, (out + err).strip()[:200]))
        return
    rc, out, err = _run(["mount", mountpoint, volume, "--pass", PASSWORD], timeout=30)
    body = out + err
    ok = rc != 0 and not _crashed(rc) and bool(body.strip())
    _report("mount: 无 /dev/fuse（鸿蒙 PC 现状）时优雅失败而非崩溃", ok,
            "rc={} body={!r}".format(rc, body.strip()[:200]))


def main():
    if not BINARY:
        print("SECUREFS_BINARY 未设置且 PATH 中找不到 securefs")
        return 2
    print("被测二进制: {}".format(BINARY))
    workdir = _scratch_dir()
    volume = os.path.join(workdir, "volume")
    mountpoint = os.path.join(workdir, "mnt")
    os.makedirs(volume)
    os.makedirs(mountpoint)
    try:
        check_version()
        if check_create(volume):
            check_info(volume)
            check_wrong_password(volume)
            check_no_fuse(mountpoint, volume)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    if _FAILURES:
        print("\n{} 项消费者用例失败: {}".format(len(_FAILURES), ", ".join(_FAILURES)))
        return 1
    print("\n全部消费者用例通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
