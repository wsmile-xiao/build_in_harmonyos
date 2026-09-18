cmake_minimum_required(VERSION 3.15)
project(test_isl C)

# Find the package via Conan-generated CMakeDeps
find_package(isl REQUIRED)

# 消费者用例：模拟编译器多面体调度业务场景，仅用公开 API
add_executable(isl_consumer consumer.c)
target_link_libraries(isl_consumer isl::isl)

# HarmonyOS 专项测试：验证 imath 多精度后端与公开 API 行为
add_executable(isl_ohos_test isl_ohos_test.c)
target_link_libraries(isl_ohos_test isl::isl)

enable_testing()
add_test(NAME isl_consumer COMMAND isl_consumer)
add_test(NAME isl_ohos_test COMMAND isl_ohos_test)