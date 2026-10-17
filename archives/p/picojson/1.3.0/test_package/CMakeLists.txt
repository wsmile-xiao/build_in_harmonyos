cmake_minimum_required(VERSION 3.15)
project(test_picojson CXX)

# Find the package via Conan-generated CMakeDeps
find_package(picojson REQUIRED)

add_executable(test_picojson test.cc)
target_link_libraries(test_picojson picojson::picojson)

# OHOS 专项测试：int64/UTF-8/错误路径/序列化（clang 15 + libc++17 平台敏感行为）
add_executable(test_ohos test_ohos.cc)
target_link_libraries(test_ohos picojson::picojson)

enable_testing()
add_test(NAME test_picojson COMMAND test_picojson)
add_test(NAME test_ohos COMMAND test_ohos)
