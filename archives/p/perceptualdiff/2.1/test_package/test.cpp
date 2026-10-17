/*
Consumer probe for the perceptualdiff package (test_package).

It exercises the packaged pdiff library through its public headers
(<perceptualdiff/metric.h>, <perceptualdiff/rgba_image.h>) and asserts both
functional behaviour and OHOS platform characteristics. Images are synthesised
in memory, so no external data files are required.
*/
#include <perceptualdiff/metric.h>
#include <perceptualdiff/rgba_image.h>

#include <cstdio>
#include <cstring>
#include <memory>
#include <string>
#include <unistd.h>

namespace
{

int g_passed = 0;
int g_failed = 0;

void check(const bool condition, const std::string &name)
{
    if (condition)
    {
        ++g_passed;
        std::printf("PASS: %s\n", name.c_str());
    }
    else
    {
        ++g_failed;
        std::printf("FAIL: %s\n", name.c_str());
    }
}

const unsigned int kWidth = 64;
const unsigned int kHeight = 64;

void fill_gradient(pdiff::RGBAImage &image)
{
    for (unsigned int y = 0; y < kHeight; ++y)
    {
        for (unsigned int x = 0; x < kWidth; ++x)
        {
            const unsigned char r = static_cast<unsigned char>((x * 3 + y * 5) % 256);
            const unsigned char g = static_cast<unsigned char>((x * 7 + y * 11) % 256);
            const unsigned char b = static_cast<unsigned char>((x * 13 + y * 17) % 256);
            image.set(r, g, b, 255, y * kWidth + x);
        }
    }
}

} // namespace

int main()
{
    auto a = std::make_shared<pdiff::RGBAImage>(kWidth, kHeight, "a");
    auto b = std::make_shared<pdiff::RGBAImage>(kWidth, kHeight, "b");
    auto c = std::make_shared<pdiff::RGBAImage>(kWidth, kHeight, "c");
    fill_gradient(*a);
    fill_gradient(*b);
    fill_gradient(*c);
    for (unsigned int y = 8; y < 24; ++y)
    {
        for (unsigned int x = 8; x < 24; ++x)
        {
            c->set(255, 0, 0, 255, y * kWidth + x);
        }
    }

    pdiff::PerceptualDiffParameters params;
    std::size_t failed_pixels = 0;
    float error_sum = 0.0f;
    std::string reason;

    // --- library API (consumer view) ------------------------------------
    const bool same = pdiff::yee_compare(params, *a, *b, &failed_pixels,
                                         &error_sum, &reason);
    check(same, "pdiff::yee_compare reports identical images as equal");

    failed_pixels = 0;
    const bool different = pdiff::yee_compare(params, *a, *c, &failed_pixels,
                                              &error_sum, &reason);
    check(!different, "pdiff::yee_compare reports different images as unequal");
    check(failed_pixels > 0, "pdiff::yee_compare reports a non-zero failure count");

    // --- FreeImage backed image IO --------------------------------------
    const std::string png_name = "pdiff_consumer_roundtrip.png";
    a->write_to_file(png_name);
    auto loaded = pdiff::read_from_file(png_name);
    check(loaded->get_width() == kWidth && loaded->get_height() == kHeight,
          "read_from_file/write_to_file round trip preserves dimensions");
    bool pixels_equal = true;
    for (unsigned int i = 0; i < kWidth * kHeight; ++i)
    {
        if (a->get(i) != loaded->get(i))
        {
            pixels_equal = false;
            break;
        }
    }
    check(pixels_equal, "read_from_file/write_to_file round trip preserves pixels");
    std::remove(png_name.c_str());

    // --- OHOS platform characteristics ----------------------------------
    check(sizeof(void *) == 8 && sizeof(long) == 8 && sizeof(int) == 4,
          "OHOS aarch64 LP64 data model");

    const unsigned int endian_probe = 1;
    const unsigned char first_byte =
        *reinterpret_cast<const unsigned char *>(&endian_probe);
    check(first_byte == 1, "OHOS aarch64 little endian byte order");

    auto packed = std::make_shared<pdiff::RGBAImage>(1, 1);
    packed->set(0x11, 0x22, 0x33, 0x44, 0);
    check(packed->get_red(0) == 0x11 && packed->get_green(0) == 0x22 &&
              packed->get_blue(0) == 0x33 && packed->get_alpha(0) == 0x44,
          "ABGR channel packing matches little endian layout");

#ifdef __GLIBC__
    const bool is_glibc = true;
#else
    const bool is_glibc = false;
#endif
    const std::size_t libc_info_length = confstr(_CS_GNU_LIBC_VERSION, nullptr, 0);
    check(!is_glibc && libc_info_length == 0,
          "OHOS musl libc identification (no glibc, confstr returns 0)");

#ifdef _LIBCPP_VERSION
    const bool is_libcxx = true;
#else
    const bool is_libcxx = false;
#endif
    check(is_libcxx, "OHOS clang libc++ standard library");

    bool stable = true;
    for (int round = 0; round < 16; ++round)
    {
        auto left = std::make_shared<pdiff::RGBAImage>(kWidth, kHeight);
        auto right = std::make_shared<pdiff::RGBAImage>(kWidth, kHeight);
        for (unsigned int i = 0; i < kWidth * kHeight; ++i)
        {
            left->set(10, 20, 30, 255, i);
            right->set(200, 100, 50, 255, i);
        }
        std::size_t nfailed = 0;
        const bool equal = pdiff::yee_compare(params, *left, *right, &nfailed,
                                              nullptr, nullptr);
        if (equal || nfailed == 0)
        {
            stable = false;
        }
    }
    check(stable, "API lifecycle stable over 16 repeated compare rounds");

    std::printf("\n%d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
