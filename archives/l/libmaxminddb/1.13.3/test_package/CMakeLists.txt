cmake_minimum_required(VERSION 3.15)
project(test_libmaxminddb C)

# Find the package via Conan-generated CMakeDeps
find_package(libmaxminddb CONFIG REQUIRED)

# Copy the upstream test database into the build directory so the test
# binary always finds it regardless of the working directory at runtime.
# The fixture is stored as base64 text (.mmdb.b64, same convention as
# aircrack/blur): GitCode's PR diff endpoint carries no binary patch data,
# so CI checkout-pr's git apply would fail on a committed binary .mmdb.
# conanfile.py test() decodes the .b64 back to .mmdb in the build dir.
configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/data/MaxMind-DB-test-ipv4-28.mmdb.b64
    ${CMAKE_CURRENT_BINARY_DIR}/MaxMind-DB-test-ipv4-28.mmdb.b64
    COPYONLY)

add_executable(test_libmaxminddb test_package.c)
target_link_libraries(test_libmaxminddb PRIVATE libmaxminddb::libmaxminddb)
target_compile_definitions(
    test_libmaxminddb
    PRIVATE MMDB_TEST_DB_PATH="${CMAKE_CURRENT_BINARY_DIR}/MaxMind-DB-test-ipv4-28.mmdb")

enable_testing()
add_test(NAME test_libmaxminddb COMMAND test_libmaxminddb)
