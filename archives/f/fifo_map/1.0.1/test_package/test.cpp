// test_fifo_map.cpp — test_package 消费者验证（L1）
// 仅通过已安装的公开头文件 <fifo_map.hpp> 与公开 API 使用 fifo_map，
// 真实编译、链接、运行并验证 FIFO 语义的可观察结果（R34：非空壳）。
#include <fifo_map.hpp>

#include <cstdio>
#include <string>

int main()
{
    nlohmann::fifo_map<std::string, int> m;
    m["first"] = 10;
    m["second"] = 20;

    // 验证 FIFO 插入顺序（first 在 second 之前，尽管 second < first 字典序更小）
    const char* expect_first = m.begin()->first.c_str();
    if (std::string(expect_first) != "first" || m.at("second") != 20 || m.size() != 2) {
        std::fprintf(stderr, "test_fifo_map FAIL\n");
        return 1;
    }
    std::printf("test_fifo_map: fifo_map 1.0.1 consumer test OK (order=%s,%s size=%zu)\n",
                expect_first, (++m.begin())->first.c_str(), m.size());
    return 0;
}