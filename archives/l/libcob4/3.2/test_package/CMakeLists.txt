cmake_minimum_required(VERSION 3.15)
project(test_libcob4 C)

# Find the package through the Conan-generated CMakeDeps config
find_package(libcob4 REQUIRED)

add_executable(test_libcob test_libcob.c)
target_link_libraries(test_libcob libcob4::libcob4)

# Keep the executable at a predictable location so test_libcob.sh can find it
# (the shell driver needs to spawn it several times with different TMPDIR).
set_target_properties(test_libcob PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")

enable_testing()
add_test(NAME libcob4_api COMMAND test_libcob api)
