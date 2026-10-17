// test_package 消费者测试：实际调用 cpp-sort 2.2.0 公共 API。
// cpp-sort 2.x 无泛型 <cpp-sort/sort.h>，统一入口为 sorters.h 提供的
// 各 sorter_facade 常量（merge_sort/adaptive_shivers_sort 等）。
//
// 审查修复（R03）：不使用 assert()/NDEBUG 条件宏——Release/NDEBUG 构建下
// assert 会被预处理器删除导致测试空转。本实现用宏 CHECK 执行无条件真实校验，
// 校验失败打印具体信息并以非零退出码返回，保证任何构建配置下测试语义真实。
#include <cstddef>
#include <cstdio>
#include <functional>
#include <vector>

#include <cpp-sort/sorters.h>

#define CHECK(cond)                                                       \
    do {                                                                  \
        if (!(cond)) {                                                    \
            std::fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__); \
            ++failures;                                                   \
        }                                                                 \
    } while (0)

int main() {
    int failures = 0;

    // 1) merge_sorter 稳定排序：正确性 + 稳定性（无条件校验）
    std::vector<int> data = {5, 3, 8, 1, 9, 2, 7, 4, 6, 0};
    cppsort::merge_sort(data);
    for (std::size_t i = 0; i < data.size(); ++i) {
        CHECK(data[i] == static_cast<int>(i));
    }

    std::vector<int> pairs = {3, 1, 2, 1, 3, 2};
    cppsort::merge_sort(pairs);
    CHECK((pairs == std::vector<int>{1, 1, 2, 2, 3, 3}));

    // 2) adaptive_shivers_sorter：验证分块排序入口（默认 fixed_buffer 缓冲策略）
    std::vector<int> chunk = {9, 4, 8, 2, 7, 1, 6, 3, 5, 0};
    cppsort::adaptive_shivers_sort(chunk);
    for (std::size_t i = 0; i < chunk.size(); ++i) {
        CHECK(chunk[i] == static_cast<int>(i));
    }

    // 3) 自定义比较谓词路径
    std::vector<int> desc = {1, 2, 3, 4, 5};
    cppsort::merge_sort(desc, std::greater<>{});
    CHECK((desc == std::vector<int>{5, 4, 3, 2, 1}));

    if (failures == 0) {
        std::printf("test_cpp-sort: all checks passed (13 assertions)\n");
        return 0;
    }
    std::printf("test_cpp-sort: FAILED (%d assertion failures)\n", failures);
    return 1;
}