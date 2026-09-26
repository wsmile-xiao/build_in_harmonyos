cmake_minimum_required(VERSION 3.15)
project(test_audioresamplerate C)

# Find the package via Conan-generated CMakeDeps
find_package(audioresamplerate REQUIRED)

add_executable(test_audioresamplerate test.c)
target_link_libraries(test_audioresamplerate audioresamplerate::audioresamplerate)

enable_testing()
add_test(NAME test_audioresamplerate COMMAND test_audioresamplerate)
