cmake_minimum_required(VERSION 3.15)
project(test_svpng C)

# Find the package via Conan-generated CMakeDeps
find_package(svpng REQUIRED)

add_executable(test_svpng test.c)
target_link_libraries(test_svpng svpng::svpng)

# HarmonyOS PC 专属专项测试（本轮新增）：
# 运行期解析 svpng() 输出 PNG 的 IHDR/IDAT/IEND 块并逐项断言结构正确
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos svpng::svpng)

enable_testing()
add_test(NAME test_svpng COMMAND test_svpng)
add_test(NAME test_ohos COMMAND test_ohos)
