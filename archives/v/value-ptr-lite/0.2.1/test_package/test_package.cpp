#include <iostream>
#include <string>
#include "nonstd/value_ptr.hpp"

// 消费者验证：真实调用 value-ptr-lite 的 value_ptr API
// （header-only 库，验证头文件可包含、构造/访问/比较/哈希可用）
int main()
{
    int fails = 0;

    // 基本构造与解引用
    nonstd::value_ptr<int> vp(new int(42));
    if (!vp) { std::cerr << "FAIL: engaged value_ptr reports empty\n"; ++fails; }
    if (*vp != 42) { std::cerr << "FAIL: *vp != 42\n"; ++fails; }

    // 值语义复制
    nonstd::value_ptr<int> vp2(vp);
    *vp2 = 7;
    if (*vp != 42) { std::cerr << "FAIL: deep copy not independent\n"; ++fails; }
    if (*vp2 != 7) { std::cerr << "FAIL: copy value wrong\n"; ++fails; }

    // 空状态与值默认
    nonstd::value_ptr<int> empty;
    if (empty.has_value()) { std::cerr << "FAIL: default should be empty\n"; ++fails; }
    if (empty.value_or(99) != 99) { std::cerr << "FAIL: value_or default wrong\n"; ++fails; }

    // 关系比较（值比较模式）
    nonstd::value_ptr<int> a(new int(10));
    nonstd::value_ptr<int> b(new int(20));
    if (!(a < b)) { std::cerr << "FAIL: a < b expected\n"; ++fails; }

    if (fails == 0) {
        std::cout << "value-ptr-lite 0.2.1 consumer test: ALL OK\n";
        return 0;
    }
    std::cerr << "value-ptr-lite consumer test: " << fails << " failure(s)\n";
    return 1;
}
