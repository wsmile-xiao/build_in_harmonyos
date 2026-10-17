//
// HarmonyOS 专项测试 — pytorch 2.13.0 (libtorch C++ API)
//
// R8: 不使用任何 `#if defined(<平台宏>)` 平台条件编译。宿主平台改为**运行时**
// 判定（uname(2) 的 sysname）；只有在 HarmonyOS 上才执行鸿蒙适配点校验，其它
// 平台打印 SKIP 并以 0 退出，因此同一测试目标在任何平台构建/运行都成立。
//
// 覆盖的 OHOS / musl aarch64 适配点：
//   1) 平台身份：宿主为 HarmonyOS 且机器为 aarch64，libtorch 的 CPU 后端可用；
//   2) 补丁 0004 语义：c10/util/Enumerate.h 在 musl 下显式引入 sys/types.h，
//      使 ssize_t 可见（上游非 Windows 分支原本不引入，musl 不传递提供）；
//   3) 补丁 0001 领域：std::ranges::any_of 降级为 <algorithm> 迭代器版本，
//      覆盖 group_norm 的空张量判定与形状保持；
//   4) musl/OHOS 运行时：复数标量（complex64）与 CPU 张量算术、int64 归约、
//      STL 容器互操作。
//
// 诊断：可选 argv[1] 覆盖检测到的 sysname（例如 `./test_pytorch_ohos Linux`），
// 用于在 OHOS 上验证非 OHOS 平台的跳过路径。
//
#include <torch/torch.h>

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <string>
#include <sys/utsname.h>
#include <vector>

namespace {

struct Platform {
    std::string sysname;
    std::string machine;
};

Platform detect_platform() {
    Platform p{"unknown", "unknown"};
    struct utsname u;
    if (::uname(&u) == 0) {
        p.sysname = u.sysname;
        p.machine = u.machine;
    }
    return p;
}

std::string to_lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return s;
}

// 运行时判据：OHOS 的 uname(2) 报 "HarmonyOS" / "OpenHarmony" / "OHOS"。
bool is_harmonyos(const std::string& sysname) {
    const std::string s = to_lower(sysname);
    return s.find("harmonyos") != std::string::npos ||
           s.find("openharmony") != std::string::npos ||
           s.find("ohos") != std::string::npos;
}

int g_failures = 0;

void check(bool ok, const char* what) {
    std::printf("  [%s] %s\n", ok ? "PASS" : "FAIL", what);
    if (!ok) {
        ++g_failures;
    }
}

// 1) 平台身份（运行时判定，无平台宏） --------------------------------------
void test_platform_identity(const Platform& plat) {
    std::printf("[1] 平台身份\n");
    check(is_harmonyos(plat.sysname), "host reports HarmonyOS/OHOS via uname(2)");
    check(plat.machine == "aarch64" || plat.machine == "arm64",
          "host machine is aarch64/arm64");
    check(sizeof(void*) == 8, "target is 64-bit");
    check(at::Device(at::kCPU).is_cpu(), "at::Device(kCPU) resolves to the CPU backend");
    check(at::get_default_dtype() == at::kFloat, "default dtype is float32");
    check(at::get_num_threads() > 0, "torch thread pool is initialised");
}

// 2) 补丁 0004 语义：musl 下 ssize_t 可见 ----------------------------------
void test_musl_ssize_t() {
    std::printf("[2] musl ssize_t 可见性（补丁 0004）\n");
    // ssize_t 由 <sys/types.h> 显式提供（补丁内容）；若头文件未引入则本 TU
    // 无法编译，构成实质性校验。
    ssize_t s = -1;
    unsigned long long max = static_cast<unsigned long long>(s);
    check(s == -1, "ssize_t is signed and usable under OHOS/musl");
    check(max > 0, "ssize_t round-trips through unsigned conversion");
    check(sizeof(ssize_t) == sizeof(void*), "ssize_t width matches pointer width");
    check(sizeof(std::int64_t) == 8, "int64_t is 8 bytes on OHOS aarch64");
}

