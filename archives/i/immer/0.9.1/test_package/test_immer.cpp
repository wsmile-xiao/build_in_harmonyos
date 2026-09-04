// test_immer.cpp — L1 smoke test for immer 0.9.1 header-only library
// 验证 immer/vector.hpp 头文件可正常包含，immer::vector push_back/update/get 核心 API 可用
#include <immer/vector.hpp>
#include <iostream>
#include <string>

int main() {
    // 测试 1: push_back 构建持久化向量
    auto v1 = immer::vector<int>{};
    v1 = v1.push_back(10);
    v1 = v1.push_back(20);
    v1 = v1.push_back(30);
    if (v1.size() != 3) {
        std::cerr << "FAIL: vector size should be 3, got " << v1.size() << std::endl;
        return 1;
    }

    // 测试 2: 随机访问（get/operator[]）
    if (v1[0] != 10 || v1[1] != 20 || v1[2] != 30) {
        std::cerr << "FAIL: vector element access mismatch" << std::endl;
        return 1;
    }

    // 测试 3: update 持久化更新（旧版本不变，新版本更新）
    auto v2 = v1.set(1, 99);
    if (v2[1] != 99 || v1[1] != 20) {
        std::cerr << "FAIL: persistent update should leave old vector unchanged" << std::endl;
        return 1;
    }

    // 测试 4: 结构共享 + 遍历
    int sum = 0;
    for (auto x : v2) {
        sum += x;
    }
    if (sum != (10 + 99 + 30)) {
        std::cerr << "FAIL: iteration sum should be 139, got " << sum << std::endl;
        return 1;
    }

    std::cout << "PASS: immer header-only 库链接和核心 API 验证通过 (size=3, update-ok, sum=139)" << std::endl;
    return 0;
}
