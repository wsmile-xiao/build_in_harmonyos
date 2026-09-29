// test_package: 真实消费者验证 —— 调用 fplus 公共 API 并逐条断言读数
//
// 断言不使用 assert()：Release 构建定义 NDEBUG 时 assert() 整体失效，
// 会把失败判成通过（假绿）。此处改用显式检查 + 计数 + 非零退出码。
// 第 10 条断言读取 **交付进包的那一份** fplus.hpp 做内容指纹校验
// （路径由 test_package/CMakeLists.txt 从 FunctionalPlus::fplus 的
//   INTERFACE_INCLUDE_DIRECTORIES 取出，指向 conan 包 include/ 而非源码树）。
#include <fplus/fplus.hpp>

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#ifndef FPLUS_FPLUS_HPP
#error "FPLUS_FPLUS_HPP must point at the packaged include/fplus/fplus.hpp"
#endif

namespace {
int checks = 0;
int fails = 0;

void check(bool cond, const char* what) {
    ++checks;
    if (cond) {
        std::printf("[consumer] PASS: %s\n", what);
    } else {
        ++fails;
        std::printf("[consumer] FAIL: %s\n", what);
    }
}
}  // namespace

int main() {
    using std::string;
    using std::vector;

    const vector<int> xs = {1, 2, 3, 4, 5, 6, 7, 8};

    check(fplus::keep_if(fplus::is_even<int>, xs) == vector<int>({2, 4, 6, 8}),
          "keep_if(is_even) == {2,4,6,8}");
    check(fplus::sum(vector<int>{1, 2, 3}) == 6, "sum({1,2,3}) == 6");
    check(fplus::join(string(","), vector<string>{"a", "b", "c"}) == "a,b,c",
          "join(\",\") == a,b,c");
    check(fplus::transform([](int v) { return v * 2; }, vector<int>{1, 2, 3}) ==
              vector<int>({2, 4, 6}),
          "transform(*2) == {2,4,6}");
    check(fplus::take(3, xs) == vector<int>({1, 2, 3}), "take(3) == {1,2,3}");
    check(fplus::drop(6, xs) == vector<int>({7, 8}), "drop(6) == {7,8}");
    check(fplus::replicate(3, 7) == vector<int>({7, 7, 7}), "replicate(3,7) == {7,7,7}");
    check(fplus::sort_by([](int a, int b) { return a > b; }, vector<int>{3, 1, 2}) ==
              vector<int>({3, 2, 1}),
          "sort_by(desc) == {3,2,1}");
    check(fplus::minimum(vector<int>{5, 2, 9}) == 2, "minimum({5,2,9}) == 2");

    // 第 10 条：交付件内容指纹（读 package() 交付进 conan 包的那一份头文件）
    std::ifstream in(FPLUS_FPLUS_HPP);
    if (!in) {
        check(false, "packaged fplus/fplus.hpp readable");
    } else {
        std::stringstream ss;
        ss << in.rdbuf();
        const std::string body = ss.str();
        const bool marker = body.find("FunctionalPlus") != std::string::npos;
        const bool sized = body.size() > 1000;
        const bool incs = body.find("#include <fplus/") != std::string::npos;
        check(marker && sized && incs,
              "packaged fplus.hpp content fingerprint (marker + size>1000 + includes)");
        std::printf("[consumer] fplus.hpp bytes=%zu\n", body.size());
    }

    std::printf("[consumer] TOTAL=%d FAIL=%d\n", checks, fails);
    return fails == 0 ? 0 : 1;
}
