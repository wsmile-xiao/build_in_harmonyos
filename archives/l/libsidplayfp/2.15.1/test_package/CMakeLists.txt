cmake_minimum_required(VERSION 3.15)
project(test_libsidplayfp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libsidplayfp REQUIRED)

add_executable(test_libsidplayfp test.cpp)
target_link_libraries(test_libsidplayfp libsidplayfp::libsidplayfp)
target_compile_features(test_libsidplayfp PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_libsidplayfp COMMAND test_libsidplayfp)
