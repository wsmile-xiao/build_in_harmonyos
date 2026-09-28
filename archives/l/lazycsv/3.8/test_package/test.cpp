// 消费者用例：模拟业务上层组件，仅通过 lazycsv 已安装/导出的公开头文件
// 与公开 API 编译、链接并运行，验证第三方使用者可正常使用该库。
#include <lazycsv.hpp>

#include <cstdio>
#include <string>

int main()
{
    // 公开 API：字符串源构造 parser（含表头行）
    lazycsv::parser<std::string, lazycsv::has_header<true>> parser{
        "name,age,city\nAlice,30,Beijing\nBob,25,Shanghai\n"
    };

    // 公开 API：header() 返回表头行视图
    auto header = parser.header();
    if (std::string(header.raw()) != "name,age,city") {
        std::fprintf(stderr, "FAIL header raw: %s\n", std::string(header.raw()).c_str());
        return 1;
    }

    // 公开 API：index_of() 按列名查索引
    if (parser.index_of("name") != 0 || parser.index_of("city") != 2) {
        std::fprintf(stderr, "FAIL index_of\n");
        return 2;
    }

    // 公开 API：逐行迭代 + cells() 取列 + raw()/trimmed() 视图
    int rows = 0;
    for (const auto row : parser) {
        const auto [name, age, city] = row.cells(0, 1, 2);
        if (rows == 0) {
            if (std::string(name.raw()) != "Alice" ||
                std::string(age.raw()) != "30" ||
                std::string(city.trimmed()) != "Beijing") {
                std::fprintf(stderr, "FAIL row0\n");
                return 3;
            }
        } else if (rows == 1) {
            if (std::string(name.trimmed()) != "Bob" ||
                std::string(age.raw()) != "25" ||
                std::string(city.trimmed()) != "Shanghai") {
                std::fprintf(stderr, "FAIL row1\n");
                return 4;
            }
        }
        ++rows;
    }
    if (rows != 2) {
        std::fprintf(stderr, "FAIL data rows=%d (expect 2)\n", rows);
        return 5;
    }

    std::printf("lazycsv consumer test PASS: %d data rows, header=%s\n",
                rows, std::string(header.raw()).c_str());
    return 0;
}
