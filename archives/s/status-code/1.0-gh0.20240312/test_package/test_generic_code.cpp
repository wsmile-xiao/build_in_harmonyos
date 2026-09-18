// Consumer test — status-code 1.0-gh0.20240312
// 以库使用者身份使用 system_error2 的 generic_code/errc 公开 API，
// 经 CMakeDeps + find_package 链接打包头，以断言结果决定退出码。
#include "status-code/generic_code.hpp"

int main()
{
    SYSTEM_ERROR2_NAMESPACE::generic_code bad = SYSTEM_ERROR2_NAMESPACE::errc::invalid_argument;
    if (!bad.failure()) return 2;   // 断言 1: 失败码可判 failure()

    SYSTEM_ERROR2_NAMESPACE::generic_code ok = SYSTEM_ERROR2_NAMESPACE::errc::success;
    if (!ok.success()) return 3;    // 断言 2: 成功码可判 success()

    return 0;
}
