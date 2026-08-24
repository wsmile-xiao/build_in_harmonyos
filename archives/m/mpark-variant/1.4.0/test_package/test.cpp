#include <mpark/variant.hpp>
#include <cstdio>
#include <string>

// header-only 库：真实计算 = 真的存取、真的访问者派发、真的异常语义。
int main() {
    int bad = 0;

    // ① 基本存取与 index
    mpark::variant<int, std::string> v = 42;
    if (v.index() != 0 || mpark::get<int>(v) != 42) { std::printf("FAIL 存 int\n"); bad++; }
    v = std::string("hi");
    if (v.index() != 1 || mpark::get<std::string>(v) != "hi") { std::printf("FAIL 存 string\n"); bad++; }

    // ② visit 派发到正确分支（模板实例化正确性）
    struct Vis {
        int operator()(int x) const { return x * 2; }
        int operator()(const std::string& s) const { return (int)s.size(); }
    };
    mpark::variant<int, std::string> a = 21, b = std::string("abcd");
    if (mpark::visit(Vis{}, a) != 42) { std::printf("FAIL visit(int)\n"); bad++; }
    if (mpark::visit(Vis{}, b) != 4)  { std::printf("FAIL visit(string)\n"); bad++; }

    // ③ 取错类型必须抛 bad_variant_access —— 这是类型安全的核心保证
    bool threw = false;
    try { (void)mpark::get<int>(b); } catch (const mpark::bad_variant_access&) { threw = true; }
    if (!threw) { std::printf("FAIL 取错类型没抛\n"); bad++; }

    // ④ get_if 的空指针语义
    if (mpark::get_if<int>(&b) != nullptr) { std::printf("FAIL get_if 该给 null\n"); bad++; }
    if (mpark::get_if<std::string>(&b) == nullptr) { std::printf("FAIL get_if 该给非 null\n"); bad++; }

    if (bad == 0) std::printf("mpark-variant 1.4.0: 6 项断言全过\n");
    return bad ? 1 : 0;
}
