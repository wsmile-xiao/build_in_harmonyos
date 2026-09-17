import os
import shutil
import subprocess
import sys
import tempfile


def main() -> int:
    if len(sys.argv) < 3:
        print("FAIL: usage: test_ccscript.py <ccscript_pkg> <ucommon_pkg>",
              file=sys.stderr)
        return 1
    ccscript, ucommon = sys.argv[1], sys.argv[2]
    # 包布局为 <pkg>/usr/{include,lib}（configure --prefix=/usr + DESTDIR）
    inc = [os.path.join(ccscript, "usr", "include"),
           os.path.join(ucommon, "usr", "include")]
    lib = [os.path.join(ccscript, "usr", "lib"),
           os.path.join(ucommon, "usr", "lib")]
    if not os.path.isdir(inc[1]):
        # ucommon 为 CMake 构建，布局也可能为 <pkg>/{include,lib}
        inc[1] = os.path.join(ucommon, "include")
        lib[1] = os.path.join(ucommon, "lib")
    for d in inc + lib:
        if not os.path.isdir(d):
            print(f"FAIL: missing directory: {d}", file=sys.stderr)
            return 1
    if not os.path.isfile(os.path.join(inc[0], "ccscript.h")):
        print(f"FAIL: ccscript.h missing under {inc[0]}", file=sys.stderr)
        return 1
    # 传递依赖库目录（ucommon 静态链依赖 gnutls 等）——由 conan 提供时
    # 全部位于各自 package_folder/lib，逐个加入 -L
    extra_lib = sys.argv[3:]
    for d in extra_lib:
        if os.path.isdir(d):
            lib.append(d)
    src = os.path.join(os.path.dirname(__file__), "smoke.cpp")
    tmpdir = tempfile.mkdtemp(prefix="ccscript-smoke-")
    binp = os.path.join(tmpdir, "smoke")
    try:
        cmd = ["/data/service/hnp/bin/clang++", "-std=c++11", src, "-o", binp]
        cmd += [f"-I{i}" for i in inc]
        cmd += [f"-L{l}" for l in lib]
        cmd += ["-lccscript", "-lusecure", "-lucommon", "-lpthread",
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
    print("OK: ccscript headers + lib present + smoke API link/run works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
