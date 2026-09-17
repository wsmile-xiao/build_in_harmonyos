import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print("FAIL: usage: test_moe.py <moe_pkg> <ncurses_pkg>", file=sys.stderr)
        return 1
    moe_pkg, ncurses_pkg = sys.argv[1], sys.argv[2]
    binary = os.path.join(moe_pkg, "usr", "bin", "moe")
    if not os.path.isfile(binary):
        print(f"FAIL: moe binary missing: {binary}", file=sys.stderr)
        return 1
    os.chmod(binary, 0o755)
    # 运行被测二进制并断言行为（R34）：--version 输出必须含版本号 1.5
    env = dict(os.environ)
    libdir = os.path.join(ncurses_pkg, "lib")
    env["LD_LIBRARY_PATH"] = libdir + os.pathsep + env.get("LD_LIBRARY_PATH", "")

    r = subprocess.run([binary, "--version"], capture_output=True, text=True,
                       env=env, timeout=30)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        print(f"FAIL: moe --version rc={r.returncode}: {out}", file=sys.stderr)
        return 1
    if "1.5" not in out:
        print(f"FAIL: version output unexpected: {out}", file=sys.stderr)
        return 1
    print(f"moe --version OK: {out.strip().splitlines()[0]}")

    r = subprocess.run([binary, "--help"], capture_output=True, text=True,
                       env=env, timeout=30)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0 or "--help" not in out and "Usage" not in out:
        print(f"FAIL: moe --help rc={r.returncode}: {out[:400]}",
              file=sys.stderr)
        return 1
    print("moe --help OK")
    print("OK: moe binary runs and reports version/usage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
