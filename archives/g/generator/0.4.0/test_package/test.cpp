#include <tl/generator.hpp>
#include <string>
#include <vector>

tl::generator<int> firstn(int n) {
    for (int i = 0; i < n; ++i) co_yield i;
}

int main() {
    std::vector<int> values;
    for (int value : firstn(5)) values.push_back(value);
    if (values != std::vector<int>{0, 1, 2, 3, 4}) return 1;
    auto generated = firstn(3);
    auto it = generated.begin();
    if (it == generated.end() || *it != 0) return 2;
    return 0;
}
