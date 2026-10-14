#include <hwy/highway.h>
#include <hwy/aligned_allocator.h>
#include <hwy/targets.h>
#include <hwy/contrib/sort/vqsort.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <unistd.h>

#define CHECK(expr) do { if (!(expr)) { std::fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #expr); std::exit(1); } } while (0)
namespace hn = hwy::HWY_NAMESPACE;

int main() {
    const hn::ScalableTag<float> d;
    const size_t count = 4 * hn::Lanes(d);
    auto left = hwy::AllocateAligned<float>(count);
    auto right = hwy::AllocateAligned<float>(count);
    auto out = hwy::AllocateAligned<float>(count);
    CHECK(left && right && out);
    CHECK(reinterpret_cast<uintptr_t>(out.get()) % HWY_ALIGNMENT == 0);
    for (size_t i = 0; i < count; ++i) { left[i] = float(i); right[i] = 0.5f; }
    for (size_t i = 0; i < count; i += hn::Lanes(d)) hn::Store(hn::Add(hn::Load(d, left.get() + i), hn::Load(d, right.get() + i)), d, out.get() + i);
    for (size_t i = 0; i < count; ++i) CHECK(out[i] == float(i) + 0.5f);
    int32_t keys[] = {42, -1, 5, 0, 2147483647, -2147483647, 5, 2, 9, -4};
    const size_t n = sizeof keys / sizeof keys[0];
    hwy::VQSort(keys, n, hwy::SortAscending());
    CHECK(std::is_sorted(keys, keys + n));
    CHECK(keys[0] == -2147483647 && keys[n - 1] == 2147483647);
    CHECK(hwy::SupportedTargets() != 0);
#ifdef __OHOS__
    const char *tmp = std::getenv("TMPDIR");
    CHECK(tmp && tmp[0] == '/' && std::string(tmp).rfind("/tmp/", 0) != 0);
    const std::string path = std::string(tmp) + "/hwy-" + std::to_string(getpid()) + ".bin";
    { std::ofstream file(path, std::ios::binary); file.write(reinterpret_cast<const char *>(keys), sizeof keys); CHECK(file.good()); }
    int32_t restored[n] = {};
    { std::ifstream file(path, std::ios::binary); file.read(reinterpret_cast<char *>(restored), sizeof restored); CHECK(file.good()); }
    CHECK(std::equal(keys, keys + n, restored));
    CHECK(unlink(path.c_str()) == 0);
    std::puts("OHOS_ALIGNED_SIMD_DYNAMIC_SORT_PRIVATE_FILE_PASS");
#endif
    std::printf("HIGHWAY_API_PASS lanes=%zu targets=%lld\n", hn::Lanes(d), static_cast<long long>(hwy::SupportedTargets()));
}
