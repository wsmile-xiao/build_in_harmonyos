// 消费者测试（鸿蒙特有测试行，不进上游分母）。
// 只通过**已安装包头** <icurve/copypp.hh> 与导入目标 icurve::copypp 使用上游 API：
// 不 include 上游源码树、不依赖 assert/NDEBUG——全部为显式计数检查，任一失败进程非零退出。
#include <icurve/copypp.hh>

#include <iostream>
#include <string>
#include <vector>

static int g_run = 0;
static int g_failed = 0;

static void check(bool cond, const char* what) {
    ++g_run;
    if (!cond) {
        ++g_failed;
        std::cout << "FAIL: " << what << "\n";
    }
}

// ── 非侵入式字段映射（README / 上游 test 同形）────────────────────────
class A {
public:
    int id = 0;
    std::string name;
    bool sex = false;

    A() = default;
    A(int id, std::string name, bool sex) : id(id), name(std::move(name)), sex(sex) {}
};

class B {
public:
    int id = 0;
    std::string name;
    bool sex = false;

    B() = default;
    B(int id, std::string name, bool sex) : id(id), name(std::move(name)), sex(sex) {}
};

COPYPP_FIELDS_NON_INTRUSIVE(B, A, id, name, sex)

// ── 侵入式（私有成员）字段映射 ─────────────────────────────────────────
class AA {
private:
    int id = 0;
    std::string name;
    bool sex = false;

public:
    AA() = default;
    AA(int id, std::string name, bool sex) : id(id), name(std::move(name)), sex(sex) {}

    void setId(decltype(id) v) { this->id = v; }
    void setName(decltype(name) v) { this->name = v; }
    void setSex(decltype(sex) v) { this->sex = v; }
    auto getId() const { return this->id; }
    auto getName() const { return this->name; }
    auto getSex() const { return this->sex; }

public:
    COPYPP_FIELDS_INTRUSIVE(AA, id, name, sex)
};

class BB {
private:
    int id = 0;
    std::string name;
    bool sex = false;

public:
    BB() = default;
    BB(int id, std::string name, bool sex) : id(id), name(std::move(name)), sex(sex) {}

    void setId(decltype(id) v) { this->id = v; }
    void setName(decltype(name) v) { this->name = v; }
    void setSex(decltype(sex) v) { this->sex = v; }
    auto getId() const { return this->id; }
    auto getName() const { return this->name; }
    auto getSex() const { return this->sex; }

public:
    COPYPP_FIELDS_INTRUSIVE(BB, id, name, sex)
};

int main() {
    // 1) 交付头自报版本 = 0.3.0（证明用的是打包后的头）
    check(COPYPP_VERSION == 000300, "COPYPP_VERSION == 000300 (0.3.0)");

    // 2) 非侵入式结构体字段拷贝
    A a(1, "curve", true);
    B b;
    icurve::copy(b, a);
    check(b.id == 1, "NON_INTRUSIVE: id copied");
    check(b.name == "curve", "NON_INTRUSIVE: name copied");
    check(b.sex == true, "NON_INTRUSIVE: sex copied");

    // 3) 侵入式私有成员字段拷贝
    AA aa(10, "i-curve", false);
    BB bb;
    icurve::copy(bb, aa);
    check(bb.getId() == 10, "INTRUSIVE: private id copied");
    check(bb.getName() == "i-curve", "INTRUSIVE: private name copied");
    check(bb.getSex() == false, "INTRUSIVE: private sex copied");

    // 4) C 数组拷贝（逐元素走字段映射）
    A src3[3] = {A(1, "a", true), A(2, "b", false), A(3, "c", true)};
    B dst3[3];
    icurve::copy(dst3, src3);
    check(dst3[0].id == 1, "ARRAY: dst[0].id == 1");
    check(dst3[1].id == 2, "ARRAY: dst[1].id == 2");
    check(dst3[2].id == 3, "ARRAY: dst[2].id == 3");
    check(dst3[2].name == "c", "ARRAY: dst[2].name == \"c\"");

    // 5) std::vector 容器拷贝（PushBack 重载）
    std::vector<A> vsrc = {A(7, "seven", true), A(8, "eight", false)};
    std::vector<B> vdst;
    icurve::copy(vdst, vsrc);
    check(vdst.size() == 2, "VECTOR: size == 2");
    check(vdst[0].id == 7, "VECTOR: vdst[0].id == 7");
    check(vdst[1].name == "eight", "VECTOR: vdst[1].name == \"eight\"");
    check(vdst[0].sex == true, "VECTOR: vdst[0].sex == true");

    // 6) 通用可转换拷贝（std::string → std::string）
    std::string s1 = "hello copypp";
    std::string s2;
    icurve::copy(s2, s1);
    check(s2 == "hello copypp", "STRING: copy equality");

    // 7) 数组截断语义 min(L1, L2)：目标 2 槽、源 3 槽
    B dst2[2];
    icurve::copy(dst2, src3);
    check(dst2[1].id == 2, "ARRAY_TRUNC: min(L1,L2) 取前 2 个元素");

    std::cout << "copypp consumer checks: " << g_run << " run, " << g_failed
              << " failed" << std::endl;
    return g_failed == 0 ? 0 : 1;
}
