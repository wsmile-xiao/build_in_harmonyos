// 消费者测试（鸿蒙特有测试 A1-A6）：以安装后的头文件 + libparaglob.a 为准，
// 断言值全部来自上游 README / btest Baseline 的实测口径（见 notes.md 验证结果）。
//
// 断言计数：A1-A5 + A6a/A6b 共 7 条；任一失败即非零退出。
#include <paraglob/paraglob.h>

#include <iostream>
#include <string>
#include <vector>

namespace {

int failures = 0;

void check(bool cond, const char* name) {
    if (cond) {
        std::cout << "[ok]   " << name << "\n";
    } else {
        std::cout << "[FAIL] " << name << "\n";
        ++failures;
    }
}

}  // namespace

int main() {
    // A1 —— README 示例：{*og, do*, ca*, plant} 对 "dog" 命中 2 条
    {
        std::vector<std::string> pats{"*og", "do*", "ca*", "plant"};
        paraglob::Paraglob p(pats);
        check(p.get("dog").size() == 2u,
              "A1 README example {*og,do*,ca*,plant} vs dog == 2");
    }

    // A2 —— 上游 testing/Baseline/driver.basic_matches/out 首行 == 4
    {
        std::vector<std::string> pats{"*", "d?g", "*og", "d?", "d[!wl]g"};
        paraglob::Paraglob p(pats);
        check(p.get("dog").size() == 4u,
              "A2 basic_matches baseline count == 4");
    }

    // A3 —— 上游 testing/Baseline/driver.empty_patterns/out 首行 == 1
    {
        std::vector<std::string> pats{"*", "cat", "dog?", "fish",
                                      "horse", "frog", "lion"};
        paraglob::Paraglob p(pats);
        check(p.get("dog").size() == 1u,
              "A3 empty_patterns baseline count == 1");
    }

    // A4 —— 无模式可命中时返回空（CLI 侧同口径 == 0）
    {
        std::vector<std::string> pats{"cat", "dog"};
        paraglob::Paraglob p(pats);
        check(p.get("zzz").empty(),
              "A4 no-match query returns empty result");
    }

    // A5 —— 序列化往返等价（上游 driver.serial 基线语义 == passed）
    {
        std::vector<std::string> pats{"*", "d?g", "*og", "d?", "d[!wl]g"};
        paraglob::Paraglob p(pats);
        paraglob::Paraglob q(p.serialize());
        check(p == q,
              "A5 serialize/deserialize round-trip keeps equality");
    }

    // A6 —— add()+compile() 增量构建路径（构造函数路径之外的第二条 API）
    {
        paraglob::Paraglob p;
        check(p.add("do*") && p.add("*og"),
              "A6a add() accepts both patterns");
        p.compile();
        check(p.get("dog").size() == 2u,
              "A6b add()+compile() vs dog == 2");
    }

    std::cout << (failures ? "paraglob consumer: FAIL\n"
                           : "paraglob consumer: PASS\n");
    return failures ? 1 : 0;
}
