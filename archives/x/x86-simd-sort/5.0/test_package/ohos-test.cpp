// HarmonyOS 专项测试: x86-simd-sort 5.0 on OHOS aarch64
//
// 该测试不是上游测试的复述, 而是针对本次适配实际产生的平台差异点做真实验证:
//   1. aarch64/OHOS 上 x86 SIMD 分派被编译剔除, 库必须经 scalar 路径正确排序
//      (比较 std::sort 的可观察结果, 覆盖 qsort/argsort/qselect/partial_qsort)
//   2. 上游 compare 的 NAN > INF 语义 (hasnan=true 时 NaN 必须排在末尾)
//   3. keyvalue_qsort 与 object_qsort 的公开 API 在 OHOS 上可用且正确
#include <x86simdsort.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <functional>
#include <limits>
#include <numeric>
#include <string>
#include <vector>

namespace {

int failures = 0;

void expect(bool cond, const char *name)
{
    std::printf("[%s] %s\n", cond ? "PASS" : "FAIL", name);
    if (!cond) ++failures;
}

// 1) qsort 与 std::sort 在 OHOS aarch64 上结果一致 (scalar 路径)。
void check_qsort_against_std()
{
    const size_t n = 65536;
    std::vector<uint64_t> arr(n);
    uint64_t s = 0x243F6A8885A308D3ULL;
    for (size_t i = 0; i < n; ++i) {
        s = s * 6364136223846793005ULL + 1442695040888963407ULL;
        arr[i] = s >> 33;
    }
    std::vector<uint64_t> ref(arr);
    std::sort(ref.begin(), ref.end());
    x86simdsort::qsort(arr.data(), n, false);
    expect(arr == ref, "qsort(uint64, n=65536) == std::sort");
}

// 2) argsort 返回的索引是置换且取值有序。
void check_argsort_permutation()
{
    const size_t n = 8192;
    std::vector<double> arr(n);
    for (size_t i = 0; i < n; ++i) {
        arr[i] = static_cast<double>((i * 2654435761ULL) % 1000003) / 11.0;
    }
    std::vector<size_t> idx = x86simdsort::argsort(arr.data(), n, false);
    bool ok = idx.size() == n;
    if (ok) {
        std::vector<bool> seen(n, false);
        for (size_t i = 0; i < n; ++i) {
            if (idx[i] >= n || seen[idx[i]]) { ok = false; break; }
            seen[idx[i]] = true;
            if (i > 0 && arr[idx[i - 1]] > arr[idx[i]]) { ok = false; break; }
        }
    }
    expect(ok, "argsort(double, n=8192) permutation+sorted");
}

// 3) qselect 找到第 k 小元素。
void check_qselect()
{
    const size_t n = 4096, k = 1234;
    std::vector<int32_t> arr(n);
    uint64_t s = 0x9E3779B97F4A7C15ULL;
    for (size_t i = 0; i < n; ++i) {
        s = s * 6364136223846793005ULL + 1;
        arr[i] = static_cast<int32_t>(s >> 32);
    }
    std::vector<int32_t> ref(arr);
    std::nth_element(ref.begin(), ref.begin() + k, ref.end());
    x86simdsort::qselect(arr.data(), k, n, false);
    expect(arr[k] == ref[k], "qselect(int32, k=1234) == nth_element");
}

// 4) partial_qsort 前 k 个有序。
void check_partial_qsort()
{
    const size_t n = 2048, k = 200;
    std::vector<float> arr(n);
    uint64_t s = 0xDEADBEEFCAFEBABEULL;
    for (size_t i = 0; i < n; ++i) {
        s = s * 6364136223846793005ULL + 1;
        arr[i] = static_cast<float>((s >> 32) % 100000) / 3.0f;
    }
    x86simdsort::partial_qsort(arr.data(), k, n, false);
    bool ok = true;
    for (size_t i = 1; i < k; ++i) {
        if (arr[i - 1] > arr[i]) { ok = false; break; }
    }
    expect(ok, "partial_qsort(float, k=200) prefix sorted");
}

// 5) hasnan=true 时 NaN 排到末尾 (NAN > INF 语义)。
void check_nan_tail()
{
    const size_t n = 512;
    std::vector<double> arr(n);
    uint64_t s = 0x1ULL;
    for (size_t i = 0; i < n; ++i) {
        s = s * 6364136223846793005ULL + 1;
        arr[i] = static_cast<double>((s >> 32) % 1000) / 7.0;
    }
    arr[17] = std::numeric_limits<double>::infinity();
    arr[33] = std::numeric_limits<double>::quiet_NaN();
    arr[99] = -std::numeric_limits<double>::infinity();
    arr[200] = std::numeric_limits<double>::quiet_NaN();
    x86simdsort::qsort(arr.data(), n, true);
    bool ok = true;
    size_t first_nan = n;
    for (size_t i = 0; i < n; ++i) {
        if (arr[i] != arr[i]) {  // is NaN
            first_nan = i;
            break;
        }
    }
    for (size_t i = first_nan; i < n; ++i) {
        if (arr[i] == arr[i]) { ok = false; break; }  // non-NaN after first NaN
    }
    for (size_t i = 1; i < first_nan; ++i) {
        if (arr[i - 1] > arr[i]) { ok = false; break; }
    }
    expect(ok, "qsort(hasnan=true) NaNs at tail (NAN>INF)");
}

// 6) keyvalue_qsort 键值同步排序。
void check_keyvalue_qsort()
{
    const size_t n = 2048;
    std::vector<uint32_t> key(n);
    std::vector<int64_t> val(n);  // val 携带原始下标，用于复核键值配对
    uint64_t s = 0xABCDEF0123456789ULL;
    for (size_t i = 0; i < n; ++i) {
        s = s * 6364136223846793005ULL + 1;
        key[i] = static_cast<uint32_t>(s >> 33);
        val[i] = static_cast<int64_t>(i);
    }
    // 排序前键值快照
    std::vector<uint32_t> orig_key(key);
    std::vector<int64_t> orig_val(val);
    x86simdsort::keyvalue_qsort(key.data(), val.data(), n, false);
    bool ok = std::is_sorted(key.begin(), key.end());
    if (ok) {
        for (size_t i = 0; i < n; ++i) {
            // 新位置 i 处的 val 是原始下标；该下标对应的原始键/原始值必须与当前位置一致
            const size_t orig = static_cast<size_t>(val[i]);
            if (orig >= n || orig_key[orig] != key[i] || orig_val[orig] != val[i]) {
                ok = false;
                break;
            }
        }
    }
    expect(ok, "keyvalue_qsort(uint32,int64) key-value paired");
}

// 7) object_qsort 按 key_func 排序对象数组。
void check_object_qsort()
{
    struct Item { int32_t key; int32_t payload; };
    const size_t n = 1024;
    std::vector<Item> arr(n);
    uint64_t s = 0x1122334455667788ULL;
    for (size_t i = 0; i < n; ++i) {
        s = s * 6364136223846793005ULL + 1;
        arr[i] = Item{static_cast<int32_t>(s >> 33), static_cast<int32_t>(i)};
    }
    x86simdsort::object_qsort(arr.data(), static_cast<uint32_t>(n),
                              [](const Item &it) { return it.key; });
    bool ok = true;
    for (size_t i = 1; i < n; ++i) {
        if (arr[i - 1].key > arr[i].key) { ok = false; break; }
    }
    expect(ok, "object_qsort(Item, n=1024) sorted by key");
}

} // namespace

int main()
{
    std::printf("target: OHOS aarch64, sizeof(size_t)=%zu, arch=%s\n",
                sizeof(size_t),
#if defined(__aarch64__)
                "aarch64"
#elif defined(__x86_64__)
                "x86_64"
#else
                "unknown"
#endif
    );
    check_qsort_against_std();
    check_argsort_permutation();
    check_qselect();
    check_partial_qsort();
    check_nan_tail();
    check_keyvalue_qsort();
    check_object_qsort();
    std::printf("%d checks, %d failed\n", 7, failures);
    return failures == 0 ? 0 : 1;
}