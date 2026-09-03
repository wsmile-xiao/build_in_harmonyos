cmake_minimum_required(VERSION 3.15)
project(test_scope_guard_ohos CXX)

# Consumer build: find scope_guard via Conan-generated CMakeDeps
find_package(scope_guard REQUIRED)

add_executable(test_scope_guard_ohos test_scope_guard_ohos.cpp)
target_link_libraries(test_scope_guard_ohos PRIVATE scope_guard::scope_guard)
target_compile_features(test_scope_guard_ohos PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_scope_guard_ohos COMMAND test_scope_guard_ohos)