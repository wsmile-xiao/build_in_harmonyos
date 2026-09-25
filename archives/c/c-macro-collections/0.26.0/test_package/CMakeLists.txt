cmake_minimum_required(VERSION 3.15)
project(test_c-macro-collections C)

# Find the package via Conan-generated CMakeDeps
find_package(c-macro-collections REQUIRED)

# 消费者冒烟用例（R34 实质调用公开 API）
add_executable(test_c-macro-collections test.c)
target_link_libraries(test_c-macro-collections c-macro-collections::c-macro-collections)

# 鸿蒙专项测试用例（OHOS 平台真实编译运行，覆盖 hashmap/stack/heap/treemap）
add_executable(ohos_special_test ohos_special_test.c)
target_link_libraries(ohos_special_test c-macro-collections::c-macro-collections)

enable_testing()
add_test(NAME test_c-macro-collections COMMAND test_c-macro-collections)
add_test(NAME ohos_special_test COMMAND ohos_special_test)