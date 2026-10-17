cmake_minimum_required(VERSION 3.15)
project(test_libspatialaudio CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libspatialaudio REQUIRED)

add_executable(test_libspatialaudio test_consumer.cpp)
target_link_libraries(test_libspatialaudio PRIVATE libspatialaudio::libspatialaudio)

enable_testing()
add_test(NAME test_libspatialaudio COMMAND test_libspatialaudio)
