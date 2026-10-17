cmake_minimum_required(VERSION 3.15)
project(test_tl_optional CXX)

# Find the package via Conan-generated CMakeDeps
find_package(tl-optional REQUIRED)

add_executable(test_tl_optional test_optional.cpp)
target_link_libraries(test_tl_optional tl::optional)

# HarmonyOS 专项测试：覆盖当前库实际调用/消费入口，真实编译并运行
add_executable(harmonyos_specific_test harmonyos_specific_test.cpp)
target_link_libraries(harmonyos_specific_test tl::optional)
target_compile_features(harmonyos_specific_test PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_tl_optional COMMAND test_tl_optional)
add_test(NAME harmonyos_specific_test COMMAND harmonyos_specific_test)