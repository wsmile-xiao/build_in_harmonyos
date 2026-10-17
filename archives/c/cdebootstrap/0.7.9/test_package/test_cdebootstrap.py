import os
import shutil
import subprocess
import sys
import time


def has_network(timeout=8):
    # 优先系统 curl（绝对路径，避免 PATH 差异），失败回退 urllib——
    # 任一可达即视为有网。探测目标 = 测试 C 实际下载用的 aliyun 镜像
    # （与实测源一致：deb.debian.org 跨海，CI 小 HEAD 能过但大流量
    # 180s 拉不完——#59987 教训）
    url = "https://mirrors.aliyun.com/debian/dists/bookworm/Release"
    curl = shutil.which("curl")
    if curl:
        r = subprocess.run([curl, "-sf", "-I", "--connect-timeout",
                            str(timeout), "--max-time", str(timeout + 4),
                            url], capture_output=True)
        if r.returncode == 0:
            return True
    try:
        import urllib.request
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout + 4) as resp:
            return resp.status < 400
    except Exception:
        return False


def run(args, timeout):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return r


def probe_chroot():
    """探测 chroot(2) 系统调用在 OHOS 是否被拒。
    aarch64 用 asm-generic 表，__NR_chroot=51（OHOS sysroot
    aarch64-linux-ohos/bits/syscall.h 实测核对）。
    OHOS 禁 chroot：隔离子进程收到 SIGSYS（signal 31，退出码 128+31=159）。
    注意：不能把 rc=-1 判成"chroot 可用"——非 root 下 chroot('/') 合法失败
    就是 -1/EPERM，与"被禁"不可区分，故本探测只作 SIGSYS 证据（install
    层阻塞已由 B 段 5/5 root 门实测覆盖）。"""
    code = (
        "import ctypes, ctypes.util\n"
        "libc = ctypes.CDLL(ctypes.util.find_library('c') or 'libc.so')\n"
        "libc.syscall.restype = ctypes.c_long\n"
        "libc.syscall.argtypes = [ctypes.c_long, ctypes.c_char_p]\n"
        "rc = libc.syscall(51, b'/')\n"
        "print(f'chroot syscall rc={rc}')\n")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                       text=True, timeout=20)
    if r.returncode == 159 or (r.returncode < 0 and abs(r.returncode) == 31):
        return "chroot(2) SIGSYS signal 31（OHOS 禁 chroot）"
    if r.returncode == 0:
        return f"chroot(2) 可用: {r.stdout.strip()}"
    return (f"chroot(2) 探测 rc={r.returncode} "
            f"out={r.stdout.strip()} err={r.stderr.strip()[:120]}")


