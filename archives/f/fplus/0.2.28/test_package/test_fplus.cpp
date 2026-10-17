// test_package: 真实消费者验证 — 调用 fplus API 并断言结果
#include <fplus/fplus.hpp>
#include <cassert>
#include <string>
#include <vector>

int main() {
    const std::vector<int> xs = {1, 2, 3, 4, 5};
    const auto evens = fplus::keep_if(fplus::is_even<int>, xs);
    assert(evens.size() == 2);
    assert(evens[0] == 2 && evens[1] == 4);

    const auto sum = fplus::sum(xs);
    assert(sum == 15);

    const auto joined = fplus::join(std::string(","), std::vector<std::string>{"a", "b", "c"});
    assert(joined == "a,b,c");

    return 0;
}
