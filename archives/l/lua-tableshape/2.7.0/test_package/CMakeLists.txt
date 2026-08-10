cmake_minimum_required(VERSION 3.15)
project(test_tableshape C)

find_package(lua CONFIG REQUIRED)

add_executable(test_tableshape test_tableshape.c)
target_compile_definitions(
    test_tableshape
    PRIVATE TABLESHAPE_MODULE_DIR="${TABLESHAPE_MODULE_DIR}"
)
target_link_libraries(test_tableshape PRIVATE lua::lua)
