cmake_minimum_required(VERSION 3.15)
project(test_ancient CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ancient REQUIRED)

add_executable(test_ancient test.cpp)
target_link_libraries(test_ancient ancient::ancient)

# HarmonyOS 专项测试：严格编译 (-Wall -Wextra -Werror) + 解压 + 文件 I/O 往返
add_executable(test_ancient_ohos ohos_test.cpp)
target_link_libraries(test_ancient_ohos ancient::ancient)
target_compile_options(test_ancient_ohos PRIVATE -Wall -Wextra -Werror)

enable_testing()
add_test(NAME test_ancient COMMAND test_ancient)
add_test(NAME test_ancient_ohos COMMAND test_ancient_ohos)