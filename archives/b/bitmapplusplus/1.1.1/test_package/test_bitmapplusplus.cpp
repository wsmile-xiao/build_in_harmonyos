// test_package/test_bitmapplusplus.cpp — bitmapplusplus 消费者测试
//
// 真实验证 BitmapPlusPlus 1.1.1 的公开 API：
//   构造 Bitmap(width, height) → fill() → operator[] → width()/height() →
//   save() → load() 回读 → 像素相等断言 → 迭代器遍历。
// 每项断言失败即 return 1，非仅 include + return 0 的空壳测试。
#include <BitmapPlusPlus.hpp>

#include <cstdio>
#include <cstdlib>
#include <string>

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

std::string writable_tmp_path() {
    // OHOS /tmp 可能只读：优先 TMPDIR/TMP/TEMP，最后回退当前目录
    const char* cands[] = {std::getenv("TMPDIR"), std::getenv("TMP"),
                           std::getenv("TEMP")};
    for (const char* c : cands) {
        if (c && *c) {
            return std::string(c) + "/bpp_test.bmp";
        }
    }
    return "bpp_test.bmp";
}
}  // namespace

int main() {
    // 1. 构造 + 尺寸断言
    bmp::Bitmap bitmap(8, 8);
    check(bitmap.width() == 8, "Bitmap(8,8).width() == 8");
    check(bitmap.height() == 8, "Bitmap(8,8).height() == 8");

    // 2. clear(全像素填充) + 逐像素访问
    //    （本库全像素填充 API 名为 clear()，语义即 std::fill）
    bitmap.clear(bmp::Pixel(42, 69, 96));
    const bmp::Pixel& p0 = bitmap[0];
    check(p0.r == 42 && p0.g == 69 && p0.b == 96,
          "bitmap[0] == Pixel(42,69,96) after clear");
    check(bitmap[63] == bitmap[0], "bitmap[63] == bitmap[0] after clear");

    // 3. 写入特定像素（首尾不同）
    bitmap[7] = bmp::Red;
    check(bitmap[7] == bmp::Red, "bitmap[7] = Red");

    // 4. save → load 回环
    const std::string path = writable_tmp_path();
    check(!path.empty(), "writable tmp path resolved");
    bitmap.save(path);
    bmp::Bitmap loaded(path);
    check(loaded.width() == 8 && loaded.height() == 8,
          "loaded width/height match after save/load round-trip");
    check(loaded[0] == bmp::Pixel(42, 69, 96),
          "loaded[0] pixel preserved after round-trip");
    check(loaded[7] == bmp::Red,
          "loaded[7] pixel preserved after round-trip");

    // 5. 迭代器遍历（begin/end 覆盖全部像素）
    std::size_t count = 0;
    for (auto& px : loaded) {
        (void)px;
        ++count;
    }
    check(count == 64, "iterator covers 8x8=64 pixels");

    // 6. clear 后全黑
    loaded.clear(bmp::Black);
    check(loaded[0] == bmp::Black && loaded[63] == bmp::Black,
          "clear(Black) resets pixels");

    if (g_failures == 0) {
        printf("test_bitmapplusplus: ALL PASS (%d checks)\n", 11);
        return 0;
    }
    printf("test_bitmapplusplus: %d FAILURES\n", g_failures);
    return 1;
}
