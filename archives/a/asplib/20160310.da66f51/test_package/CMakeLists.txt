cmake_minimum_required(VERSION 3.15)
project(test_asplib CXX)

# Find the package via Conan-generated CMakeDeps
find_package(asplib REQUIRED)

add_executable(test_asplib test.cpp)
target_link_libraries(test_asplib asplib::asplib)
target_compile_features(test_asplib PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_asplib COMMAND test_asplib)
