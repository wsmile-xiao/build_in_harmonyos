import os
import shutil
import subprocess
import sys
import tempfile


def main() -> int:
    if len(sys.argv) < 4:
        print("FAIL: usage: test_ccaudio.py <ccaudio_pkg> <commoncpp2_pkg> <zlib_pkg>",
              file=sys.stderr)
        return 1
    ccaudio, ccxx, zlib = sys.argv[1], sys.argv[2], sys.argv[3]
    inc = [os.path.join(ccaudio, "usr", "include", "cc++2"),
           os.path.join(ccxx, "usr", "include")]
    lib = [os.path.join(ccaudio, "usr", "lib"),
           os.path.join(ccxx, "usr", "lib"),
           os.path.join(zlib, "lib")]
    for d in inc + lib:
        if not os.path.isdir(d):
            print(f"FAIL: missing directory: {d}", file=sys.stderr)
            return 1
    if not os.path.isfile(os.path.join(inc[0], "cc++", "audio.h")):
        print(f"FAIL: cc++/audio.h missing under {inc[0]}", file=sys.stderr)
        return 1
    src = os.path.join(os.path.dirname(__file__), "smoke.cpp")
    # 编译产物写入临时目录（不污染源码目录 / 只读文件系统假阴性）
    tmpdir = tempfile.mkdtemp(prefix="ccaudio-smoke-")
    binp = os.path.join(tmpdir, "smoke")
    try:
        cmd = ["/data/service/hnp/bin/clang++", src, "-o", binp]
        cmd += [f"-I{i}" for i in inc]
        cmd += [f"-L{l}" for l in lib]
        cmd += ["-lccaudio1", "-lccgnu2", "-lccext2", "-lz", "-lpthread", "-lm",
                "-Wno-deprecated-declarations"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: compile smoke: {r.stderr}", file=sys.stderr)
            return 1
        r = subprocess.run([binp], capture_output=True, text=True, cwd=tmpdir)
        print(r.stdout.strip())
        if r.returncode != 0:
            print(f"FAIL: run smoke rc={r.returncode}: {r.stderr}",
                  file=sys.stderr)
            return 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("OK: ccaudio headers + lib present + smoke API link/run works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
