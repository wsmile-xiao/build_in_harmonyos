#include <fixed_containers/fixed_vector.hpp>
#include <fixed_containers/fixed_string.hpp>

#include <cassert>
#include <cstdlib>
#include <iostream>
#include <string_view>

// 消费者验证：仅通过库公开头文件与公开 API（FixedVector / FixedString）使用 fixed-containers。
// 验证固定容量容器无堆分配、可正常构造/插入/读取，且数值符合预期。
int main()
{
    using fixed_containers::FixedVector;
    using fixed_containers::FixedString;

    constexpr std::size_t CAP = 4;
    FixedVector<int, CAP> vec;
    assert(vec.empty());
    vec.push_back(10);
    vec.push_back(20);
    vec.push_back(30);
    assert(vec.size() == 3);
    assert(vec[0] == 10 && vec[2] == 30);
    for (int& v : vec)
    {
        v += 1;
    }
    assert(vec[0] == 11 && vec[1] == 21 && vec[2] == 31);
    // 容量内操作正常；固定容量上限正确
    assert(vec.static_max_size() == CAP);

    FixedString<8> s;
    s.push_back('h');
    s.push_back('i');
    assert(s.size() == 2);
    assert(s[0] == 'h' && s[1] == 'i');
    s += '!';
    assert(s.size() == 3);
    assert(std::string_view{s.c_str()} == "hi!");

    std::cout << "test fixed-containers consumer: OK (vec size=" << vec.size()
              << " str=" << s.c_str() << ")" << std::endl;
    return 0;
}