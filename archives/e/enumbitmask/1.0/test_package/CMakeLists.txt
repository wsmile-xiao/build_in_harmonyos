cmake_minimum_required(VERSION 3.15)
project(test_enumbitmask CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(enumbitmask REQUIRED)

add_executable(test_enumbitmask test.cpp)
target_link_libraries(test_enumbitmask enumbitmask::enumbitmask)

# HarmonyOS 专项测试：覆盖底层类型宽度/constexpr/复合运算（真实编译+运行）
add_executable(test_ohos_enumbitmask test_ohos.cpp)
target_link_libraries(test_ohos_enumbitmask enumbitmask::enumbitmask)

enable_testing()
add_test(NAME test_enumbitmask COMMAND test_enumbitmask)
add_test(NAME test_ohos_enumbitmask COMMAND test_ohos_enumbitmask)
