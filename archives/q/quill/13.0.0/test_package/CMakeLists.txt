cmake_minimum_required(VERSION 3.15)
project(test_quill CXX)

# Find the package via Conan-generated CMakeDeps
find_package(quill REQUIRED)
find_package(Threads REQUIRED)

add_executable(test_quill test.cpp)
target_link_libraries(test_quill quill::quill Threads::Threads)
target_compile_features(test_quill PRIVATE cxx_std_17)

# HarmonyOS/OHOS 专项测试：验证 TMPDIR 日志写入（/tmp 只读平台适配点）
add_executable(test_quill_ohos test_ohos.cpp)
target_link_libraries(test_quill_ohos quill::quill Threads::Threads)
target_compile_features(test_quill_ohos PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_quill COMMAND test_quill)
add_test(NAME test_quill_ohos COMMAND test_quill_ohos)