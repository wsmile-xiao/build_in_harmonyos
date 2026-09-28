cmake_minimum_required(VERSION 3.15)
project(test_libalgebra C)

# Find the package via Conan-generated CMakeDeps
find_package(libalgebra REQUIRED)

add_executable(test_libalgebra test.c)
target_link_libraries(test_libalgebra libalgebra::libalgebra)

# HarmonyOS 专项测试（OHOS aarch64 工具链真实运行，独立于消费者测试）
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos libalgebra::libalgebra)

enable_testing()
add_test(NAME test_libalgebra COMMAND test_libalgebra)
add_test(NAME test_ohos COMMAND test_ohos)
