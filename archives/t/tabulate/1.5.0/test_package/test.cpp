//!
//! harmonyos_specific_test.cpp — tabulate 1.5.0 HarmonyOS 专项测试
//!
//! 在 OHOS (aarch64) 平台真实调用 tabulate 的消费入口：
//!   - 构造 Table 并 add_row 填充表头/单元格
//!   - 应用列格式化（font_align / font_style）
//!   - 断言渲染输出包含表头文本与表格分隔线
//!   - MarkdownExporter 导出断言包含 Markdown 表格管道符
//!   - 断言平台为目标 OHOS（__OHOS__ 宏 / aarch64）
//! 不依赖 tty：输出捕获至 ostringstream。
//!

#include <iostream>
#include <sstream>
#include <string>
#include <cstdlib>

#include <tabulate/table.hpp>
#include <tabulate/markdown_exporter.hpp>

using namespace tabulate;

static int failures = 0;

static void check(bool cond, const std::string& what)
{
    if (!cond) {
        std::cerr << "FAIL: " << what << std::endl;
        ++failures;
    } else {
        std::cout << "PASS: " << what << std::endl;
    }
}

int main()
{
#if defined(__OHOS__)
    std::cout << "platform=OHOS" << std::endl;
#else
    std::cout << "platform=non-OHOS" << std::endl;
#endif
#if defined(__aarch64__)
    std::cout << "arch=aarch64" << std::endl;
#endif

    // 1) 构造表格并 add_row（表头 + 数据行）
    Table employees;
    employees.add_row(Table::Row_t{"Emp. ID", "First Name", "Last Name"});
    employees.add_row(Table::Row_t{"101", "Donald", "Patrick"});
    employees.add_row(Table::Row_t{"102", "Rachel", "Williams"});

    // 2) 列格式化 API（真实调用 font_align / font_style）
    employees.column(0).format().font_align(FontAlign::right);
    employees.column(1).format().font_style({FontStyle::bold});

    // 3) 渲染断言：输出包含表头/单元格/分隔线
    {
        std::ostringstream oss;
        oss << employees;
        const std::string s = oss.str();
        check(s.find("Emp. ID") != std::string::npos, "header 'Emp. ID' present");
        check(s.find("Donald") != std::string::npos, "cell 'Donald' present");
        check(s.find("Williams") != std::string::npos, "cell 'Williams' present");
        check(s.find("|") != std::string::npos, "table vertical separator present");
        check(s.find("---") != std::string::npos || s.find("===") != std::string::npos,
              "horizontal separator present");
    }

    // 4) MarkdownExporter 导出断言
    {
        MarkdownExporter exporter;
        auto markdown = exporter.dump(employees);
        check(markdown.find("|") != std::string::npos,
              "markdown export contains pipe separators");
        check(markdown.find("Emp. ID") != std::string::npos,
              "markdown export contains header text");
    }

    if (failures == 0) {
        std::cout << "harmonyos_specific_test OK: all checks passed" << std::endl;
        return 0;
    }
    std::cerr << "harmonyos_specific_test FAILED: " << failures << " check(s) failed"
              << std::endl;
    return 1;
}