cmake_minimum_required(VERSION 3.15)
project(test_libsavitar CXX)

# Find the package via Conan-generated CMakeDeps/CMakeToolchain
find_package(Savitar REQUIRED)

add_executable(test_libsavitar test.cpp)
target_link_libraries(test_libsavitar Savitar::Savitar)

# HarmonyOS 专项测试：独立可执行目标，调用 libsavitar 真实 API
add_executable(harmonyos_specific_test harmonyos_specific_test.cpp)
target_link_libraries(harmonyos_specific_test Savitar::Savitar)

enable_testing()
add_test(NAME test_libsavitar COMMAND test_libsavitar)
add_test(NAME harmonyos_specific_test COMMAND harmonyos_specific_test)