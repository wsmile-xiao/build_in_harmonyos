#include <nameof.hpp>
#include <cassert>
#include <iostream>
#include <string>

// 枚举用于验证 NAMEOF_ENUM
enum class Color { Red, Green, Blue };

// 结构体用于验证 NAMEOF_TYPE 与 NAMEOF_MEMBER
struct Point {
    int x = 0;
    int y = 0;
};

int main() {
    // Test 1: 变量名
    int my_variable = 42;
    assert(NAMEOF(my_variable) == "my_variable");
    assert(NAMEOF(my_variable).size() == std::string("my_variable").size());

    // Test 2: 类型名
    assert(NAMEOF_TYPE(int) == "int");
    assert(NAMEOF_TYPE(Color) == "Color");
    assert(NAMEOF_TYPE(Point) == "Point");

    // Test 3: 枚举名
    assert(NAMEOF(Color::Red) == "Red");
    assert(NAMEOF(Color::Green) == "Green");
    assert(NAMEOF(Color::Blue) == "Blue");

    // Test 4: 成员名
    assert(NAMEOF_MEMBER(Point::x) == "x");
    assert(NAMEOF_MEMBER(Point::y) == "y");

    // Test 5: 变量名完整路径
    Point p;
    assert(NAMEOF_FULL(p.x) == "p.x");

    std::cout << "All nameof tests passed!" << std::endl;
    return 0;
}