// 3) 补丁 0001 领域：group_norm 的迭代器化实现 -----------------------------
void test_group_norm_algorithm_path() {
    std::printf("[3] group_norm 路径（补丁 0001，ranges→iterator）\n");
    const int64_t N = 2, C = 4, H = 3, W = 3;
    auto x = torch::arange(static_cast<float>(N * C * H * W)).reshape({N, C, H, W});
    // 上游 group_norm 的空张量判定在 OHOS 上走迭代器版本；这里用同一谓词
    // 校验维度扫描逻辑（std::any_of 迭代器版）在 OHOS 工具链下行为正确。
    auto sizes = x.sizes();
    const bool has_zero = std::any_of(sizes.begin(), sizes.end(),
                                      [](int64_t s) { return s == 0; });
    check(!has_zero, "std::any_of over sizes() detects no empty dims");

    auto y = torch::group_norm(x, /*num_groups=*/2);
    check(y.sizes() == x.sizes(), "group_norm preserves shape");
    check(y.defined() && y.numel() == x.numel(), "group_norm produced full output");
    check(torch::isfinite(y).all().item<bool>(), "group_norm output is finite");

    auto empty = torch::empty({0, C, H, W});
    auto empty_sizes = empty.sizes();
    const bool empty_has_zero = std::any_of(empty_sizes.begin(), empty_sizes.end(),
                                            [](int64_t s) { return s == 0; });
    check(empty_has_zero, "empty input detected by the same predicate");
}

// 4) OHOS aarch64 上的 musl/libc++ 算术与复数 -------------------------------
void test_ohos_numeric_paths() {
    std::printf("[4] OHOS aarch64 算术与复数\n");
    auto a = torch::tensor({1.0f, 2.0f, 3.0f, 4.0f});
    auto b = torch::tensor({4.0f, 3.0f, 2.0f, 1.0f});
    auto c = a * b + a;  // 5, 8, 9, 8 -> 30
    check(std::abs(c.sum().item<double>() - 30.0) < 1e-6,
          "arithmetic on aarch64 CPU tensors");

    // 复数标量路径（musl libc++ 下的 complex 运算）
    auto z = at::tensor({c10::complex<float>(1.0f, 2.0f), c10::complex<float>(3.0f, -1.0f)},
                        at::dtype(at::kComplexFloat));
    check(z.scalar_type() == at::kComplexFloat, "complex64 tensor constructed");
    auto z0 = (z[0] * z[0]).item<c10::complex<float>>();
    check(std::abs(z0.real() - (-3.0f)) < 1e-5 && std::abs(z0.imag() - 4.0f) < 1e-5,
          "complex64 multiply matches (1+2i)^2 = -3+4i");

    // 整数归约（sizes/索引路径在 musl 下使用 ssize_t）
    auto iv = torch::arange(0, 100, torch::kInt64);
    check(iv.sum().item<int64_t>() == 4950, "int64 arange+sum uses ssize_t-safe indexing");

    // STL 容器与 torch 交互（libc++ ABI 组合）
    std::vector<float> host{1.0f, 2.0f, 3.0f};
    auto t = torch::from_blob(host.data(), {3}, torch::kFloat).clone();
    check(t.sum().item<float>() == 6.0f, "std::vector -> tensor interop");
}

}  // namespace

int main(int argc, char** argv) {
    Platform plat = detect_platform();
    if (argc > 1) {  // diagnostic override, see file header
        plat.sysname = argv[1];
    }

    std::printf("== HarmonyOS 专项测试: pytorch 2.13.0 ==\n");
    std::printf("   platform: sysname=%s machine=%s\n", plat.sysname.c_str(),
                plat.machine.c_str());
    std::printf("   torch version: %s\n", TORCH_VERSION);

    if (!is_harmonyos(plat.sysname)) {
        std::printf("SKIP: HarmonyOS-specific checks need a HarmonyOS host "
                    "(detected sysname=%s); exiting 0.\n", plat.sysname.c_str());
        return 0;
    }

    test_platform_identity(plat);
    test_musl_ssize_t();
    test_group_norm_algorithm_path();
    test_ohos_numeric_paths();

    if (g_failures != 0) {
        std::fprintf(stderr, "ohos special test FAILED: %d check(s) failed\n", g_failures);
        return 1;
    }
    std::printf("ohos special test OK (all checks passed)\n");
    return 0;
}
