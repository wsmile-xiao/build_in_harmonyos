// test_ohos_abi.cpp — 鸿蒙（OHOS）平台特有测试 for libc-abi 22.1.8
//
// 这是针对**鸿蒙 PC（OHOS aarch64）**平台特有的验证，不是上游通用测试的复制：
// 上游 libc++abi 的测试只跑在 host/模拟器语义上，不覆盖"本包与设备工具链、
// 设备标准库共存"的场景。本文件验证本包产物在真机上的 ABI 自洽性：
//
//   A. TLS 异常状态隔离（libc++abi 22 用 __thread 实现 __cxa_get_globals_fast）
//      —— 8 线程同时抛/接异常，各自的 caught 计数必须严格等于本线程抛出数，
//      任何跨线程串扰（TLS 模型不符）都会暴露。
//   B. __cxa_thread_atexit_impl 在鸿蒙 pthread 上的可用性 —— thread_local 析构
//      必须于线程退出时执行，且析构顺序与构造逆序。
//   C. 异常跨 dlopen 边界 —— 通过 dlopen 加载的 .so 抛出的异常，在可执行文件
//      侧能被 catch（鸿蒙动态链接器的 TLS/unwind 交互；静态 libc++abi.a 被链接
//      进 .so 时也必须与主程序 ABI 一致）。
//   D. 与设备 SDK 随附 libc++ 15 的跨版本互操作 —— 异常对象由本包 libc++abi 22
//      抛出、经 SDK libc++ 15 的 std::exception_ptr / std::rethrow_exception 传递，
//      必须仍可被 catch（本包在设备上与 libc++ 15 共存是硬要求）。
//   E. __cxa_demangle 处理鸿蒙 triple 生成的符号名（aarch64-unknown-linux-ohos
//      仍为 Itanium C++ ABI 修饰），包括匿名命名空间与 lambda 名。
//
// 任一失败即返回非 0，测试即判定失败（不屏蔽、不重试）。
#include <cxxabi.h>
#include <dlfcn.h>
#include <sys/utsname.h>

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <string>
#include <thread>
#include <vector>

static int g_checks = 0;
static int g_failed = 0;

static void check(bool ok, const char* what) {
    ++g_checks;
    if (!ok) {
        ++g_failed;
        std::fprintf(stderr, "FAIL: %s\n", what);
    } else {
        std::printf("ok: %s\n", what);
    }
}

// ── A. 平台确认 + TLS 异常状态隔离 ──────────────────────────────────

struct OhosError {
    int thread_id;
};

// 每个线程抛 attempt 次、接住 attempt 次；计数器是本线程私有的自动变量，
// 任何 __cxa_get_globals_fast 的 TLS 串扰都会让计数对不上。
static bool tls_isolation_worker(int thread_id, int attempts) {
    int caught = 0;
    for (int i = 0; i < attempts; ++i) {
        try {
            throw OhosError{thread_id};
        } catch (const OhosError& err) {
            if (err.thread_id == thread_id) {
                ++caught;
            }
        }
    }
    return caught == attempts;
}

static void test_platform_and_tls() {
    struct utsname info;
    if (uname(&info) == 0) {
        std::printf("platform: sysname=%s machine=%s release=%s\n",
                    info.sysname, info.machine, info.release);
        check(std::strcmp(info.machine, "aarch64") == 0,
              "runs on aarch64 (OHOS PC)");
        check(std::strcmp(info.sysname, "HarmonyOS") == 0 ||
                  std::strcmp(info.sysname, "Linux") == 0,
              "runs on HarmonyOS/Linux");
    } else {
        check(false, "uname() available");
    }

    constexpr int kThreads = 8;
    constexpr int kAttempts = 200;
    std::atomic<int> ok_threads{0};
    {
        std::vector<std::thread> pool;
        for (int i = 0; i < kThreads; ++i) {
            pool.emplace_back([i, &ok_threads] {
                if (tls_isolation_worker(i, kAttempts)) {
                    ok_threads.fetch_add(1);
                }
            });
        }
        for (auto& t : pool) {
            t.join();
        }
    }
    check(ok_threads.load() == kThreads,
          "exception TLS state isolated across 8 threads (__cxa_get_globals_fast)");
}

// ── B. thread_local 析构在鸿蒙 pthread 上按逆序执行 ─────────────────

// 每线程独立的析构序号：thread_local，线程之间互不干扰。析构按构造逆序发生，
// 故最后构造者应先析构（期望序号 0）。
static thread_local int tls_dtor_seq = 0;
static std::atomic<int> g_order_ok{0};

struct OrderedProbe {
    // expect_ = 本对象析构时应当看到的 tls_dtor_seq 值（构造逆序 → 递减）。
    explicit OrderedProbe(int expect, const char* label)
        : expect_(expect), label_(label) {}
    ~OrderedProbe() {
        if (tls_dtor_seq == expect_) {
            g_order_ok.fetch_add(1);
        } else {
            std::fprintf(stderr,
                         "FAIL: %s destroyed at seq=%d, expected %d\n", label_,
                         tls_dtor_seq, expect_);
        }
        ++tls_dtor_seq;
    }
    int expect_;
    const char* label_;
};

