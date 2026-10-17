// ---------------------------------------------------------------------------
// permlib 0.2.9 消费者测试（鸿蒙特有测试）
//
// 目的：证明「装进 Conan 包的那一份头文件」在**第三方消费者**手里可用 ——
//   * 只 include 公开头（permlib/permlib_api.h、permlib/symmetric_group.h、
//     permlib/version.h），消费者自己**不写** boost 的 include 路径：公开头内部的
//     #include <boost/...> 必须由 permlib 的 cpp_info.requires（boost::headers）
//     传递过来；boost 路径一旦没传过来，本文件根本编译不过；
//   * 断言分三类，每类的对照物都在本文件内独立算出（不靠被测库自证）：
//       ① 闭式公式：|S_10| = 10!、|Stab_{S_10}(4-集合)| = 4!·6!；
//       ② 自写暴力枚举：S_4 的阶用 BFS 闭包数出来，再与 BSGS 的 order() 比；
//       ③ 另一条构造路径：SymmetricGroup 的已知基/横截系大小连乘。
//   * 任一条不成立 → 进程退出码非 0；末尾打印机器可解析的
//     PERMLIB_CONSUMER_CHECKS <通过>/<总> 与 PERMLIB_CONSUMER_RESULT PASS|FAIL。
// 用法（由 test_package/conanfile.py 调用）：
//   ./permlib_consumer_test                            # 正常路径
//   env -u LD_LIBRARY_PATH ./permlib_consumer_test     # 裸环境 smoke（不靠注入的库路径）
// ---------------------------------------------------------------------------
#include <permlib/permlib_api.h>
#include <permlib/symmetric_group.h>
#include <permlib/version.h>

#include <algorithm>
#include <iostream>
#include <list>
#include <string>
#include <vector>

namespace {

/// permlib 的置换作用在点上是 p.at(v)（与上游 example/example-orbit.cpp 同一写法）
unsigned long action(const permlib::Permutation& p, unsigned long v) {
    return p.at(v);
}

int g_checks = 0;
int g_failed = 0;

void report(bool ok, const std::string& what) {
    ++g_checks;
    if (!ok) {
        ++g_failed;
    }
    std::cout << (ok ? "[ok]   " : "[FAIL] ") << what << std::endl;
}

template <class T>
void report_eq(const T& got, const T& want, const std::string& what) {
    ++g_checks;
    const bool ok = (got == want);
    if (!ok) {
        ++g_failed;
    }
    std::cout << (ok ? "[ok]   " : "[FAIL] ") << what
              << ": got=" << got << " want=" << want << std::endl;
}

unsigned long long factorial(unsigned int k) {
    unsigned long long f = 1;
    for (unsigned int i = 2; i <= k; ++i) {
        f *= i;
    }
    return f;
}

/// 独立 oracle：用 BFS 闭包把生成元张成的群**枚举**出来（只用公开的置换乘法/相等）
std::size_t bruteForceGroupOrder(const permlib::Permutation& identity,
                                 const std::vector<permlib::Permutation>& generators) {
    std::vector<permlib::Permutation> elements;
    elements.push_back(identity);
    for (std::size_t i = 0; i < elements.size(); ++i) {
        for (std::size_t g = 0; g < generators.size(); ++g) {
            const permlib::Permutation next = elements[i] * generators[g];
            bool known = false;
            for (std::size_t j = 0; j < elements.size(); ++j) {
                if (elements[j] == next) {
                    known = true;
                    break;
                }
            }
            if (!known) {
                elements.push_back(next);
            }
        }
    }
    return elements.size();
}

}  // namespace

