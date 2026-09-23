cmake_minimum_required(VERSION 3.15)
project(test_resolv-wrapper C)

# Find the package via Conan-generated CMakeDeps
find_package(resolv-wrapper REQUIRED)

add_executable(test_resolv-wrapper test.c)
# On OHOS/musl the res_n* declarations are absent from <resolv.h>, but the
# library exports them; test.c declares them itself.  Growing a PIE-capable
# shared object requires export-dynamic linked symbols, so just link normally.
target_link_libraries(test_resolv-wrapper resolv-wrapper::resolv-wrapper)

enable_testing()
add_test(NAME test_resolv-wrapper COMMAND test_resolv-wrapper)
