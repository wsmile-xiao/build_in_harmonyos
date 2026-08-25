cmake_minimum_required(VERSION 3.15)
project(test_pulseaudio C)

# Find the package via Conan-generated CMakeDeps
find_package(pulseaudio REQUIRED)

add_executable(test_pulseaudio test.c)
target_link_libraries(test_pulseaudio pulseaudio::pulse)

enable_testing()
add_test(NAME test_pulseaudio COMMAND test_pulseaudio)
