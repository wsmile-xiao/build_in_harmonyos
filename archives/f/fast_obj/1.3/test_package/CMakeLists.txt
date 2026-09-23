cmake_minimum_required(VERSION 3.15)
project(test_fast_obj C)

# Find the package via Conan-generated CMakeDeps
find_package(fast_obj REQUIRED)

add_executable(test_fast_obj test.c)
target_link_libraries(test_fast_obj fast_obj::fast_obj)

# Copy the sample OBJ next to the test binary (test reads it at runtime)
add_custom_command(TARGET test_fast_obj POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_CURRENT_SOURCE_DIR}/cube.obj
        $<TARGET_FILE_DIR:test_fast_obj>/cube.obj)

enable_testing()
add_test(NAME test_fast_obj COMMAND test_fast_obj)
