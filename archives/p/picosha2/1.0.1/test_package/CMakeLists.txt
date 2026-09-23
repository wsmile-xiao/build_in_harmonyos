cmake_minimum_required(VERSION 3.15)
project(test_picosha2 CXX)

# Find the package via Conan-generated CMakeDeps
find_package(picosha2 REQUIRED)

add_executable(test_picosha2 test_picosha2.cpp)
target_link_libraries(test_picosha2 picosha2::picosha2)
target_compile_features(test_picosha2 PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_picosha2 COMMAND test_picosha2)