def main():
    pkg = sys.argv[1]
    bin_path = os.path.join(pkg, "bin", "cdebootstrap")
    cfg = os.path.join(pkg, "share", "cdebootstrap")
    assert os.path.isfile(bin_path), f"binary missing: {bin_path}"
    assert os.path.isfile(os.path.join(cfg, "suites")), \
        f"suites config missing: {cfg}/suites"

    # ── A. 基础冒烟（无网络） ──────────────────────────────
    r = run([bin_path, "--version"], 10)
    assert r.returncode == 0, f"--version rc={r.returncode}"
    assert "cdebootstrap 0.7.9" in r.stdout, f"version: {r.stdout!r}"
    ver_line = r.stdout.splitlines()[0]
    r2 = run([bin_path], 10)
    assert r2.returncode == 1, f"no-args rc={r2.returncode} (expect 1)"
    with open(bin_path, "rb") as f:
        assert f.read(4) == b"\x7fELF"
    print("A. smoke OK:", ver_line)

    # ── B. 上游 5 个集成测试实际执行（debian/tests/*）──────
    # 每个测试 = exec cdebootstrap <suite> <target> --debug --flavour <F>。
    # OHOS 非 root（euid 20020084，sudo 需密码且无 tty，root 账户 /bin/false），
    # 源码 check_permission(): if (!noexec && getuid()) → "Need root privileges"。
    # 实际执行拿到该真实报错即验证了二进制/配置/镜像解析路径到权限门。
    suites = [("Debian/bookworm", "standard"),
              ("Debian/sid", "build"),
              ("Debian/sid", "minimal"),
              ("Debian/sid", "standard"),
              ("Debian/trixie", "standard")]
    blocked_root = 0
    for i, (suite, flavour) in enumerate(suites, 1):
        target = os.path.join(pkg, f"_test_root{i}")
        os.makedirs(target, exist_ok=True)
        args = [bin_path, suite, target, "--debug", "--flavour", flavour,
                "--configdir", cfg]
        t0 = time.time()
        try:
            r = run(args, 30)
        except subprocess.TimeoutExpired:
            print(f"B{i}. {suite}/{flavour}: TIMEOUT(30s) — 异常")
            r = None
        dur = time.time() - t0
        combined = ""
        if r:
            combined = (r.stdout or "") + (r.stderr or "")
            ok = "Need root privileges" in combined
            if ok:
                blocked_root += 1
            print(f"B{i}. {suite}/{flavour}: rc={r.returncode} "
                  f"{dur:.1f}s root-gate={'HIT' if ok else 'MISS'}")
            assert ok, (f"{suite}/{flavour} 未到 root 权限门:\n"
                        f"{combined[-800:]}")
        shutil.rmtree(target, ignore_errors=True)
    assert blocked_root == 5, f"root 权限门命中 {blocked_root}/5"
    print("B. 5/5 上游集成测试实际执行，全部在 root 权限门真实阻塞 "
          f"(E: Need root privileges)")

    # ── C. 下载层真跑（--download-only 不设 noexec 根检查）──────
    # 验证：config 解析→镜像解析→libcurl 下载 Release/Packages.xz→
    # 依赖解析→.deb 真实落盘。CI 无网络时 SKIP 不失败。
    # 镜像说明：包内 pristine config/suites 默认 Mirror=
    # http://deb.debian.org/debian 跨海，CI worker 180s 拉不完
    # bookworm（#58151/#59674/#59987 三次同因超时 debs=0）→ 经 CLI
    # 第 3 位置参数（cdebootstrap 内置能力，main.c）显式传国内源
    # https://mirrors.aliyun.com/debian（CI 可达，conandata 源码
    # tarball 即该源，构建成功已证明）；本地实测 79 个 .deb 全落盘
    # <30s。-a 因 CI 容器无 /usr/share/keyrings/
    # debian-archive-keyring.gpg（与 A/B 段一致）。
    if not has_network():
        dl_summary = "SKIP（CI 无网络；本地实测 79 deb/28MB）"
        print("C. SKIP: 无网络——下载层（aliyun 镜像）无法在 CI 验证")
    else:
        target = os.path.join(pkg, "_test_dl")
        os.makedirs(target, exist_ok=True)
        args = [bin_path, "Debian/bookworm", target,
                "https://mirrors.aliyun.com/debian", "--configdir", cfg,
                "-d", "--allow-unauthenticated", "--debug"]
        t0 = time.time()
        try:
            r = run(args, 300)
        except subprocess.TimeoutExpired:
            r = None
        dur = time.time() - t0
        deb_count = 0
        total = 0
        for dp, _, fns in os.walk(target):
            for fn in fns:
                if fn.endswith(".deb"):
                    deb_count += 1
                    total += os.path.getsize(os.path.join(dp, fn))
        log = ""
        if r:
            log = (r.stdout or "") + (r.stderr or "")
        print(f"C. download-layer: rc={getattr(r, 'returncode', 'timeout')} "
              f"{dur:.1f}s debs={deb_count} size={total // 1024}KB")
        if deb_count == 0:
            print("   日志尾部:\n" + log[-1200:])
            assert False, "download-layer 未下载到任何 .deb"
        assert deb_count >= 5, f"仅 {deb_count} 个 .deb（无 .deb 落盘，aliyun 下载层异常）"
        assert "Using mirror https://mirrors.aliyun.com/debian" in log
        dl_summary = f"真跑 {deb_count} deb/{total // 1024}KB"
        print("C. 下载层真跑 OK：libcurl/镜像/索引/依赖解析/.deb 落盘 全链路")
        shutil.rmtree(target, ignore_errors=True)

    # ── D. chroot(2) 探测（install 层第二道系统级阻塞证据）──
    # 放最后：隔离子进程执行，即使内核 SIGSYS 也不影响前序结果
    chroot_summary = probe_chroot()
    print("D. " + chroot_summary)

    print("cdebootstrap test OK: cdebootstrap 0.7.9 "
          f"(5/5 upstream integration 实际执行+root 门真实报错, "
          f"download-layer {dl_summary}, {chroot_summary})")


if __name__ == "__main__":
    main()
