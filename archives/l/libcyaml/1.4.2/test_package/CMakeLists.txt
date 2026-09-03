cmake_minimum_required(VERSION 3.15)
project(test_libcyaml C)

# Find the package via Conan-generated CMakeDeps
find_package(libcyaml REQUIRED)

add_executable(test_libcyaml test.c)
target_link_libraries(test_libcyaml libcyaml::libcyaml)

enable_testing()
add_test(NAME test_libcyaml COMMAND test_libcyaml)

# HarmonyOS-specific test: UTF-8 Chinese YAML load->save->reload round trip
add_executable(test_libcyaml_ohos ohos_test.c)
target_link_libraries(test_libcyaml_ohos libcyaml::libcyaml)
add_test(NAME test_libcyaml_ohos COMMAND test_libcyaml_ohos)