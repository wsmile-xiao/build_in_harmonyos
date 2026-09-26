cmake_minimum_required(VERSION 3.15)
project(test_lurlparser CXX)

# Find the package via Conan-generated CMakeDeps
find_package(lurlparser REQUIRED)

add_executable(test_lurlparser test.cpp)
target_link_libraries(test_lurlparser lurlparser::lurlparser)
target_compile_features(test_lurlparser PRIVATE cxx_std_11)

# HarmonyOS 专项测试：严格编译 (-Werror) + OHOS 平台 URL 解析行为
add_executable(test_lurlparser_ohos ohos_test.cpp)
target_link_libraries(test_lurlparser_ohos lurlparser::lurlparser)
target_compile_features(test_lurlparser_ohos PRIVATE cxx_std_11)
target_compile_options(test_lurlparser_ohos PRIVATE -Wall -Wextra -Werror)

enable_testing()
add_test(NAME test_lurlparser COMMAND test_lurlparser)
add_test(NAME test_lurlparser_ohos COMMAND test_lurlparser_ohos)
