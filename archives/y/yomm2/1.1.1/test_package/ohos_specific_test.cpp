// yomm2 1.1.1 — HarmonyOS 专项适配测试
// 验证 open-multi-methods 在 OHOS aarch64 工具链上的多继承虚基类分派与
// next() 组合（覆盖 pss1/namespaces 未断言的场景，并显式断言结果）。
#include <iostream>
#include <string>

#include <yorel/yomm2/cute.hpp>

using yorel::yomm2::virtual_;

struct A { virtual ~A() {} };
struct B : A { };
struct C : A { };
struct D : B, C {};

register_class(A);
register_class(B, A);
register_class(C, A);
register_class(D, B, C);

declare_method(std::string, which, (virtual_<A&>));

define_method(std::string, which, (A&)) {
    return "A";
}

define_method(std::string, which, (C&)) {
    return "C";
}

// next() 链式组合：B 的实现委托到基类 A 的默认实现。
declare_method(std::string, greet, (virtual_<A&>));

define_method(std::string, greet, (A&)) {
    return "hi(A)";
}

define_method(std::string, greet, (B& b)) {
    return "hi(B) then " + next(b);
}

int main() {
    yorel::yomm2::update_methods();

    D d;
    B& db = static_cast<B&>(d);
    C& dc = static_cast<C&>(d);

    // yomm2 按动态类型（D）匹配最具体的 override：D 同时是 B 与 C 的派生类，
    // 因此 D 对象无论以 B& 还是 C& 传入，which() 都解析到 C 的 override。
    const std::string wb = which(db);
    const std::string wc = which(dc);
    const std::string g = greet(db);  // 应组合 next()

    std::cout << "which(D as B): " << wb << "\n";
    std::cout << "which(D as C): " << wc << "\n";
    std::cout << "greet(B): " << g << "\n";

    int failures = 0;
    if (wb != "C") { std::cerr << "FAIL: which(D as B)\n"; ++failures; }
    if (wc != "C") { std::cerr << "FAIL: which(D as C)\n"; ++failures; }
    if (g != "hi(B) then hi(A)") { std::cerr << "FAIL: greet next()\n"; ++failures; }

    if (failures) {
        std::cerr << "HarmonyOS-specific test FAILED (" << failures << ")\n";
        return 1;
    }
    std::cout << "HarmonyOS-specific test PASSED\n";
    return 0;
}