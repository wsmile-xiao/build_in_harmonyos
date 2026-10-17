// test_itlib.cpp — itlib 1.12.2 消费者验证
// 仅通过已安装的公开头文件 <itlib/...> 与公开 API 使用该三方库：
//   - itlib::small_vector（公开头文件 itlib/small_vector.hpp）
//   - itlib::flat_map / itlib::flat_set（公开头文件 itlib/flat_map.hpp, flat_set.hpp）
//   - itlib::span 别名（itlib/span.hpp）
// 验证编译、链接、调用与可观察结果（R34：非空壳，有真实断言输出）。
#include <itlib/small_vector.hpp>
#include <itlib/flat_map.hpp>
#include <itlib/flat_set.hpp>
#include <itlib/span.hpp>

#include <cstdio>
#include <string>
#include <cassert>

int main()
{
    int failures = 0;

    // small_vector：动态小容量 vector，公开 API push_back/emplace_back/at
    itlib::small_vector<int, 4> sv;
    sv.push_back(10);
    sv.push_back(20);
    sv.push_back(30);
    sv.emplace_back(40);
    if (sv.size() != 4 || sv.at(0) != 10 || sv.at(3) != 40) {
        std::printf("FAIL small_vector size/at: %zu\n", sv.size());
        ++failures;
    }

    // flat_map：vector 底层的 map，公开 API insert/at/count
    itlib::flat_map<std::string, int> fm;
    fm.insert({"alpha", 1});
    fm.insert({"beta", 2});
    if (fm.count("alpha") != 1 || fm.at("beta") != 2) {
        std::printf("FAIL flat_map insert/at\n");
        ++failures;
    }

    // flat_set：vector 底层的 set，公开 API insert/count/erase
    itlib::flat_set<int> fs;
    fs.insert(7);
    fs.insert(3);
    fs.insert(7); // 重复，set 语义去重
    if (fs.count(7) != 1 || fs.count(3) != 1 || fs.size() != 2) {
        std::printf("FAIL flat_set insert/count: %zu\n", fs.size());
        ++failures;
    }

    // span：公开 API data()/size()
    int arr[3] = {1, 2, 3};
    itlib::span<int> sp(arr, 3);
    if (sp.size() != 3 || sp.data()[1] != 2) {
        std::printf("FAIL span size/data\n");
        ++failures;
    }

    if (failures == 0) {
        std::printf("itlib consumer test PASSED: small_vector/flat_map/flat_set/span OK\n");
        return 0;
    }
    std::printf("itlib consumer test FAILED: %d failure(s)\n", failures);
    return 1;
}
