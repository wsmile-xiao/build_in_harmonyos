#include <cstdio>
#include <cstdlib>

#include <ImfHeader.h>
#include <ImathBox.h>

int main(int argc, char *argv[])
{
    // 1) C++ API: 构造 Header，读 screenWindowWidth（默认 1.0）
    Imf::Header header;
    float w = header.screenWindowWidth();
    std::printf("Header screenWindowWidth = %g\n", w);

    // 2) 验证 Imath 数值链路（OpenEXR::OpenEXR 依赖 imath::imath）
    Imath::V2i v(3, 4);
    int len2 = v.dot(v);
    std::printf("Imath::V2i dot = %d\n", len2);

    // 3) 构造 Box2i 并调用 OpenEXR Header 的 dataWindow 逻辑
    Imath::Box2i dataWindow(Imath::V2i(0, 0), Imath::V2i(255, 255));
    header.dataWindow() = dataWindow;
    std::printf("dataWindow max.x = %d\n", header.dataWindow().max.x);

    if (w != 1.0f || len2 != 25 || header.dataWindow().max.x != 255) {
        std::printf("FAILED\n");
        return EXIT_FAILURE;
    }
    std::printf("test_openexr OK\n");
    return EXIT_SUCCESS;
}
