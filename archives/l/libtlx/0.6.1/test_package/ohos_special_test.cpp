// ohos_special_test.cpp — libtlx 0.6.1 HarmonyOS PC 平台专项测试
// `#ifdef __OHOS__` 真实质校验（非空壳）：
//   1. OHOS 工具链宏探针（__OHOS__/__OHOS_FAMILY__/aarch64）
//   2. 字节序与位宽（tlx endian 宏 + C++ 标准断言）
//   3. 静态库符号真实链接（调用 libtlx.a 编译单元内的 4 个模块）
//   4. pthread（musl libc）真实多线程
//   5. 文件系统路径行为（tlx::port::setenv + 展开环境变量）
// 末尾打印 PASS 汇总行供判读。
#include <tlx/define/endian.hpp>
#include <tlx/digest/md5.hpp>
#include <tlx/string/expand_environment_variables.hpp>
#include <tlx/port/setenv.hpp>
#include <tlx/string.hpp>
#include <tlx/thread_pool.hpp>

#include <atomic>
#include <cstdio>
#include <cstdint>
#include <thread>
#include <type_traits>

static int g_checks = 0;
static int g_fails = 0;
#define CHECK(cond)                                                            \
  do {                                                                         \
    ++g_checks;                                                                \
    if (!(cond)) {                                                             \
      ++g_fails;                                                               \
      std::printf("[ohos][FAIL] %s:%d: %s\n", __FILE__, __LINE__, #cond);      \
    }                                                                          \
  } while (0)

#if defined(__OHOS__) || defined(__OHOS_FAMILY__)

static void test_ohos_toolchain() {
    // OHOS clang 工具链宏（llvm 15.0.4 aarch64-unknown-linux-ohos 实测定义）
#ifdef __OHOS__
    CHECK(true);
#else
    CHECK(false);  // __OHOS__ 必须已定义
#endif
#ifdef __OHOS_FAMILY__
    CHECK(true);
#else
    CHECK(false);
#endif
    CHECK(sizeof(void*) == 8);              // 64 位指针
#if defined(__aarch64__)
    CHECK(true);
#else
    CHECK(false);                          // 目标架构 aarch64
#endif
    CHECK(__clang_major__ == 15);           // OHOS SDK clang 15
}

static void test_endian_and_abi() {
    // tlx endian 宏与运行时实测一致（aarch64 小端）
#if defined(TLX_LITTLE_ENDIAN)
    CHECK(true);
#elif defined(TLX_BIG_ENDIAN)
    CHECK(false);  // OHOS aarch64 必须小端
#endif
    std::uint32_t probe = 0x01020304;
    std::uint8_t first = reinterpret_cast<std::uint8_t*>(&probe)[0];
    CHECK(first == 0x04);  // 小端：低字节在低地址

    // C++ 标准库 ABI 基本面（libc++）
    CHECK(std::is_trivially_copyable<std::uint64_t>::value);
    static_assert(sizeof(std::size_t) == 8, "64-bit size_t");
}

static void test_static_lib_symbols() {
    // 依次调用 libtlx.a 内不同编译单元的符号，验证静态归档链接完整性
    // digest/md5.cpp
    CHECK(tlx::md5_hex("abc") == "900150983cd24fb0d6963f7d28e17f72");
    // string/ssprintf.cpp
    CHECK(tlx::ssprintf("%s-%d", "ohos", 1) == "ohos-1");
    // string/expand_environment_variables.cpp（无变量串原样返回；
    // 真实展开行为在 test_filesystem_env 用受控变量验证）
    CHECK(tlx::expand_environment_variables("no variable here") == "no variable here");
    // string/base64.cpp
    CHECK(tlx::base64_encode(std::string("\x01\x02\x03", 3)) == "AQID");
}

static void test_pthreads() {
    // musl libc pthread：多生产者原子计数（与 consumer ThreadPool 测试互补的裸线程路径）
    std::atomic<int> total{0};
    std::thread producers[4];
    for (int t = 0; t < 4; ++t) {
        producers[t] = std::thread([&total] {
            for (int i = 0; i < 250; ++i) ++total;
        });
    }
    for (auto& th : producers) th.join();
    CHECK(total.load() == 1000);

    // hardware_concurrency 可用（OHOS sched 接口）
    unsigned hc = std::thread::hardware_concurrency();
    CHECK(hc > 0);
}

static void test_filesystem_env() {
    // port/setenv.cpp：tlx::setenv + 展开环境变量（真实写环境并读回）
    tlx::setenv("TLX_OHOS_PROBE", "harmony", 1);
    CHECK(tlx::expand_environment_variables("$TLX_OHOS_PROBE") == "harmony");
    CHECK(tlx::expand_environment_variables("x${TLX_OHOS_PROBE}y") == "xharmonyy");
    CHECK(tlx::expand_environment_variables("$UNDEFINED_TLX_VAR_XYZ") == "");
}

#else
// 非 OHOS 平台不空跑：直接失败退出（本测试存在的意义就是 OHOS 专项）
#error "ohos_special_test.cpp must be built on OHOS toolchain"
#endif

int main() {
    test_ohos_toolchain();
    test_endian_and_abi();
    test_static_lib_symbols();
    test_pthreads();
    test_filesystem_env();

    if (g_fails == 0) {
        std::printf("ohos_special_test: PASS %d/%d assertions\n",
                    g_checks, g_checks);
        return 0;
    }
    std::printf("ohos_special_test: FAIL %d/%d assertions\n",
                g_checks - g_fails, g_checks);
    return 1;
}
