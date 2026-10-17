cmake_minimum_required(VERSION 3.15)
project(test_rapidhash LANGUAGES C CXX)

find_package(rapidhash REQUIRED)

# C99 消费路径：冻结 KAT + 属性断言（832 checks）
add_executable(test_rapidhash test_package.c)
target_link_libraries(test_rapidhash PRIVATE rapidhash::rapidhash)
set_target_properties(test_rapidhash PROPERTIES C_STANDARD 99)

# C++17 消费路径：同一组 KAT + std::string/std::vector 消费路径（835 checks）
add_executable(test_rapidhash_cpp test_package_cpp.cpp)
target_link_libraries(test_rapidhash_cpp PRIVATE rapidhash::rapidhash)
set_target_properties(test_rapidhash_cpp PROPERTIES CXX_STANDARD 17)

# 鸿蒙平台专项：平台宏/小端序/128 位乘法路径/非对齐安全/KAT 抽查
add_executable(ohos_platform_test ohos_platform_test.cpp)
target_link_libraries(ohos_platform_test PRIVATE rapidhash::rapidhash)
set_target_properties(ohos_platform_test PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_rapidhash COMMAND test_rapidhash)
add_test(NAME test_rapidhash_cpp COMMAND test_rapidhash_cpp)
add_test(NAME ohos_platform_test COMMAND ohos_platform_test)
