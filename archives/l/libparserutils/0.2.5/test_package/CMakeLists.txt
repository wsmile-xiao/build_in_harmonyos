cmake_minimum_required(VERSION 3.15)
project(test_libparserutils C)

# Find the package via Conan-generated CMakeDeps
find_package(LibParserUtils REQUIRED)

add_executable(test_libparserutils test.c)
target_link_libraries(test_libparserutils LibParserUtils::parserutils)

enable_testing()
add_test(NAME test_libparserutils COMMAND test_libparserutils)
