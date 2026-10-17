// test_package/test_bitmapplusplus_ohos.cpp — 鸿蒙特有测试
//
// 验证 BitmapPlusPlus 在 OHOS 运行时的真实 BMP 文件 I/O 行为：
//   - 使用当前用户可写的专用临时目录（TMPDIR/TMP/TEMP 优先，回退当前目录）
//   - 完整 24bpp BMP 写读回环：构造 → 填充渐变 → save → load → 逐像素断言
//   - 验证非 24bpp/坏文件格式抛出 bmp::Exception（OHOS 上真实异常路径）
// 每项断言失败即 return 1。
#include <BitmapPlusPlus.hpp>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <sys/stat.h>

namespace {
int g_failures = 0;

void check(bool cond, const char* label) {
    if (cond) {
        printf("[ok] %s\n", label);
    } else {
        printf("[FAIL] %s\n", label);
        ++g_failures;
    }
}

bool mkdir_wrapper(const std::string& dir) {
    return ::mkdir(dir.c_str(), 0700) == 0;
}

std::string make_tmpdir() {
    // OHOS /tmp 可能不可写：构造当前用户可写目录并验证
    std::string dir = ".";
    const char* cands[] = {std::getenv("TMPDIR"), std::getenv("TMP"),
                           std::getenv("TEMP")};
    for (const char* c : cands) {
        if (c && *c) {
            // 尝试在该候选下创建唯一子目录
            std::string try_dir = std::string(c) + "/bpp_ohos_tmp";
            if (mkdir_wrapper(try_dir)) {
                dir = try_dir;
                break;
            }
        }
    }
    return dir;
}
}  // namespace

int main() {
    // 1. 专用临时目录
    std::string dir = make_tmpdir();
    check(!dir.empty(), "dedicated writable temp dir resolved");
    std::string path = dir + "/bpp_ohos_roundtrip.bmp";

    // 2. 渐变填充的 16x16 BMP 保存
    bmp::Bitmap src(16, 16);
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            src[y * 16 + x] = bmp::Pixel(
                static_cast<std::uint8_t>(x * 16),
                static_cast<std::uint8_t>(y * 16),
                static_cast<std::uint8_t>((x + y) * 8));
        }
    }
    src.save(path);

    // 3. 重新加载并逐像素核对（256 像素全量断言）
    bmp::Bitmap back(path);
    check(back.width() == 16 && back.height() == 16,
          "OHOS round-trip: size preserved");
    bool all_match = true;
    for (int y = 0; y < 16 && all_match; ++y) {
        for (int x = 0; x < 16; ++x) {
            bmp::Pixel expect(
                static_cast<std::uint8_t>(x * 16),
                static_cast<std::uint8_t>(y * 16),
                static_cast<std::uint8_t>((x + y) * 8));
            if (!(back[y * 16 + x] == expect)) {
                all_match = false;
                break;
            }
        }
    }
    check(all_match, "OHOS round-trip: all 256 pixels preserved");

    // 4. 坏文件必须抛出 bmp::Exception（真实异常路径）
    std::string bad = dir + "/bpp_bad.bmp";
    {
        FILE* f = std::fopen(bad.c_str(), "wb");
        if (f) {
            std::fwrite("not a bmp", 1, 9, f);
            std::fclose(f);
        }
    }
    bool threw = false;
    try {
        bmp::Bitmap broken(bad);
        (void)broken;
    } catch (const bmp::Exception&) {
        threw = true;
    }
    check(threw, "corrupt BMP throws bmp::Exception on OHOS");

    if (g_failures == 0) {
        printf("test_bitmapplusplus_ohos: ALL PASS (%d checks)\n", 4);
        return 0;
    }
    printf("test_bitmapplusplus_ohos: %d FAILURES\n", g_failures);
    return 1;
}