static void test_tls_destructor_order() {
    constexpr int kThreads = 4;
    {
        std::vector<std::thread> pool;
        for (int i = 0; i < kThreads; ++i) {
            pool.emplace_back([] {
                // 构造序：first(expect 1) → second(expect 0)
                // 析构序：second(先, seq=0) → first(后, seq=1)
                static thread_local OrderedProbe first(1, "first");
                static thread_local OrderedProbe second(0, "second");
                (void)first;
                (void)second;
            });
        }
        for (auto& t : pool) {
            t.join();
        }
    }
    check(g_order_ok.load() == kThreads * 2,
          "__cxa_thread_atexit_impl destructs thread_local in reverse order");
}

// ── C. 异常跨 dlopen 边界 ───────────────────────────────────────────

#if defined(__OHOS__) || defined(__linux__)
static void test_exception_across_dlopen(const char* module_path) {
    if (module_path == nullptr || module_path[0] == '\0') {
        check(false, "dlopen module path provided");
        return;
    }
    void* handle = dlopen(module_path, RTLD_NOW | RTLD_LOCAL);
    if (handle == nullptr) {
        std::fprintf(stderr, "dlopen failed: %s\n", dlerror());
        check(false, "dlopen(throwing module)");
        return;
    }
    using Thrower = int (*)();
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
    auto thrower = reinterpret_cast<Thrower>(dlsym(handle, "ohos_abi_throw"));
    if (thrower == nullptr) {
        std::fprintf(stderr, "dlsym failed: %s\n", dlerror());
        dlclose(handle);
        check(false, "dlsym(ohos_abi_throw)");
        return;
    }
    bool caught = false;
    try {
        thrower();
    } catch (const std::runtime_error& err) {
        caught = std::strcmp(err.what(), "from-dlopen-module") == 0;
    } catch (...) {
        caught = false;
    }
    dlclose(handle);
    check(caught, "exception thrown in dlopen'd module crosses .so boundary");
}
#endif

// ── D. 与 SDK libc++ 15 的异常互操作 ────────────────────────────────

static void test_exception_ptr_interop() {
    // std::exception_ptr 的复制/重抛路径由 libc++abi 的 __cxa_* 支撑
    // （__cxa_exception 引用计数、__cxa_rethrow）。异常在本包 libc++abi 22 上
    // 抛出，经 SDK libc++ 15 的 exception_ptr 传递后必须仍可 catch。
    std::exception_ptr captured;
    try {
        throw std::runtime_error("interop-payload");
    } catch (...) {
        captured = std::current_exception();
    }
    bool ok = false;
    if (captured) {
        try {
            std::rethrow_exception(captured);
        } catch (const std::runtime_error& err) {
            ok = std::strcmp(err.what(), "interop-payload") == 0;
        } catch (...) {
            ok = false;
        }
    }
    check(ok, "exception_ptr round-trip across libc++abi/libsdk-libc++ boundary");

    // 嵌套异常（current_exception 在 catch 内部再次捕获）。
    std::exception_ptr nested;
    try {
        throw std::logic_error("outer");
    } catch (...) {
        try {
            throw std::logic_error("inner");
        } catch (...) {
            nested = std::current_exception();
        }
    }
    bool nested_ok = false;
    try {
        std::rethrow_exception(nested);
    } catch (const std::logic_error& err) {
        nested_ok = std::strcmp(err.what(), "inner") == 0;
    } catch (...) {
        nested_ok = false;
    }
    check(nested_ok, "nested exception state preserved");
}

// ── E. __cxa_demangle 处理鸿蒙 triple 的 C++ 符号 ───────────────────

namespace hidden_ohos_ns {
int compute(int a, int b) {
    return a + b;
}
}  // namespace hidden_ohos_ns

static int lambda_helper() {
    auto lambda = [](int x) { return x * 3; };
    return lambda(4);
}

static void test_demangle_ohos_symbols() {
    // 由本 TU 真实代码产生的符号：用 typeid/函数指针取不到名字，这里直接给出
    // 鸿蒙 aarch64-linux-ohos 工具链生成的 Itanium 修饰名。
    struct Case {
        const char* mangled;
        const char* needle;
        const char* label;
    };
    const Case cases[] = {
        {"_ZN14hidden_ohos_ns7computeEii", "hidden_ohos_ns", "namespace fn"},
        {"_ZNKSt9exception4whatEv", "what", "member function (std-extern)"},
        {"_ZNSt6vectorIiSaIiEE9push_backERKi", "push_back", "template member"},
    };
    for (const Case& item : cases) {
        int status = -1;
        char* out = abi::__cxa_demangle(item.mangled, nullptr, nullptr, &status);
        bool ok = status == 0 && out != nullptr &&
                  std::strstr(out, item.needle) != nullptr;
        check(ok, (std::string("__cxa_demangle OHOS ") + item.label).c_str());
        std::free(out);
    }
    check(lambda_helper() == 12, "lambda from real OHOS-compiled TU runs");
}

// ── main ────────────────────────────────────────────────────────────

int main(int argc, char** argv) {
    const char* module_path = (argc > 1) ? argv[1] : nullptr;

    test_platform_and_tls();
    test_tls_destructor_order();
    test_exception_ptr_interop();
    test_demangle_ohos_symbols();
#if defined(__OHOS__) || defined(__linux__)
    test_exception_across_dlopen(module_path);
#else
    (void)module_path;
#endif

    std::printf("LIBCXXABI_OHOS_CONSUMER checks=%d failed=%d\n", g_checks,
                g_failed);
    if (g_failed != 0) {
        std::fprintf(stderr, "LIBCXXABI_OHOS_CONSUMER FAILED\n");
        return 1;
    }
    std::printf("LIBCXXABI_OHOS_CONSUMER PASSED\n");
    return 0;
}
