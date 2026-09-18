// Consumer validation for gli 0.8.2.0 — simulates an upper-layer component
// using ONLY the library's installed public headers (gli/gli.hpp) and public API.
#include <gli/gli.hpp>
#include <gli/texture2d.hpp>
#include <gli/load.hpp>
#include <gli/save.hpp>
#include <gli/generate_mipmaps.hpp>
#include <gli/convert.hpp>

#include <cstdio>
#include <cstring>
#include <cstdint>

int main(int argc, char* argv[])
{
    std::printf("=== gli consumer test ===\n");

    // 1. Create a texture2d through the public API and verify observable state
    //    (single-level: 双参构造会生成完整 mipmap 链，size() 为全部层级之和)
    gli::texture2d Tex(gli::FORMAT_RGBA8_UNORM_PACK8, gli::texture2d::extent_type(16, 16), 1);
    if (Tex.empty() || Tex.format() != gli::FORMAT_RGBA8_UNORM_PACK8)
    {
        std::printf("FAIL: texture2d creation\n");
        return 1;
    }
    if (Tex.extent().x != 16 || Tex.extent().y != 16 || Tex.size() != 16u * 16u * 4u)
    {
        std::printf("FAIL: texture2d extent/size\n");
        return 1;
    }
    std::printf("OK: texture2d 16x16 RGBA8 created, size=%zu\n", Tex.size());

    // 2. Write and read back pixel data through public data() API
    std::uint8_t* Data = static_cast<std::uint8_t*>(Tex.data());
    for (std::size_t i = 0; i < 16u * 16u * 4u; ++i)
        Data[i] = static_cast<std::uint8_t>(i & 0xFF);
    if (Data[0] != 0x00 || Data[255] != 0xFF || Data[256] != 0x00)
    {
        std::printf("FAIL: pixel data roundtrip\n");
        return 1;
    }
    std::printf("OK: pixel data roundtrip\n");

    // 3. Generate mipmaps via public API and verify multi-level chain
    //    (源纹理用完整链构造，generate_mipmaps 才会产出多级)
    gli::texture2d Mip = gli::generate_mipmaps(
        gli::texture2d(gli::FORMAT_RGBA8_UNORM_PACK8, gli::texture2d::extent_type(16, 16)),
        gli::FILTER_LINEAR);
    if (Mip.empty() || Mip.levels() <= 1)
    {
        std::printf("FAIL: generate_mipmaps\n");
        return 1;
    }
    std::printf("OK: generate_mipmaps -> %zu levels\n", Mip.levels());

    // 4. Convert format via public API and verify
    gli::texture2d Conv = gli::convert(Tex, gli::FORMAT_RGB8_UNORM_PACK8);
    if (Conv.empty() || Conv.format() != gli::FORMAT_RGB8_UNORM_PACK8 ||
        Conv.size() != 16u * 16u * 3u)
    {
        std::printf("FAIL: convert\n");
        return 1;
    }
    std::printf("OK: convert to RGB8, size=%zu\n", Conv.size());

    std::printf("=== gli consumer test PASSED ===\n");
    return 0;
}
