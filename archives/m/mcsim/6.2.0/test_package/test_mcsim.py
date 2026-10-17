import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print("FAIL: usage: test_mcsim.py <mcsim_pkg> <gsl_pkg>", file=sys.stderr)
        return 1
    mcsim_pkg, gsl_pkg = sys.argv[1], sys.argv[2]
    bindir = os.path.join(mcsim_pkg, "usr", "bin")
    mod = os.path.join(bindir, "mod")
    if not os.path.isfile(mod):
        print(f"FAIL: mod binary missing: {mod}", file=sys.stderr)
        return 1
    os.chmod(mod, 0o755)
    env = dict(os.environ)
    libdirs = [os.path.join(gsl_pkg, "lib")] + [d for d in sys.argv[3:]
                                                if os.path.isdir(d)]
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        libdirs + [env.get("LD_LIBRARY_PATH", "")])

    # 运行被测二进制并断言行为（R34）：mod -h 输出用法且退出码 0
    r = subprocess.run([mod, "-h"], capture_output=True, text=True,
                       env=env, timeout=30)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        print(f"FAIL: mod -h rc={r.returncode}: {out[:300]}", file=sys.stderr)
        return 1
    if "Usage: mod" not in out:
        print(f"FAIL: usage output unexpected: {out[:300]}", file=sys.stderr)
        return 1
    print("mod -h OK: usage printed")

    # 附加行为检查：mod 对不存在的输入文件应报错退出（非零退出码，不挂起）
    import tempfile
    tmp = tempfile.mkdtemp(prefix="mcsim-smoke-")
    r = subprocess.run([mod, os.path.join(tmp, "nonexistent.model")],
                       capture_output=True, text=True, env=env, cwd=tmp,
                       stdin=subprocess.DEVNULL, timeout=30)
    if r.returncode == 0:
        print("FAIL: mod accepted nonexistent input file", file=sys.stderr)
        return 1
    print("mod invalid-input handling OK (nonzero exit, no hang)")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print("OK: mcsim mod binary runs (usage + input error handling)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
