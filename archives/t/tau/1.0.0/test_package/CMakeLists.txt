cmake_minimum_required(VERSION 3.15)
project(test_tau C)

# 通过 Conan CMakeDeps 查找 tau 包（公开头文件接口）
find_package(tau REQUIRED)

add_executable(test_tau test.c)
target_link_libraries(test_tau tau::tau)

# 鸿蒙专项测试：验证 Muon 在 OHOS 工具链/运行时下的编译链接与断言行为
add_executable(test_tau_ohos test_ohos.c)
target_link_libraries(test_tau_ohos tau::tau)

enable_testing()
add_test(NAME test_tau COMMAND test_tau)
add_test(NAME test_tau_ohos COMMAND test_tau_ohos)