int main() {
    using namespace permlib;

    // ── 1. 版本指纹：断言装进包的那一份头文件自报的版本 ──────────────────────
    report_eq<std::string>(std::string(PERMLIB_VERSION), std::string("0.2.9"),
                           "permlib/version.h 的 PERMLIB_VERSION");

    // ── 2. 小群交叉验证：S_4 = <(1 2 3 4), (1 2)>，24 阶 ─────────────────────
    //     被测库给 order()，本文件给 BFS 暴力枚举，二者必须一致。
    {
        const Permutation id4(4);
        std::vector<Permutation> gens4;
        gens4.push_back(Permutation(4, std::string("1 2 3 4")));
        gens4.push_back(Permutation(4, std::string("1 2")));
        std::list<Permutation::ptr> gens4list;
        for (std::size_t i = 0; i < gens4.size(); ++i) {
            gens4list.push_back(Permutation::ptr(new Permutation(gens4[i])));
        }
        boost::shared_ptr<PermutationGroup> s4 = construct(4, gens4list.begin(), gens4list.end());
        const std::size_t brute = bruteForceGroupOrder(id4, gens4);
        report_eq<std::size_t>(brute, 24UL, "本文件 BFS 暴力枚举出的 S_4 阶（独立 oracle）");
        report_eq<boost::uint64_t>(s4->order(), static_cast<boost::uint64_t>(brute),
                                   "BSGS order() 与暴力枚举一致（S_4）");
    }

    // ── 3. S_10：10-轮换 + 相邻对换 → 10! = 3628800 ─────────────────────────
    const unsigned long n = 10;
    std::list<Permutation::ptr> gens;
    gens.push_back(Permutation::ptr(new Permutation(n, std::string("1 2 3 4 5 6 7 8 9 10"))));
    gens.push_back(Permutation::ptr(new Permutation(n, std::string("1 2"))));
    boost::shared_ptr<PermutationGroup> group = construct(n, gens.begin(), gens.end());

    report_eq<unsigned long>(group->n, 10UL, "群的作用点数 n");
    const unsigned long long tenFactorial = factorial(10);
    report_eq<unsigned long long>(static_cast<unsigned long long>(group->order()), tenFactorial,
                                  "|S_10| = 10!（BSGS 横截系大小连乘）");

    // 另一条构造路径：SymmetricGroup 的基/横截系已知，横截系大小连乘应同为 10!
    {
        SymmetricGroup<Permutation> sym(n);
        unsigned long long product = 1;
        for (unsigned int i = 0; i < sym.B.size(); ++i) {
            product *= static_cast<unsigned long long>(sym.U[i].size());
        }
        report_eq<unsigned long long>(product, tenFactorial,
                                      "SymmetricGroup(10) 横截系连乘 = 10!（独立构造路径）");
    }

    // 单个置换的运算（不经过群构造）
    const Permutation rot(n, std::string("1 2 3 4 5 6 7 8 9 10"));
    report_eq<boost::uint64_t>(rot.order(), 10ULL, "10-轮换的阶");
    report((rot * (~rot)).isIdentity(), "p * p^-1 是恒等置换");
    report(!(rot * rot).isIdentity(), "p^2 不是恒等置换");
    report_eq<dom_int>(rot.at(0), 1, "轮换把点 1 映到点 2（0-based: 0 -> 1）");

    // ── 4. 集合稳定化子：Delta = {1,5,8,9}（0-based {0,4,7,8}）──────────────
    const unsigned long deltaSize = 4;
    const unsigned long delta[deltaSize] = {0, 4, 7, 8};
    boost::shared_ptr<PermutationGroup> stabilizer =
        setStabilizer(*group, delta, delta + deltaSize);
    // S_10 中 4-集合的稳定化子 ≅ S_4 × S_6 ⇒ 阶 = 4! · 6!
    const unsigned long long stabOrder = factorial(4) * factorial(6);
    report_eq<unsigned long long>(static_cast<unsigned long long>(stabilizer->order()),
                                  stabOrder, "|Stab_S10({1,5,8,9})| = 4! * 6! = 17280");

    // 稳定化子保持该集合不变 ⇒ 作用在 10 个点上有 2 条轨道（集合自身与补集）
    std::list<boost::shared_ptr<OrbitAsSet> > orbitList = orbits(*stabilizer);
    report_eq<std::size_t>(orbitList.size(), 2UL, "稳定化子的轨道条数");

    // ── 5. 集合像：找一个把 Delta 映到 Gamma 的群元素 ───────────────────────
    const unsigned long gamma[deltaSize] = {2, 6, 0, 9};  // 集合 {1,3,7,10}
    Permutation::ptr repr = setImage(*group, delta, delta + deltaSize, gamma, gamma + deltaSize);
    report(repr != 0, "setImage 在 S_10 中找到了 Delta -> Gamma 的群元素");
    if (repr) {
        // 集合像的判据是**像集合相等**（集合无序，元素间没有配对关系）：
        // 把 Delta 的像算出来，排序后与排序后的 Gamma 比。
        std::vector<unsigned long> image;
        for (unsigned long i = 0; i < deltaSize; ++i) {
            image.push_back(static_cast<unsigned long>(repr->at(delta[i])));
        }
        std::vector<unsigned long> sortedGamma(gamma, gamma + deltaSize);
        std::sort(image.begin(), image.end());
        std::sort(sortedGamma.begin(), sortedGamma.end());
        report(image == sortedGamma,
               "返回的群元素把集合 Delta 映成集合 Gamma（像集合相等）");
    }

    // ── 6. 字典序最小集合像（dset = boost::dynamic_bitset）─────────────────
    dset dGamma(n);
    for (unsigned long i = 0; i < deltaSize; ++i) {
        dGamma.set(gamma[i]);
    }
    dset least = smallestSetImage(*group, dGamma);
    unsigned long leastBits = 0;
    for (unsigned long i = 0; i < n; ++i) {
        if (least[i]) {
            ++leastBits;
        }
    }
    report_eq<unsigned long>(leastBits, deltaSize, "字典序最小集合像的基数不变");
    report(least[0] && least[1] && least[2] && least[3],
           "S_10 中 4-集合轨道的最小代表是 {1,2,3,4}（0-based {0,1,2,3}）");

    // ── 7. 轨道（OrbitSet）：S_10 传递 ⇒ 点 5 的轨道是全部 10 个点 ──────────
    OrbitAsSet orbitOfFive;
    orbitOfFive.orbit(4, gens, action);
    report_eq<std::size_t>(orbitOfFive.size(), 10UL, "S_10 中点 5 的轨道大小");
    report(orbitOfFive.contains(3), "点 5 的轨道包含点 4");

    std::cout << "PERMLIB_CONSUMER_CHECKS " << (g_checks - g_failed) << "/" << g_checks
              << std::endl;
    if (g_failed != 0) {
        std::cout << "PERMLIB_CONSUMER_RESULT FAIL" << std::endl;
        return 1;
    }
    std::cout << "PERMLIB_CONSUMER_RESULT PASS" << std::endl;
    return 0;
}
