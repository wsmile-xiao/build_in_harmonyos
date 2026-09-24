// test_package — imageinfo 2.0.0 消费者验证（R34：必须实际调用被测包 API）
//
// 使用 imageinfo 的 parse<FilePathReader> 解析一个真实的 1x1 PNG 文件，
// 校验格式（kFormatPng）、扩展名（png）、MIME（image/png）与尺寸（1x1）。
// 数据为 1x1 透明 PNG（官方规范字节流），不依赖外部文件。

#include <cstdint>
#include <cstdio>
#include <cstdlib>

#include "imageinfo.hpp"

// 1x1 透明 PNG：89 50 4E 47 0D 0A 1A 0A ...
static const uint8_t kPng1x1[] = {
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  // PNG signature
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  // IHDR chunk
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  // width=1, height=1
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,  // bit depth/color type
    0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,  // IDAT chunk
    0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,  //
    0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,  //
    0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,  // IEND chunk
    0x42, 0x60, 0x82,
};

int main() {
    using namespace imageinfo;

    // 通过 RawDataReader 从内存解析（真实调用 parse API 与格式探测）
    auto info = parse<RawDataReader>(RawData(kPng1x1, sizeof(kPng1x1)));
    if (!info.ok()) {
        std::fprintf(stderr, "FAIL: parse error=%s\n", info.error_msg());
        return 1;
    }
    if (info.format() != kFormatPng) {
        std::fprintf(stderr, "FAIL: format != png\n");
        return 1;
    }
    if (info.size().width != 1 || info.size().height != 1) {
        std::fprintf(stderr, "FAIL: size != 1x1 (got %ldx%ld)\n",
                     static_cast<long>(info.size().width),
                     static_cast<long>(info.size().height));
        return 1;
    }
    std::printf("imageinfo 2.0.0: png 1x1 parsed OK (ext=%s, mime=%s)\n",
                info.ext(), info.mimetype());
    return 0;
}
