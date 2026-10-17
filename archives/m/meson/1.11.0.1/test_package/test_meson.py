import shutil
import subprocess
import sys


def test_meson(meson=None):
    try:
        # 优先使用调用方传入的绝对路径（test_package/conanfile.py 通过
        # dep.package_folder 定位）；未传入时回退 PATH 查找，避免部分环境
        # (toybox/musl posix_spawn) 下 PATH 查找差异导致找不到可执行文件
        if meson is None:
            meson = shutil.which("meson")
        if not meson:
            raise RuntimeError("meson executable not found in PATH")
        output = subprocess.check_output([meson, "--version"], text=True)
        print("Meson version:", output.strip())
        assert output.strip() != ""
    except Exception as e:
        print("FAIL: Failed to run meson:", e)
        sys.exit(1)

    print("PASS")


if __name__ == "__main__":
    test_meson(sys.argv[1] if len(sys.argv) > 1 else None)
