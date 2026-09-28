cmake_minimum_required(VERSION 3.15)
project(test_clove_unit C)

# 消费者视角：从 conan 包（include/clove-unit.h）而不是源码树取头文件
find_package(clove-unit REQUIRED)

# 1) 消费者冒烟（R34：实质调用被测包 API）——自带 3 用例 / 8 断言的 clove 测试程序
add_executable(test_clove_unit test.c)
target_link_libraries(test_clove_unit PRIVATE clove-unit::clove-unit)

# 2) 鸿蒙专项（OHOS aarch64 端到端 16 项断言）——驱动上面的可执行文件
add_executable(ohos_special_test ohos_special_test.c)

enable_testing()
add_test(NAME test_clove_unit COMMAND test_clove_unit -x)
add_test(NAME ohos_special_test COMMAND ohos_special_test $<TARGET_FILE:test_clove_unit>)
