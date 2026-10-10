// Consumer test for xeus 6.0.5
// Verifies that a downstream project can:
//   1. Include xeus headers
//   2. Link the xeus library
//   3. Use xinterpreter API (inheritance pattern)
//
// Validation style: explicit checks — every check point
// prints a diagnostic to stderr and returns 1 on failure, so the test
// remains effective in Release builds (NDEBUG).

#include <cstdio>
#include <iostream>
#include <memory>
#include <string>

#include <nlohmann/json.hpp>

#include <xeus/xinterpreter.hpp>
#include <xeus/xmessage.hpp>
#include <xeus/xeus.hpp>

using json = nlohmann::json;

class test_interpreter : public xeus::xinterpreter
{
public:
    test_interpreter() = default;
    virtual ~test_interpreter() = default;

private:
    void configure_impl() override {}

    void execute_request_impl(send_reply_callback cb,
                              int execution_counter,
                              const std::string& code,
                              xeus::execute_request_config config,
                              json user_expressions) override
    {
        json result;
        result["status"] = "ok";
        result["execution_count"] = execution_counter;
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
        result["status"] = "complete";
        return result;
    }

    json kernel_info_request_impl() override
    {
        json result;
        result["implementation"] = "test_xeus_consumer";
        result["implementation_version"] = "1.0.0";
        result["language_info"]["name"] = "test";
        result["language_info"]["version"] = "1.0";
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
    std::cout << "XEUS_VERSION: " << XEUS_VERSION_MAJOR << "."
              << XEUS_VERSION_MINOR << "." << XEUS_VERSION_PATCH << std::endl;

    auto interp = std::make_unique<test_interpreter>();

    // Check 1: kernel_info_request returns the expected implementation name
    json info = interp->kernel_info_request();
    if (!info.contains("implementation") || info["implementation"] != "test_xeus_consumer")
    {
        std::fprintf(stderr, "kernel_info_request implementation mismatch: %s\n",
                     info.dump().c_str());
        return 1;
    }
    std::cout << "kernel_info_request: OK" << std::endl;

    // Check 2: execute_request invokes the reply callback with status "ok"
    json exec_result;
    bool callback_called = false;
    interp->execute_request(
        xeus::xrequest_context(),
        [&exec_result, &callback_called](json result) {
            exec_result = result;
            callback_called = true;
        },
        "print('hello')",
        xeus::execute_request_config(), json::object()
    );
    if (!callback_called)
    {
        std::fprintf(stderr, "execute_request reply callback was not invoked\n");
        return 1;
    }
    if (!exec_result.contains("status") || exec_result["status"] != "ok")
    {
        std::fprintf(stderr, "execute_request status not ok: %s\n",
                     exec_result.dump().c_str());
        return 1;
    }
    std::cout << "execute_request: OK" << std::endl;

    std::cout << "xeus 6.0.5 consumer test: PASS" << std::endl;
    return 0;
}
