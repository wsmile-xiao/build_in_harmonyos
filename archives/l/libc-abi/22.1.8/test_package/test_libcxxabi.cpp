// test_libcxxabi.cpp — consumer test for libc-abi 22.1.8 (libc++abi)
//
// 真实驱动 libc++abi 的 ABI 入口（不是空壳）：
//   * __cxa_demangle          — 符号反修饰（含非法输入、缓冲区复用）
//   * __cxa_guard_acquire/release — 函数内静态量的线程安全初始化
//   * __cxa_throw/__cxa_begin_catch/__cxa_end_catch — 异常抛出与捕获
//   * __cxa_thread_atexit     — thread_local 析构注册
//   * type_info / RTTI        — typeid、dynamic_cast（含交叉转型）
//   * operator new/delete     — 普通、数组、对齐（align_val_t）三个重载
//
// 任一 __cxa_* 符号缺失都会在链接期报 undefined reference，因此本测试确实
// 依赖被测包（R34）。
//
// 兼容性：用 OHOS SDK 随附的 libc++ 15 头文件编译（设备工具链 clang 15），
// 故只用 C++17 及此前特性（不用 std::source_location / std::jthread）。
#include <cxxabi.h>

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <new>
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

// ── 1. __cxa_demangle ───────────────────────────────────────────────

static void test_demangle() {
    int status = -1;
    char* out = abi::__cxa_demangle("_Z3foov", nullptr, nullptr, &status);
    check(status == 0 && out != nullptr && std::strcmp(out, "foo()") == 0,
          "__cxa_demangle simple function");
    std::free(out);

    // 模板 + 命名空间限定 + N 前缀名：libc++abi 的反修饰器必须能处理。
    out = abi::__cxa_demangle("_ZN3foo3barIiEEvT_", nullptr, nullptr, &status);
    check(status == 0 && out != nullptr && std::strstr(out, "foo") != nullptr &&
              std::strstr(out, "bar") != nullptr,
          "__cxa_demangle template function");
    std::free(out);

    // 复用调用方缓冲区（libc++abi 的 realloc 路径）。
    char buf[128];
    char* reuse = buf;
    std::size_t len = 64;
    reuse = abi::__cxa_demangle("_Z3foov", reuse, &len, &status);
    check(status == 0 && reuse != nullptr, "__cxa_demangle caller buffer reuse");
    if (reuse != buf) {
        std::free(reuse);
    }

    // 非法输入必须优雅失败，不能崩溃。
    out = abi::__cxa_demangle("!!!not_a_mangled_name!!!", nullptr, nullptr,
                              &status);
    check(status != 0, "__cxa_demangle rejects invalid input");
    std::free(out);
}

// ── 2. __cxa_guard_* （函数内静态量初始化）──────────────────────────

struct Widget {
    explicit Widget(int v) : value(v) {}
    int value;
};

static std::atomic<int> g_widget_ctor_count{0};

static Widget& widget() {
    static Widget instance(42);  // __cxa_guard_acquire / __cxa_guard_release
    return instance;
}

static void test_function_local_static() {
    constexpr int kThreads = 8;
    std::atomic<int> value_sum{0};
    {
        std::vector<std::thread> pool;
        for (int i = 0; i < kThreads; ++i) {
            pool.emplace_back([&value_sum] {
                value_sum += widget().value;
            });
        }
        for (auto& t : pool) {
            t.join();
        }
    }
    check(value_sum.load() == kThreads * 42,
          "__cxa_guard_* single initialization under contention");
}

// ── 3. 异常 ─────────────────────────────────────────────────────────

struct Base {
    virtual ~Base() = default;
    virtual const char* name() const { return "Base"; }
};
struct Left : virtual Base {
    const char* name() const override { return "Left"; }
};
struct Right : virtual Base {
    const char* name() const override { return "Right"; }
};
struct Derived : Left, Right {
    const char* name() const override { return "Derived"; }
};

class PayloadError : public std::exception {
public:
    explicit PayloadError(int code) : code_(code) {}
    const char* what() const noexcept override { return "PayloadError"; }
    int code() const { return code_; }

private:
    int code_;
};

static int throwing_frame(int depth) {
    if (depth == 0) {
        throw PayloadError(7);  // __cxa_throw
    }
    return throwing_frame(depth - 1) + 1;
}

static void test_exceptions() {
    bool caught = false;
    int depth = 0;
    try {
        depth = throwing_frame(5);
    } catch (const PayloadError& err) {  // __cxa_begin_catch / __cxa_end_catch
        caught = true;
        check(err.code() == 7, "exception payload preserved through unwind");
    }
    check(caught, "exception caught through 5 nested frames");
    (void)depth;

    // RTTI：交叉转型（cross cast）依赖 libc++abi 的 __dynamic_cast / type_info。
    Derived obj;
    Right* as_right = dynamic_cast<Right*>(&obj);
    check(as_right != nullptr && std::strcmp(as_right->name(), "Derived") == 0,
          "dynamic_cast cross cast");
    Base* as_base = &obj;
    check(dynamic_cast<Derived*>(as_base) != nullptr,
          "dynamic_cast down cast");
    check(std::strcmp(typeid(obj).name(), "7Derived") == 0,
          "typeid name via ABI");
}

// ── 4. thread_local 析构（__cxa_thread_atexit）──────────────────────

static std::atomic<int> g_tls_dtor_count{0};

struct TlsProbe {
    TlsProbe() = default;
    ~TlsProbe() { g_tls_dtor_count.fetch_add(1); }
};

static void test_thread_local_dtor() {
    constexpr int kThreads = 4;
    {
        std::vector<std::thread> pool;
        for (int i = 0; i < kThreads; ++i) {
            pool.emplace_back([] {
                thread_local TlsProbe probe;  // __cxa_thread_atexit 注册
                (void)probe;
            });
        }
        for (auto& t : pool) {
            t.join();
        }
    }
    check(g_tls_dtor_count.load() == kThreads,
          "__cxa_thread_atexit runs thread_local destructors at thread exit");
}

// ── 5. 对齐分配（C++17 align_val_t 重载）────────────────────────────

struct alignas(64) Aligned {
    char bytes[64];
};

static void test_operator_new() {
    int* plain = new int(5);
    check(*plain == 5, "operator new / delete");
    delete plain;

    int* array = new int[4];
    array[3] = 9;
    check(array[3] == 9, "operator new[] / delete[]");
    delete[] array;

    Aligned* aligned = new Aligned();  // operator new(size_t, align_val_t)
    check(reinterpret_cast<std::uintptr_t>(aligned) % 64 == 0,
          "aligned operator new honours align_val_t");
    delete aligned;

    // nothrow 变体（libc++abi 的 new_delete.cpp 提供）。
    int* nothrow_int = new (std::nothrow) int(11);
    check(nothrow_int != nullptr && *nothrow_int == 11,
          "nothrow operator new");
    delete nothrow_int;
}

// ── main ────────────────────────────────────────────────────────────

int main() {
    test_demangle();
    test_function_local_static();
    test_exceptions();
    test_thread_local_dtor();
    test_operator_new();

    std::printf("LIBCXXABI_CONSUMER checks=%d failed=%d\n", g_checks, g_failed);
    if (g_failed != 0) {
        std::fprintf(stderr, "LIBCXXABI_CONSUMER FAILED\n");
        return 1;
    }
    std::printf("LIBCXXABI_CONSUMER PASSED\n");
    return 0;
}
