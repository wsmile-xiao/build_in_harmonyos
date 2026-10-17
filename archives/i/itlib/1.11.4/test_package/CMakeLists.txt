cmake_minimum_required(VERSION 3.16)
project(test_itlib CXX)

# 通过 Conan CMakeDeps 找到被测包（配方 cmake_file_name=itlib / cmake_target_name=itlib::itlib）
find_package(itlib REQUIRED)

add_executable(test_itlib test.cpp)
target_link_libraries(test_itlib PRIVATE itlib::itlib)

# 消费者按 C++17 编译：itlib/strutil.hpp 依赖 std::string_view（上游 strutil 测试即标 17）；
# 库本体的最低要求是 C++11（上游 t-*-11 用例族）。
set_target_properties(test_itlib PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_itlib COMMAND test_itlib)
