cmake_minimum_required(VERSION 3.15)
project(test_sonivox C)

# Find the package via Conan-generated CMakeDeps
find_package(sonivox REQUIRED)

add_executable(test_sonivox test.c)
target_link_libraries(test_sonivox PRIVATE sonivox::sonivox)

enable_testing()
add_test(NAME test_sonivox COMMAND test_sonivox)
