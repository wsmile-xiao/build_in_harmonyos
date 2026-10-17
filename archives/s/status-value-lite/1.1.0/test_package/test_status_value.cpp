// test_status_value.cpp — 消费者测试：验证 status-value-lite 头文件库
// 通过 nonstd 命名空间对 status_value 进行构造/状态/取值/移动/解引用验证
#include <nonstd/status_value.hpp>

#include <iostream>
#include <string>

int main()
{
    using namespace nonstd;
    int failures = 0;

    // 1. 构造（状态 + 值）→ engaged
    status_value<int, std::string> sv(1, "ok");
    if (!sv) { std::cout << "FAIL: sv should be engaged\n"; ++failures; }
    if (sv.status() != 1) { std::cout << "FAIL: status\n"; ++failures; }
    if (sv.value() != "ok") { std::cout << "FAIL: value\n"; ++failures; }

    // 2. 仅状态构造 → 无值（非 engaged），status() 仍可观察
    status_value<int, int> err(42);
    if (err) { std::cout << "FAIL: err should be not engaged\n"; ++failures; }
    if (err.has_value()) { std::cout << "FAIL: err.has_value should be false\n"; ++failures; }
    if (err.status() != 42) { std::cout << "FAIL: err status\n"; ++failures; }

    // 3. 移动语义
    status_value<int, std::string> moved(std::move(sv));
    if (moved.value() != "ok") { std::cout << "FAIL: moved value\n"; ++failures; }

    // 4. 解引用访问（operator* / operator->）
    if (*moved != "ok") { std::cout << "FAIL: operator*\n"; ++failures; }
    if (moved->size() != 2) { std::cout << "FAIL: operator->\n"; ++failures; }

    // 5. has_value() 与 bool
    if (!moved.has_value()) { std::cout << "FAIL: has_value\n"; ++failures; }

    if (failures == 0)
    {
        std::cout << "status-value-lite consumer test: PASS (" << failures << " failures)\n";
        return 0;
    }
    std::cout << "status-value-lite consumer test: FAIL (" << failures << " failures)\n";
    return 1;
}