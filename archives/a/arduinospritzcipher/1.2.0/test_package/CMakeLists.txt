cmake_minimum_required(VERSION 3.15)
project(test_arduinospritzcipher C)

# Find the package via Conan-generated CMakeDeps
find_package(arduinospritzcipher REQUIRED)

add_executable(test_arduinospritzcipher test.c)
target_link_libraries(test_arduinospritzcipher arduinospritzcipher::arduinospritzcipher)

enable_testing()
add_test(NAME test_arduinospritzcipher COMMAND test_arduinospritzcipher)
