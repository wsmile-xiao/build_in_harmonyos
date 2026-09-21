cmake_minimum_required(VERSION 3.15)
project(test_te CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(te REQUIRED)

add_executable(test_te test.cpp)
target_link_libraries(test_te te::te)

# OHOS 专项测试：验证类型擦除存储策略在 OHOS libcxx 下的行为
add_executable(ohos_special_test ohos_special_test.cpp)
target_link_libraries(ohos_special_test te::te)

enable_testing()
add_test(NAME test_te COMMAND test_te)
add_test(NAME ohos_special_test COMMAND ohos_special_test)