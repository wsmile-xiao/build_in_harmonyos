// test_indicators.cpp — L1 smoke test for indicators 2.3.0 header-only library
// 验证 <indicators/progress_bar.hpp> 可包含、ProgressBar 可构造，
// set_progress/is_completed 状态机与 option::Stream 重定向 API
#include <indicators/progress_bar.hpp>
#include <indicators/indeterminate_progress_bar.hpp>
#include <iostream>
#include <sstream>
#include <string>

int main() {
    using namespace indicators;

    // 测试 1: ProgressBar 构造 + option::Stream 重定向（避免污染终端）
    std::ostringstream stream;
    ProgressBar bar{
        option::BarWidth{20},
        option::Start{"["},
        option::Fill{"="},
        option::Remainder{"-"},
        option::End{"]"},
        option::PrefixText{"verify"},
        option::MaxProgress{100},
        option::Stream{stream},
    };

    // 测试 2: 推进进度后 is_completed 状态
    bar.set_progress(50);
    if (bar.is_completed()) {
        std::cerr << "FAIL: 50/100 不应 completed" << std::endl;
        return 1;
    }
    bar.set_progress(100);
    if (!bar.is_completed()) {
        std::cerr << "FAIL: 100/100 应 completed" << std::endl;
        return 1;
    }

    // 测试 3: option::Stream 生效（输出进入 stringstream 而非终端）
    if (stream.str().empty()) {
        std::cerr << "FAIL: option::Stream 未捕获 ProgressBar 输出" << std::endl;
        return 1;
    }

    // 测试 4: IndeterminateProgressBar 头文件/API 可编译（使用其 option 命名空间类型）
    IndeterminateProgressBar spinner{option::BarWidth{10}};
    spinner.tick();
    (void)spinner;

    std::cout << "PASS: indicators header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}