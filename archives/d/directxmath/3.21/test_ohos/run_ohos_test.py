#!/usr/bin/env python3
"""test_ohos — directxmath 3.21 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  aarch64 ELF 验证（消费者可执行文件为 ELF64 AArch64）
  T2  musl libc（无 glibc / 无 ld-linux）
  T3  .codesign 段存在（OHOS 签名管线产出）
  T4  无宿主绝对路径泄漏（含 RPATH/RUNPATH 检查）
  T5  真实 SIMD 计算（仅经公开头文件调用 XMVECTOR/XMMATRIX 公开 API，
      在 aarch64 NEON 路径上执行向量运算与矩阵旋转并可观察结果断言）

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import subprocess
import sys
import tempfile

READELF = os.environ.get("READELF", "readelf")
CXX = os.environ.get("CXX", "clang++")
STRINGS = os.environ.get("STRINGS", "strings")

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"directxmath-3.21"]

TEST_CPP = r"""
#include <DirectXMath.h>
#include <cstdio>

// 鸿蒙专项：仅通过公开头文件 Inc/DirectXMath.h 调用公开 API，
// 验证 NEON SIMD 路径下真实向量/矩阵运算的可观察结果。
int main()
{
    using namespace DirectX;

    // 1) NEON SIMD 向量往返
    XMVECTOR v = XMVectorSet(1.0f, 2.0f, 3.0f, 4.0f);
    if (XMVectorGetX(v) != 1.0f || XMVectorGetY(v) != 2.0f)
        return 1;

    // 2) SIMD 向量加法
    XMVECTOR a = XMVectorSet(1.0f, 2.0f, 3.0f, 4.0f);
    XMVECTOR b = XMVectorSet(10.0f, 20.0f, 30.0f, 40.0f);
    XMVECTOR s = XMVectorAdd(a, b);
    if (XMVectorGetX(s) != 11.0f || XMVectorGetY(s) != 22.0f)
        return 2;

    // 3) 矩阵：单位矩阵 x 旋转 90°（可观察结果）
    XMMATRIX m1 = XMMatrixIdentity();
    XMMATRIX m2 = XMMatrixRotationZ(XMConvertToRadians(90.0f));
    XMMATRIX m3 = XMMatrixMultiply(m1, m2);
    XMVECTOR axis = XMVectorSet(1.0f, 0.0f, 0.0f, 1.0f);
    XMVECTOR r = XMVector4Transform(axis, m3);
    float rx = XMVectorGetX(r);
    float ry = XMVectorGetY(r);
    if (!(rx > -1e-3f && rx < 1e-3f) || !(ry > 1.0f - 1e-3f && ry < 1.0f + 1e-3f))
        return 3;

    // 4) 浮点存储类型（公开 API）
    XMFLOAT3 f3(1.5f, 2.5f, 3.5f);
    XMVECTOR fv = XMLoadFloat3(&f3);
    if (XMVectorGetY(fv) != 2.5f)
        return 4;

    printf("OHOS_DIRECTXMATH_TESTS_PASS: vec=(%.1f,%.1f) add=(%.1f,%.1f) rot=(%.3f,%.3f)\n",
           XMVectorGetX(v), XMVectorGetY(v),
           XMVectorGetX(s), XMVectorGetY(s), rx, ry);
    return 0;
}
"""


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_ohos_test.py <conan_package_folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    include = os.path.join(pkg, "include")

    work = tempfile.mkdtemp(prefix="dxm-test-ohos-")
    src = os.path.join(work, "test_ohos.cpp")
    with open(src, "w") as f:
        f.write(TEST_CPP)
    exe = os.path.join(work, "test_ohos")

    comp = subprocess.run(
        [CXX, "-O2", "-std=c++11", "-I", include, src, "-o", exe],
        capture_output=True, text=True)
    if comp.returncode != 0:
        print("FAIL: compile/link failed:\n" + comp.stderr, file=sys.stderr)
        return 1

    # T1: ELF64 AArch64
    r = subprocess.run([READELF, "-h", exe], capture_output=True)
    if b"ELF64" not in r.stdout or b"AArch64" not in r.stdout:
        print("FAIL: not ELF64 AArch64", file=sys.stderr)
        return 1

    # T2: musl libc（NEEDED 中无 glibc / ld-linux）
    r = subprocess.run([READELF, "-d", exe], capture_output=True)
    if b"GLIBC" in r.stdout or b"ld-linux" in r.stdout:
        print("FAIL: glibc/ld-linux detected", file=sys.stderr)
        return 1

    # T3: .codesign 段存在（OHOS 签名管线产出）
    r = subprocess.run([READELF, "-S", exe], capture_output=True)
    if b".codesign" not in r.stdout:
        print("FAIL: .codesign section missing", file=sys.stderr)
        return 1

    # T4: 无宿主机绝对路径
    st = subprocess.run([STRINGS, exe], capture_output=True)
    for pat in HOST_PATH_RES:
        if pat in st.stdout:
            print("FAIL: host path leak: %s" % pat.decode(), file=sys.stderr)
            return 1

    # T5: 真实运行（NEON SIMD 计算断言）
    run = subprocess.run([exe], capture_output=True, text=True)
    if run.returncode != 0:
        print("FAIL: test run failed rc=%d:\n%s%s" % (run.returncode, run.stdout, run.stderr), file=sys.stderr)
        return 1
    print(run.stdout, end="")
    if "OHOS_DIRECTXMATH_TESTS_PASS" not in run.stdout:
        print("FAIL: test did not report PASS", file=sys.stderr)
        return 1

    print("TEST_OHOS_ALL_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())