cmake_minimum_required(VERSION 3.15)
project(test_maxminddb C)

# Find the package via Conan-generated CMakeDeps
find_package(maxminddb REQUIRED)

add_executable(test_maxminddb test.c)
target_link_libraries(test_maxminddb maxminddb::maxminddb)

# Copy the decoder test database next to the test binary so the consumer
# test can open it via the relative "data/" path.
add_custom_command(TARGET test_maxminddb POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
            ${CMAKE_CURRENT_SOURCE_DIR}/data
            $<TARGET_FILE_DIR:test_maxminddb>/data)

enable_testing()
add_test(NAME test_maxminddb COMMAND test_maxminddb)
