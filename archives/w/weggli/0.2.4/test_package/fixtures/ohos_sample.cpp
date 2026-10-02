/* HarmonyOS PC C++ sample fixture for the weggli consumer test.
 *
 * 用于 C++ 模式（weggli -X）的范围 for + lambda 语义查询断言。
 */
#include <vector>

int sum_ohos_values(const std::vector<int> &values) {
    int total = 0;
    auto add = [&total](int v) { total += v; };
    for (int v : values) {
        add(v);
    }
    return total;
}
