cmake_minimum_required(VERSION 3.15)
project(test_soundtouch CXX)

# Find the package via Conan-generated CMakeDeps
find_package(sound-touch REQUIRED)

add_executable(test_soundtouch test.cpp)
target_link_libraries(test_soundtouch sound-touch::sound-touch)

enable_testing()
add_test(NAME test_soundtouch COMMAND test_soundtouch)