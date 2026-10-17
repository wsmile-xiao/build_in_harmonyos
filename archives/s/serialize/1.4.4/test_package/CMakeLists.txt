cmake_minimum_required(VERSION 3.15)
project(test_serialize CXX)

# Find the package via Conan-generated CMakeDeps
find_package(serialize REQUIRED)

# Consumer test (R34: actually calls the public API of the tested package)
add_executable(test_serialize test_serialize.cpp)
target_link_libraries(test_serialize PRIVATE serialize::serialize)
set_target_properties(test_serialize PROPERTIES CXX_STANDARD 11)

# HarmonyOS platform-specific test (OHOS aarch64 toolchain, runs as its own case)
add_executable(test_serialize_ohos ohos_serialize_test.cpp)
target_link_libraries(test_serialize_ohos PRIVATE serialize::serialize)
set_target_properties(test_serialize_ohos PROPERTIES CXX_STANDARD 11)

enable_testing()
add_test(NAME test_serialize COMMAND test_serialize)
add_test(NAME test_serialize_ohos COMMAND test_serialize_ohos)
