// test_package/test.cpp — qoixx 0.1.7 消费者视角真实用例（鸿蒙特有测试行）
//
// 从「已安装的 qoixx 包」（package() 交付的 include/qoixx.hpp）出发，真实调用
// 编解码 API 并逐条断言行为（R34：非空壳、非 print-only、不是只打印不调用）。
// 任一断言失败 → 打印 QOIXX-CONSUMER 行并以 rc=1 退出 → conan create 失败。
//
// 取数（见 test_package/MANIFEST.yml 的 assertion_count）：
//   本文件 check_true 的调用点总数 = 消费者断言数；
//   运行期以末行 `QOIXX-CONSUMER checks=<N> failures=<M>` 为准（N=14）。
//
// 覆盖点：交付头可消费性 —— encode/decode 往返、desc 整体回读、字节级确定性、
// 指针重载与容器重载一致、QOI RLE 压缩收益、128x128 大图（aarch64 NEON 快路径
// 进入构建面时的往返）、显式 channels 参数、两条错误路径抛异常。
// 刻意不使用 std::ranges（OHOS libc++ 15.0.4 需要 -fexperimental-library 才提供，
// 上游测试面已覆盖该旗标；消费者面保持上游头文件默认可用）。
#include <qoixx.hpp>

#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>

static int g_checks = 0;
static int g_failures = 0;

static void check_true(bool cond, const char* what) {
    ++g_checks;
    if (!cond) {
        ++g_failures;
        std::fprintf(stderr, "[FAIL] %s\n", what);
    }
}

int main() {
    using image_t = std::vector<std::uint8_t>;

    // ── 1. 3 通道：encode → decode 往返 ──────────────────────────────────
    const qoixx::qoi::desc d3{.width = 8, .height = 4, .channels = 3,
                              .colorspace = qoixx::qoi::colorspace::srgb};
    image_t img3(8u * 4u * 3u);
    for (std::size_t i = 0; i < img3.size(); ++i) {
        img3[i] = static_cast<std::uint8_t>((i * 37u + 11u) & 0xFFu);
    }
    const image_t enc3 = qoixx::qoi::encode<image_t>(img3, d3);
    check_true(!enc3.empty(), "encode 3ch produces non-empty stream");
    check_true(enc3.size() >= 14 && enc3[0] == 'q' && enc3[1] == 'o' &&
                   enc3[2] == 'i' && enc3[3] == 'f',
               "encoded stream starts with qoif magic");
    const auto [dec3, hd3] = qoixx::qoi::decode<image_t>(enc3);
    check_true(dec3 == img3, "3ch decode roundtrip byte-identical");
    check_true(hd3 == d3, "3ch desc roundtrip (width/height/channels/colorspace)");

    // ── 2. 4 通道：encode → decode 往返 ──────────────────────────────────
    const qoixx::qoi::desc d4{.width = 8, .height = 4, .channels = 4,
                              .colorspace = qoixx::qoi::colorspace::srgb};
    image_t img4(8u * 4u * 4u);
    for (std::size_t i = 0; i < img4.size(); ++i) {
        img4[i] = static_cast<std::uint8_t>((i * 91u + 7u) & 0xFFu);
    }
    const image_t enc4 = qoixx::qoi::encode<image_t>(img4, d4);
    const auto [dec4, hd4] = qoixx::qoi::decode<image_t>(enc4);
    check_true(dec4 == img4, "4ch decode roundtrip byte-identical");
    check_true(hd4 == d4, "4ch desc roundtrip (width/height/channels/colorspace)");

    // ── 3. 确定性与重载一致性 ───────────────────────────────────────────
    check_true(qoixx::qoi::encode<image_t>(img3, d3) == enc3,
               "encode is deterministic for identical input");
    check_true(qoixx::qoi::encode<image_t>(img3.data(), img3.size(), d3) == enc3,
               "pointer overload matches container overload");

    // ── 4. QOI RLE：均匀图应显著小于原始像素 ────────────────────────────
    const qoixx::qoi::desc d64{.width = 64, .height = 64, .channels = 3,
                               .colorspace = qoixx::qoi::colorspace::srgb};
    const image_t flat(64u * 64u * 3u, 0x40);
    const image_t enc_flat = qoixx::qoi::encode<image_t>(flat, d64);
    check_true(enc_flat.size() < flat.size(), "uniform image compresses below raw size");

    // ── 5. 128x128 4ch 大图往返（aarch64 上 NEON 快路径进入构建面）───────
    const qoixx::qoi::desc dbig{.width = 128, .height = 128, .channels = 4,
                                .colorspace = qoixx::qoi::colorspace::srgb};
    image_t big(128u * 128u * 4u);
    std::uint32_t state = 0x12345678u;
    for (std::size_t i = 0; i < big.size(); ++i) {
        state = state * 1664525u + 1013904223u;
        big[i] = static_cast<std::uint8_t>(state >> 24);
    }
    const auto [decbig, hdbig] = qoixx::qoi::decode<image_t>(
        qoixx::qoi::encode<image_t>(big, dbig));
    check_true(decbig == big, "128x128 4ch roundtrip byte-identical");
    check_true(hdbig == dbig, "128x128 4ch desc roundtrip");

    // ── 6. 显式 channels 参数 ───────────────────────────────────────────
    const auto [dec3c, hd3c] = qoixx::qoi::decode<image_t>(enc3, 3);
    check_true(dec3c == img3 && hd3c == d3, "decode with explicit channels=3 matches default");

    // ── 7. 错误路径必须抛异常（不静默产出坏数据）─────────────────────────
    bool threw_short = false;
    try {
        const image_t truncated(8, 0);
        const auto r = qoixx::qoi::decode<image_t>(truncated);
        (void)r;
    } catch (const std::invalid_argument&) {
        threw_short = true;
    }
    check_true(threw_short, "decode of truncated stream throws std::invalid_argument");

    bool threw_channels = false;
    try {
        const qoixx::qoi::desc bad{.width = 4, .height = 4, .channels = 2,
                                   .colorspace = qoixx::qoi::colorspace::srgb};
        const auto r = qoixx::qoi::encode<image_t>(img3, bad);
        (void)r;
    } catch (const std::invalid_argument&) {
        threw_channels = true;
    }
    check_true(threw_channels, "encode with channels=2 throws std::invalid_argument");

    std::printf("QOIXX-CONSUMER checks=%d failures=%d\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
