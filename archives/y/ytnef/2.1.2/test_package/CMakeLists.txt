cmake_minimum_required(VERSION 3.15)
project(test_ytnef LANGUAGES C)

# Locate the package through the Conan-generated CMakeDeps files.
find_package(ytnef CONFIG REQUIRED)

add_executable(ytnef_test test.c)
target_link_libraries(ytnef_test PRIVATE ytnef::ytnef)

# The consumer test decodes a real TNEF stream.  The fixture is shipped
# base64 encoded (one-file.tnef.b64) and materialised by the test_package
# conanfile.py before ctest runs, so no binary file has to travel inside the
# merge-request diff.
enable_testing()
add_test(NAME ytnef_test COMMAND ytnef_test)
set_tests_properties(ytnef_test PROPERTIES WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}")
