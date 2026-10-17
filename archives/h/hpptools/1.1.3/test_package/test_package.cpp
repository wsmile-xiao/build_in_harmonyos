#include <iostream>
#include <list>
#include <string>
#include <vector>

#include "alg.hpp"
#include "logsum.hpp"

// test_package 消费者用例：仅通过 hpptools 安装的公开头文件使用其公开 API
// （alg::for_each_it_advance / alg::min_of / alg::os_join / p7_FLogsum），
// 验证第三方消费者能编译、链接并得到可观察结果。
int main() {
    // alg::for_each_it_advance: 单趟删除满足条件的元素
    std::list<int> l{3, 6, 10, 18};
    alg::for_each_it_advance(l, [&l](std::list<int>::iterator it) {
        if (*it % 5 == 0) l.erase(it);
    });
    if (l.size() != 3 || l.front() != 3 || l.back() != 18) {
        std::cerr << "FAIL: for_each_it_advance result size=" << l.size() << "\n";
        return 1;
    }
    std::cout << "for_each_it_advance OK: {3,6,18}\n";

    // alg::min_of: 按模 5 键取最小元素
    // {3,6,18} 的键分别为 3,1,3 → 最小键 1 → 元素 6
    auto it_min = alg::min_of(l, [](int i) { return i % 5; });
    if (it_min == l.end() || *it_min != 6) {
        std::cerr << "FAIL: min_of\n";
        return 1;
    }
    std::cout << "min_of OK: 6\n";

    // alg::os_join: 自定义分隔符输出
    std::vector<int> v{1, 2, 3};
    std::ostringstream os;
    os << "v: " << alg::os_join(v, ", ");
    if (os.str() != "v: 1, 2, 3") {
        std::cerr << "FAIL: os_join -> " << os.str() << "\n";
        return 1;
    }
    std::cout << "os_join OK: " << os.str() << "\n";

    // logsum::p7_FLogsum: 对数空间加法（可观察数值结果）
    // 注意：p7_FLogsum 是表驱动快速近似（p7_LOGSUM_SCALE=1000，log 空间量化 ~1e-3），
    // 库文档以 p7_FLogsumError(-0.4,-0.5)>0.0001 检测快速模式；容差取 1e-3 与其一致。
    float r = logsum::p7_FLogsum(.5f, .3f);  // ~= log(exp(.5)+exp(.3))
    float expected = std::log(std::exp(.5f) + std::exp(.3f));
    if (std::abs(r - expected) > 1e-3f) {
        std::cerr << "FAIL: p7_FLogsum got " << r << " expected " << expected << "\n";
        return 1;
    }
    std::cout << "p7_FLogsum OK: " << r << "\n";

    std::cout << "hpptools test_package consumer: ALL PASSED\n";
    return 0;
}
