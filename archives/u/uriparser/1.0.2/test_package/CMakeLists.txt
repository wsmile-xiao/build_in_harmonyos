cmake_minimum_required(VERSION 3.15)
project(test_uriparser C)

# Find the package via Conan-generated CMakeDeps
find_package(uriparser REQUIRED)

add_executable(test_uriparser test.c)
target_link_libraries(test_uriparser uriparser::uriparser)

# HarmonyOS-specific wchar API test (R13 review fix): build from committed
# source and execute on the bound OH device. Calls real wide-character
# uriparser APIs (uriParseUriW / uriToStringW / uriFreeUriMembersW).
add_executable(test_harmonyos test_harmonyos.c)
target_link_libraries(test_harmonyos uriparser::uriparser)

enable_testing()
add_test(NAME test_uriparser COMMAND test_uriparser)
add_test(NAME test_harmonyos COMMAND test_harmonyos)
