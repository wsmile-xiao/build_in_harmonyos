cmake_minimum_required(VERSION 3.15)
project(test_pajeng CXX)

# Find the package via Conan-generated CMakeDeps
find_package(pajeng REQUIRED)

add_executable(test_pajeng test.cpp)
target_link_libraries(test_pajeng pajeng::pajeng)
target_compile_definitions(test_pajeng PRIVATE
    PJ_DUMP_BIN="${PJ_DUMP_BIN}"
    TRACE_FILE="${CMAKE_CURRENT_SOURCE_DIR}/containers.trace"
)

enable_testing()
add_test(NAME test_pajeng COMMAND test_pajeng)
