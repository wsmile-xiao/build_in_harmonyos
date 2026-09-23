// test_container.cpp — boost1.84-container 容器库操作测试
// 实质调用 boost::container::vector/deque/flat_map/静态容器 API（R34）
#include <boost/container/vector.hpp>
#include <boost/container/deque.hpp>
#include <boost/container/flat_map.hpp>
#include <boost/container/small_vector.hpp>
#include <boost/container/stable_vector.hpp>
#include <boost/container/static_vector.hpp>
#include <boost/container/string.hpp>
#include <iostream>

namespace bc = boost::container;

int main() {
    // --- vector: push/emplace/iterate ---
    bc::vector<int> v;
    for (int i = 1; i <= 10; ++i) v.push_back(i * i);
    if (v.size() != 10 || v.back() != 100 || v.front() != 1) {
        std::cerr << "vector: size/front/back mismatch" << std::endl;
        return 1;
    }
    int sum = 0;
    for (int x : v) sum += x;
    if (sum != 385) {
        std::cerr << "vector: sum mismatch (" << sum << ")" << std::endl;
        return 1;
    }
    std::cout << "vector: 10 elems, sum=" << sum << " OK" << std::endl;

    // --- deque: push_front/push_back/random access ---
    bc::deque<std::string> d;
    d.push_back("back");
    d.push_front("front");
    d.emplace_back(3, 'x');
    if (d.front() != "front" || d.back() != "xxx" || d.size() != 3) {
        std::cerr << "deque: front/back/size mismatch" << std::endl;
        return 1;
    }
    std::cout << "deque: front='" << d.front() << "' back='" << d.back() << "' OK" << std::endl;

    // --- flat_map: insert/find/ordered iteration ---
    bc::flat_map<int, const char *> fm;
    fm[3] = "three";
    fm[1] = "one";
    fm[2] = "two";
    fm.emplace(4, "four");
    if (fm.size() != 4) {
        std::cerr << "flat_map: size mismatch" << std::endl;
        return 1;
    }
    auto it = fm.find(2);
    if (it == fm.end() || std::string(it->second) != "two") {
        std::cerr << "flat_map: find(2) failed" << std::endl;
        return 1;
    }
    // flat_map 保证有序遍历
    int prev = 0;
    for (const auto &kv : fm) {
        if (kv.first <= prev) {
            std::cerr << "flat_map: iteration not ordered" << std::endl;
            return 1;
        }
        prev = kv.first;
    }
    std::cout << "flat_map: 4 ordered entries OK" << std::endl;

    // --- small_vector: 栈上小缓冲 + 堆增长 ---
    bc::small_vector<int, 4> sv;
    for (int i = 0; i < 100; ++i) sv.push_back(i);
    if (sv.size() != 100 || sv[99] != 99) {
        std::cerr << "small_vector: growth mismatch" << std::endl;
        return 1;
    }
    std::cout << "small_vector: 100 elems (inline capacity 4) OK" << std::endl;

    // --- stable_vector: 引用稳定的 vector ---
    bc::stable_vector<int> stv;
    stv.resize(5, 7);
    int *p = &stv[2];
    stv.push_back(9);
    if (*p != 7 || stv.size() != 6) {
        std::cerr << "stable_vector: pointer stability broken" << std::endl;
        return 1;
    }
    std::cout << "stable_vector: pointer stability OK" << std::endl;

    // --- static_vector: 容量固定 ---
    bc::static_vector<int, 8> svec;
    for (int i = 0; i < 8; ++i) svec.push_back(i);
    if (svec.size() != 8 || svec.capacity() != 8) {
        std::cerr << "static_vector: capacity mismatch" << std::endl;
        return 1;
    }
    std::cout << "static_vector: fixed capacity 8 OK" << std::endl;

    // --- boost::container::string ---
    bc::string bs("hello ");
    bs += "harmony";
    if (bs != "hello harmony" || bs.find("mony") == bc::string::npos) {
        std::cerr << "container string: ops mismatch" << std::endl;
        return 1;
    }
    std::cout << "container string: concat/find OK" << std::endl;

    std::cout << "boost_container: vector/deque/flat_map/small_vector/stable_vector/static_vector/string all OK" << std::endl;
    return 0;
}
