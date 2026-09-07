cmake_minimum_required(VERSION 3.15)
project(test_sqlitecpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(sqlitecpp REQUIRED)

add_executable(test_sqlitecpp test_sqlitecpp.cpp)
target_link_libraries(test_sqlitecpp sqlitecpp::sqlitecpp)

enable_testing()
add_test(NAME test_sqlitecpp COMMAND test_sqlitecpp)
