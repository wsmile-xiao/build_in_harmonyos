cmake_minimum_required(VERSION 3.15)
project(test_munit C)

# Find the package via Conan-generated CMakeDeps
find_package(munit REQUIRED CONFIG)

# Create executable by compiling munit.c with our test
# munit.c is installed alongside munit.h in the include directory
add_executable(test_munit test.c)

# Link with the munit target to get include paths
target_link_libraries(test_munit munit::munit)

# Manually add munit.c to the compilation
# Get include directory from the target
get_target_property(MUNIT_INCLUDE_DIR munit::munit INTERFACE_INCLUDE_DIRECTORIES)
target_sources(test_munit PRIVATE ${MUNIT_INCLUDE_DIR}/munit.c)

# Set C standard
target_compile_features(test_munit PRIVATE c_std_99)

enable_testing()
add_test(NAME test_munit COMMAND test_munit)
