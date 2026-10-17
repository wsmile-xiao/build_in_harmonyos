cmake_minimum_required(VERSION 3.15)
project(test_oggz C)

# Find the package via Conan-generated CMakeDeps
find_package(oggz REQUIRED)

add_executable(test_oggz test.c)
target_link_libraries(test_oggz oggz::oggz)
if(LIBOGG_INCLUDE_DIR)
    target_include_directories(test_oggz PRIVATE ${LIBOGG_INCLUDE_DIR})
endif()

enable_testing()
add_test(NAME test_oggz COMMAND test_oggz)
