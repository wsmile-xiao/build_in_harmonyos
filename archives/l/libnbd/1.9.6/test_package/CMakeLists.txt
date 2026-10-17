cmake_minimum_required(VERSION 3.15)
project(test_libnbd C)

# Find the package via Conan-generated CMakeDeps
find_package(libnbd REQUIRED)

add_executable(test_libnbd test.c)
target_link_libraries(test_libnbd libnbd::libnbd)

# HarmonyOS-specific adaptation test (real public API usage, no stubs)
add_executable(ohos_spec_test ohos_spec_test.c)
target_link_libraries(ohos_spec_test libnbd::libnbd)

enable_testing()
add_test(NAME test_libnbd COMMAND test_libnbd)
add_test(NAME ohos_spec_test COMMAND ohos_spec_test)
