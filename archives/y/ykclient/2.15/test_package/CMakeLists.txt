cmake_minimum_required(VERSION 3.15)
project(test_ykclient C)

# Find the package via Conan-generated CMakeDeps
find_package(ykclient REQUIRED)

add_executable(consumer_test consumer_test.c)
target_link_libraries(consumer_test ykclient::ykclient)

enable_testing()
add_test(NAME consumer_test COMMAND consumer_test)
