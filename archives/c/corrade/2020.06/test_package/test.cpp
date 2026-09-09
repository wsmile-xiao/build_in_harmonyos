// HarmonyOS 专项测试 — corrade 2020.06 消费者验证
// 验证: ① OHOS 平台宏已生效; ② 基础 API (String/Containers) 在 OHOS 上真实可用;
//       ③ Debug 输出正常; ④ 链接了真实库符号 (非空壳)。
#include <iostream>
#include <string>
#include <vector>

#include "Corrade/configure.h"
#include "Corrade/Utility/Debug.h"
#include "Corrade/Utility/DebugStl.h"
#include "Corrade/Utility/String.h"
#include "Corrade/Containers/Array.h"
#include "Corrade/Containers/Optional.h"

int main() {
    int failures = 0;

    /* 1) OHOS 平台宏 */
#ifdef CORRADE_TARGET_OHOS
    Corrade::Utility::Debug{} << "PASS: CORRADE_TARGET_OHOS is defined";
#else
    std::cerr << "FAIL: CORRADE_TARGET_OHOS not defined" << std::endl;
    ++failures;
#endif

#ifdef CORRADE_TARGET_UNIX
    Corrade::Utility::Debug{} << "PASS: CORRADE_TARGET_UNIX is defined";
#else
    std::cerr << "FAIL: CORRADE_TARGET_UNIX not defined" << std::endl;
    ++failures;
#endif

    /* 2) Utility::String 真实 API (join/split) */
    {
        const std::vector<std::string> parts{"a", "b", "c"};
        const std::string joined = Corrade::Utility::String::join(parts, ',');
        if (joined == "a,b,c") {
            Corrade::Utility::Debug{} << "PASS: String::join ->" << joined;
        } else {
            std::cerr << "FAIL: String::join got '" << joined << "'" << std::endl;
            ++failures;
        }
        const auto split = Corrade::Utility::String::split(joined, ',');
        if (split.size() == 3 && split[1] == "b") {
            Corrade::Utility::Debug{} << "PASS: String::split ->" << split.size() << "parts";
        } else {
            std::cerr << "FAIL: String::split" << std::endl;
            ++failures;
        }
    }

    /* 3) Containers::Array / Optional 真实 API */
    {
        Corrade::Containers::Array<int> arr{Corrade::Containers::ValueInit, 4};
        arr[0] = 42;
        arr[3] = 7;
        const int sum = arr[0] + arr[1] + arr[2] + arr[3];
        if (sum == 49) {
            Corrade::Utility::Debug{} << "PASS: Containers::Array sum =" << sum;
        } else {
            std::cerr << "FAIL: Containers::Array sum =" << sum << std::endl;
            ++failures;
        }

        Corrade::Containers::Optional<int> opt = 5;
        if (opt && *opt == 5) {
            Corrade::Utility::Debug{} << "PASS: Containers::Optional =" << *opt;
        } else {
            std::cerr << "FAIL: Containers::Optional" << std::endl;
            ++failures;
        }
    }

    if (failures == 0) {
        Corrade::Utility::Debug{} << "corrade OHOS consumer test: ALL PASSED";
        return 0;
    }
    std::cerr << failures << " check(s) failed" << std::endl;
    return 1;
}
