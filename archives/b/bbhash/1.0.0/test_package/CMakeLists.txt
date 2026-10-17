cmake_minimum_required(VERSION 3.15)
project(test_bbhash CXX)

# Find the package via Conan-generated CMakeDeps
find_package(bbhash REQUIRED)

add_executable(test_bbhash test.cpp)
target_link_libraries(test_bbhash bbhash::bbhash)
target_compile_features(test_bbhash PRIVATE cxx_std_11)

# HarmonyOS 专项测试：多线程构造 + save/load 往返，严格编译 (-Werror)
add_executable(test_bbhash_ohos ohos_test.cpp)
target_link_libraries(test_bbhash_ohos bbhash::bbhash)
target_compile_features(test_bbhash_ohos PRIVATE cxx_std_11)
target_compile_options(test_bbhash_ohos PRIVATE -Wall -Wextra -Werror)

enable_testing()
add_test(NAME test_bbhash COMMAND test_bbhash)
add_test(NAME test_bbhash_ohos COMMAND test_bbhash_ohos)