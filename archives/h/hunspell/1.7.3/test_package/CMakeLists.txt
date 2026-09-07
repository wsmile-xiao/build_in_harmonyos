cmake_minimum_required(VERSION 3.15)
project(test_hunspell CXX)

# Find the package via Conan-generated CMakeDeps
find_package(hunspell REQUIRED)

add_executable(test_hunspell test.cpp)
target_link_libraries(test_hunspell hunspell::hunspell)

# copy the bundled mini dictionary next to the test binary (ctest CWD = build dir)
file(COPY test.aff test.dic DESTINATION ${CMAKE_CURRENT_BINARY_DIR})

enable_testing()
add_test(NAME test_hunspell COMMAND test_hunspell)
