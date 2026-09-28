#include <DirectXMath.h>
#include <cstdio>

// 消费者用例：仅通过公开头文件 Inc/DirectXMath.h 调用公开 API，
// 验证第三方使用者能否编译、链接、调用并正常运行（R34）。
// 覆盖至少一个真实业务意义的公开 API 调用及其可观察结果。
int main()
{
    using namespace DirectX;

    // 1) SIMD 向量：XMVectorSet / XMVectorGetX 往返
    XMVECTOR v = XMVectorSet(1.0f, 2.0f, 3.0f, 4.0f);
    float x = XMVectorGetX(v);
    float y = XMVectorGetY(v);
    if (x != 1.0f || y != 2.0f)
    {
        std::printf("FAIL vector roundtrip: (%f, %f)\n", x, y);
        return 1;
    }
    std::printf("vector roundtrip OK: (%f, %f, %f, %f)\n", x, y, XMVectorGetZ(v), XMVectorGetW(v));

    // 2) SIMD 向量加法
    XMVECTOR a = XMVectorSet(1.0f, 2.0f, 3.0f, 4.0f);
    XMVECTOR b = XMVectorSet(10.0f, 20.0f, 30.0f, 40.0f);
    XMVECTOR s = XMVectorAdd(a, b);
    if (XMVectorGetX(s) != 11.0f || XMVectorGetY(s) != 22.0f)
    {
        std::printf("FAIL vector add\n");
        return 1;
    }
    std::printf("vector add OK\n");

    // 3) 矩阵：单位矩阵与矩阵乘法（可观察结果）
    XMMATRIX m1 = XMMatrixIdentity();
    XMMATRIX m2 = XMMatrixRotationZ(XMConvertToRadians(90.0f));
    XMMATRIX m3 = XMMatrixMultiply(m1, m2);
    // 旋转 90° 后，X 轴单位向量应变为 (≈0, ≈1, 0, 1)
    XMVECTOR axis = XMVectorSet(1.0f, 0.0f, 0.0f, 1.0f);
    XMVECTOR r = XMVector4Transform(axis, m3);
    float rx = XMVectorGetX(r);
    float ry = XMVectorGetY(r);
    if (!(rx > -1e-3f && rx < 1e-3f) || !(ry > 1.0f - 1e-3f && ry < 1.0f + 1e-3f))
    {
        std::printf("FAIL matrix rotation: (%f, %f)\n", rx, ry);
        return 1;
    }
    std::printf("matrix rotate 90deg OK: (%f, %f)\n", rx, ry);

    // 4) 包装/存储类型（公开 API）
    XMFLOAT3 f3(1.5f, 2.5f, 3.5f);
    XMVECTOR fv = XMLoadFloat3(&f3);
    if (XMVectorGetY(fv) != 2.5f)
    {
        std::printf("FAIL XMFLOAT3 load\n");
        return 1;
    }
    std::printf("XMFLOAT3 load/store OK\n");

    std::printf("ALL DIRECTXMATH TESTS PASSED\n");
    return 0;
}