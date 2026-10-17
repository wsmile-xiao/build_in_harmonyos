// Consumer test for sole 1.0.4 — 仅通过公开头文件 sole.hpp 使用公开 API。
// 验证第三方消费者可以编译、链接、调用 sole::uuid0/uuid1/uuid4/rebuild
// 并得到可观察的、符合 UUID 语义的结果。
#include <cassert>
#include <cstdint>
#include <set>
#include <string>
#include <iostream>

#include <sole.hpp>

int main() {
    // 1) 生成三种 UUID 并检查字符串格式（标准 8-4-4-4-12 十六进制）
    sole::uuid u0 = sole::uuid0();
    sole::uuid u1 = sole::uuid1();
    sole::uuid u4 = sole::uuid4();

    std::string s0 = u0.str();
    std::string s1 = u1.str();
    std::string s4 = u4.str();
    assert(s0.size() == 36);
    assert(s1.size() == 36);
    assert(s4.size() == 36);
    for (size_t i = 0; i < 36; ++i) {
        char c = s4[i];
        if (i == 8 || i == 13 || i == 18 || i == 23) {
            assert(c == '-');
        } else {
            bool hex = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
            assert(hex);
        }
    }
    // v4 的 version nibble 必须是 4
    assert(s4[14] == '4');
    // v1 的 version nibble 必须是 1
    assert(s1[14] == '1');

    // 2) rebuild() 往返：str/base62 重建必须与原 UUID 相等
    sole::uuid r1 = sole::rebuild(s4);
    sole::uuid r2 = sole::rebuild(u4.base62());
    assert(r1 == u4);
    assert(r2 == u4);
    assert(sole::rebuild("F81D4FAE-7DEC-11D0-A765-00A0C91E6BF6").str() ==
           "f81d4fae-7dec-11d0-a765-00a0c91e6bf6");

    // 3) 唯一性：1000 个 v4 UUID 不得重复（可观察结果）
    std::set<sole::uuid> seen;
    for (int i = 0; i < 1000; ++i) {
        seen.insert(sole::uuid4());
    }
    assert(seen.size() == 1000);

    std::cout << "sole consumer test OK: "
              << s0 << " / " << s1 << " / " << s4 << std::endl;
    return 0;
}
