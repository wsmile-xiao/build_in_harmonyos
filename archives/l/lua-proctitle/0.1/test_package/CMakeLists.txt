cmake_minimum_required(VERSION 3.15)
project(test_lua_proctitle C)

find_package(lua CONFIG REQUIRED)

add_executable(test_lua_proctitle test_lua_proctitle.c)
target_compile_definitions(
    test_lua_proctitle
    PRIVATE PROCTITLE_MODULE_DIR="${PROCTITLE_MODULE_DIR}"
)
target_link_libraries(test_lua_proctitle PRIVATE lua::lua)
