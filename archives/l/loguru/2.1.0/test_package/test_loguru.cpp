/* test_package/test_loguru.cpp — loguru 2.1.0 (emilk) 消费者测试
   验证打包的 loguru.hpp + loguru.cpp 可被消费：单 TU #include <loguru.cpp>
   （README 官方推荐用法）把实现编译进测试，覆盖 init + add_file 文件
   sink + add_callback 回调捕获 + LOG_F printf 风格日志 + remove_callback
   + 版本宏，共 9 项断言。
*/
#include <loguru.cpp>

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

static std::vector<std::string> g_captured;

static void capture_cb(void* /*user_data*/, const loguru::Message& message)
{
    g_captured.push_back(message.message ? message.message : "");
}

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond) do { \
    ++g_checks; \
    if (!(cond)) { ++g_failures; std::printf("FAIL: %s\n", #cond); } \
} while (0)

int main(int argc, char* argv[])
{
    loguru::init(argc, argv);

    // 1-3) 打包版本为 2.1.0（版本宏，loguru.hpp:96-98）
    CHECK(LOGURU_VERSION_MAJOR == 2);
    CHECK(LOGURU_VERSION_MINOR == 1);
    CHECK(LOGURU_VERSION_PATCH == 0);

    // 4) 文件 sink：Truncate 模式，INFO 级别过滤，创建成功
    CHECK(loguru::add_file("consumer_test.log", loguru::Truncate,
                           loguru::Verbosity_INFO) == true);

    // 5-7) 回调捕获 LOG_F printf 风格日志
    loguru::add_callback("capture", capture_cb, nullptr, loguru::Verbosity_INFO);
    LOG_F(INFO, "hello from loguru %d", 42);
    CHECK(g_captured.size() == 1);
    if (!g_captured.empty()) {
        CHECK(g_captured[0].find("hello from loguru 42") != std::string::npos);
    }

    // 8) remove_callback 找到并移除
    CHECK(loguru::remove_callback("capture") == true);

    loguru::shutdown();

    // 9-10) 文件 sink 确实落盘（shutdown 后读回校验）
    FILE* f = std::fopen("consumer_test.log", "r");
    CHECK(f != nullptr);
    if (f) {
        char buf[8192];
        size_t n = std::fread(buf, 1, sizeof(buf) - 1, f);
        buf[n] = '\0';
        CHECK(std::strstr(buf, "hello from loguru 42") != nullptr);
        std::fclose(f);
    }

    std::printf("loguru consumer test: %d checks, %d failures\n",
                g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
