// test_ohos_xeus.cpp — HarmonyOS 专项测试 for xeus 6.0.5.
//
// OHOS 适配要点验证：消费者进程实现 xinterpreter 完整内核接口，依次调用
// kernel_info_request / execute_request / is_complete_request /
// shutdown_request 公开 API，并验证 xbase64 编解码、xhash 摘要与 xmessage
// 协议头构造在 OHOS clang + libc++ 环境下可用。这是本适配的核心平台
// 差异点：xeus 依赖 nlohmann_json 的 CMake config 包（OHOS 上为
// header-only，无 config 文件，需在 generate() 中动态生成），消费者
// 侧 find_package(xeus) 链路需实证可用。
//
// 验证风格：非断言式检查，每个检查点显式 if + fprintf(stderr)
// + return 1，失败即非零退出；全部通过则打印 OHOS PASS 行。
#include <cstdio>
#include <iostream>
#include <memory>
#include <string>

#include <nlohmann/json.hpp>

#include <xeus/xinterpreter.hpp>
#include <xeus/xmessage.hpp>
#include <xeus/xbase64.hpp>
#include <xeus/xhash.hpp>
#include <xeus/xsystem.hpp>
#include <xeus/xeus.hpp>

using json = nlohmann::json;

class ohos_test_kernel : public xeus::xinterpreter
{
public:
    ohos_test_kernel() = default;
    virtual ~ohos_test_kernel() = default;

    int execution_count = 0;

private:
    void configure_impl() override {}

    void execute_request_impl(send_reply_callback cb,
                              int execution_counter,
                              const std::string& code,
                              xeus::execute_request_config config,
                              json user_expressions) override
    {
        ++execution_count;

        json result;
        result["status"] = "ok";
        result["execution_count"] = execution_counter;

        json payload;
        payload["platform"] = "OHOS";
        payload["code_size"] = code.size();
        result["payload"] = payload;

        cb(result);
    }

    json complete_request_impl(const std::string& code, int cursor_pos) override
    {
        json result;
        result["matches"] = json::array();
        result["cursor_start"] = cursor_pos;
        result["cursor_end"] = cursor_pos;
        result["status"] = "ok";
        return result;
    }

    json inspect_request_impl(const std::string& code, int cursor_pos, int detail_level) override
    {
        json result;
        result["found"] = false;
        result["status"] = "ok";
        return result;
    }

    json is_complete_request_impl(const std::string& code) override
    {
        json result;
        result["status"] = code.empty() ? "complete" : "unknown";
        return result;
    }

    json kernel_info_request_impl() override
    {
        json result;
        result["implementation"] = "ohos_xeus_consumer";
        result["implementation_version"] = "6.0.5";
        result["language_info"]["name"] = "cpp";
        result["language_info"]["version"] = "17";
        result["language_info"]["mimetype"] = "text/x-c++src";
        result["language_info"]["file_extension"] = ".cpp";
        result["status"] = "ok";
        return result;
    }

    json shutdown_request_impl(bool restart) override
    {
        json result;
        result["status"] = "ok";
        return result;
    }

    json interrupt_request_impl() override
    {
        json result;
        result["status"] = "ok";
        return result;
    }
};

