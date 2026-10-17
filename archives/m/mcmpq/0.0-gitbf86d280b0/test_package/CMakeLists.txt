cmake_minimum_required(VERSION 3.15)
project(test_mcmpq C)

# Find the package via Conan-generated CMakeDeps
find_package(mcmpq REQUIRED)

add_executable(test_mcmpq test.c)
target_link_libraries(test_mcmpq mcmpq::mcmpq)

# HarmonyOS 专项测试（适配新增，覆盖 try 语义/容量边界/FIFO 顺序）
add_executable(test_ohos_specific ohos_specific_test.c)
target_link_libraries(test_ohos_specific mcmpq::mcmpq)

enable_testing()
add_test(NAME test_mcmpq COMMAND test_mcmpq)
add_test(NAME test_ohos_specific COMMAND test_ohos_specific)
