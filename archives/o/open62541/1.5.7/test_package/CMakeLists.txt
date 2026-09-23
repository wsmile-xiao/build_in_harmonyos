cmake_minimum_required(VERSION 3.15)
project(test_open62541 C)

# Find the package via Conan-generated CMakeDeps
find_package(open62541 REQUIRED)

add_executable(test_open62541_ohos test_open62541_ohos.c)
target_link_libraries(test_open62541_ohos PRIVATE open62541::open62541)

enable_testing()
add_test(NAME test_open62541_ohos COMMAND test_open62541_ohos)