int main()
{
    std::cout << "=== OHOS xeus 6.0.5 consumer test ===" << std::endl;

    // 1. Verify version macros
    std::cout << "XEUS version: " << XEUS_VERSION_MAJOR << "."
              << XEUS_VERSION_MINOR << "." << XEUS_VERSION_PATCH << std::endl;
    if (XEUS_VERSION_MAJOR != 6 || XEUS_VERSION_MINOR != 0 || XEUS_VERSION_PATCH != 5)
    {
        std::fprintf(stderr, "unexpected xeus version %d.%d.%d\n",
                     XEUS_VERSION_MAJOR, XEUS_VERSION_MINOR, XEUS_VERSION_PATCH);
        return 1;
    }

    // 2. Create kernel instance (OHOS platform test)
    // make_unique throws on allocation failure rather than returning null,
    // so no null check here.
    auto kernel = std::make_unique<ohos_test_kernel>();

    // 3. Test kernel_info_request
    json info = kernel->kernel_info_request();
    if (info["implementation"] != "ohos_xeus_consumer" || info["status"] != "ok")
    {
        std::fprintf(stderr, "kernel_info_request returned unexpected payload: %s\n",
                     info.dump().c_str());
        return 1;
    }
    std::cout << "kernel_info_request: OK" << std::endl;

    // 4. Test execute_request (with callback)
    json kernel_exec_result;
    kernel->execute_request(
        xeus::xrequest_context(),
        [&kernel_exec_result](json result) {
            kernel_exec_result = result;
        },
        "int x = 1 + 2;",
        xeus::execute_request_config(), json::object()
    );
    if (kernel->execution_count != 1)
    {
        std::fprintf(stderr, "execution_count=%d, expected 1\n", kernel->execution_count);
        return 1;
    }
    if (kernel_exec_result["status"] != "ok")
    {
        std::fprintf(stderr, "execute_request reply status not ok: %s\n",
                     kernel_exec_result.dump().c_str());
        return 1;
    }
    std::cout << "execute_request: OK" << std::endl;

    // 5. Test is_complete_request (stub semantics: empty code -> complete,
    //    non-empty code -> unknown)
    json complete_empty = kernel->is_complete_request("");
    if (complete_empty["status"] != "complete")
    {
        std::fprintf(stderr, "is_complete_request('') status not complete: %s\n",
                     complete_empty.dump().c_str());
        return 1;
    }
    json complete_code = kernel->is_complete_request("int x;");
    if (complete_code["status"] != "unknown")
    {
        std::fprintf(stderr, "is_complete_request('int x;') status not unknown: %s\n",
                     complete_code.dump().c_str());
        return 1;
    }
    std::cout << "is_complete_request: OK" << std::endl;

    // 6. Test base64 encoding
    std::string test_data = "Hello OHOS Kernel!";
    std::string encoded = xeus::base64encode(test_data);
    if (encoded.empty())
    {
        std::fprintf(stderr, "base64encode returned empty string\n");
        return 1;
    }
    std::string decoded = xeus::base64decode(encoded);
    if (decoded != test_data)
    {
        std::fprintf(stderr, "base64 roundtrip mismatch: '%s' != '%s'\n",
                     decoded.c_str(), test_data.c_str());
        return 1;
    }
    std::cout << "base64 encode/decode: OK" << std::endl;

    // 7. Test xhash (hash_bytes)
    std::string hash_input = "test_hash_input";
    std::size_t hash = xeus::hash_bytes(hash_input.data(), hash_input.size(), 42);
    if (hash == 0)
    {
        std::fprintf(stderr, "hash_bytes returned 0\n");
        return 1;
    }
    std::cout << "xhash compute: OK (hash=" << hash << ")" << std::endl;

    // 8. Test xmessage utilities (kernel protocol)
    json msg = xeus::make_header("execute_request", "test_user", "session_123");
    if (!msg.contains("msg_id") || msg["msg_type"] != "execute_request")
    {
        std::fprintf(stderr, "make_header returned unexpected payload: %s\n",
                     msg.dump().c_str());
        return 1;
    }
    std::cout << "make_header: OK" << std::endl;

    // 9. Test shutdown
    json shutdown_result = kernel->shutdown_request(false);
    if (shutdown_result["status"] != "ok")
    {
        std::fprintf(stderr, "shutdown_request status not ok: %s\n",
                     shutdown_result.dump().c_str());
        return 1;
    }
    std::cout << "shutdown: OK" << std::endl;

    std::printf("OHOS PASS: xeus 6.0.5 consumer exercised kernel_info/execute/"
                "is_complete/shutdown + base64/hash/make_header, "
                "version=%d.%d.%d, execution_count=%d\n",
                XEUS_VERSION_MAJOR, XEUS_VERSION_MINOR, XEUS_VERSION_PATCH,
                kernel->execution_count);
    return 0;
}
