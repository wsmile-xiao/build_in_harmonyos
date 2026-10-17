// test_package.cpp — 验证 jpeg-compressor 库真实可用
// 使用 jpge 压缩一张 64x64 RGB 图像，再用 jpgd 解压回来，校验尺寸与内容。
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include "jpge.h"
#include "jpgd.h"

int main()
{
    const int width = 64, height = 64, comps = 3;
    std::vector<unsigned char> src(width * height * comps);
    for (int y = 0; y < height; ++y)
        for (int x = 0; x < width; ++x)
        {
            int i = (y * width + x) * comps;
            src[i + 0] = (unsigned char)(x * 4);          // R 渐变
            src[i + 1] = (unsigned char)(y * 4);          // G 渐变
            src[i + 2] = (unsigned char)((x + y) * 2);    // B 渐变
        }

    // 编码：jpge
    jpge::params params;
    params.m_quality = 90;
    params.m_subsampling = jpge::H2V2;
    std::vector<unsigned char> jpeg;
    jpeg.resize(width * height * comps * 2);
    int jpeg_size = (int)jpeg.size();
    bool ok = jpge::compress_image_to_jpeg_file_in_memory(
        jpeg.data(), jpeg_size, width, height, comps, src.data(), params);
    if (!ok)
    {
        std::fprintf(stderr, "FAIL: jpge compress_image_to_jpeg_file_in_memory 失败\n");
        return 1;
    }

    // 解码：jpgd
    int dec_w = 0, dec_h = 0, dec_comps = 0;
    unsigned char *decoded = jpgd::decompress_jpeg_image_from_memory(
        jpeg.data(), (unsigned int)jpeg_size, &dec_w, &dec_h, &dec_comps, comps);
    if (!decoded)
    {
        std::fprintf(stderr, "FAIL: jpgd decompress_jpeg_image_from_memory 失败\n");
        return 1;
    }

    bool dims_ok = (dec_w == width && dec_h == height && dec_comps == comps);
    std::fprintf(stdout, "jpeg-compressor test: 编码 %d 字节, 解码 %dx%d (%d comps)%s\n",
                 jpeg_size, dec_w, dec_h, dec_comps, dims_ok ? " OK" : " MISMATCH");
    free(decoded);

    if (!dims_ok)
    {
        std::fprintf(stderr, "FAIL: 解码尺寸与输入不一致\n");
        return 1;
    }
    std::fprintf(stdout, "PASS: jpeg-compressor 编码/解码往返验证通过\n");
    return 0;
}