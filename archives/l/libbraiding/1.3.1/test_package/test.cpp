// libbraiding test_package —— 真实计算 + 数学不变量断言
//
// 断言依据（辫群 B3 的定义关系，无需查表即可核对）：
//   ① 辫关系 σ1σ2σ1 = σ2σ1σ2  ⇒  两者的左正规形必须**逐项相等**
//   ② σ1 ≠ σ2                 ⇒  两者的左正规形必须**不相等**
//   ③ 左正规形非空
// 若库算错（或只是空壳），①②必有一条挂。

#include <stdint.h>
#include <stddef.h>
#include <braiding.h>
#include <cstdio>
#include <list>

int main() {
    std::list<sint16> w_121, w_212, w_1, w_2;
    w_121.push_back(1); w_121.push_back(2); w_121.push_back(1);
    w_212.push_back(2); w_212.push_back(1); w_212.push_back(2);
    w_1.push_back(1);
    w_2.push_back(2);

    std::list<std::list<sint16> > a = Braiding::LeftNormalForm(3, w_121);
    std::list<std::list<sint16> > b = Braiding::LeftNormalForm(3, w_212);

    std::printf("libbraiding: LNF(s1 s2 s1) 因子数 = %zu\n", a.size());
    std::printf("libbraiding: LNF(s2 s1 s2) 因子数 = %zu\n", b.size());

    if (a.empty()) {
        std::fprintf(stderr, "libbraiding: FAIL —— LeftNormalForm 返回空\n");
        return 1;
    }
    if (!(a == b)) {
        std::fprintf(stderr,
                     "libbraiding: FAIL —— 辫关系 s1s2s1 = s2s1s2 不成立"
                     "（两者左正规形不等）\n");
        return 1;
    }

    std::list<std::list<sint16> > c = Braiding::LeftNormalForm(3, w_1);
    std::list<std::list<sint16> > d = Braiding::LeftNormalForm(3, w_2);
    if (c == d) {
        std::fprintf(stderr,
                     "libbraiding: FAIL —— s1 与 s2 的左正规形相同，"
                     "说明计算退化\n");
        return 1;
    }

    std::printf("libbraiding: OK —— 辫关系与可区分性断言均通过\n");
    return 0;
}
