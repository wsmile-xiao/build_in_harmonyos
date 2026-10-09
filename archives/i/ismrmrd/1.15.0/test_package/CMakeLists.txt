cmake_minimum_required(VERSION 3.15)
project(test_ismrmrd C CXX)

# Find the package through the Conan-generated CMakeDeps config.
find_package(ismrmrd CONFIG REQUIRED)

# Consumer test A: public C API.
add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer ismrmrd::ismrmrd)

# Consumer test B (HarmonyOS-specific): public C++ XML interchange API.
add_executable(test_ohos test_ohos.cpp)
target_link_libraries(test_ohos ismrmrd::ismrmrd)
set_target_properties(test_ohos PROPERTIES CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_consumer COMMAND test_consumer)
add_test(NAME test_ohos COMMAND test_ohos)
