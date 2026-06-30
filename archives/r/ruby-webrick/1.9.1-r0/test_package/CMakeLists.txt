cmake_minimum_required(VERSION 3.15)
project(test_ruby-webrick C)

# Find the package via Conan-generated CMakeDeps
find_package(ruby-webrick REQUIRED)

add_executable(test_ruby-webrick test.c)
target_link_libraries(test_ruby-webrick ruby-webrick::ruby-webrick)

enable_testing()
add_test(NAME test_ruby-webrick COMMAND test_ruby-webrick)
