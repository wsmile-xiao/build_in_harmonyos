cmake_minimum_required(VERSION 3.15)
project(test_lua_rapidjson C)

find_package(lua REQUIRED)

add_executable(test_lua_rapidjson test.c)
target_link_libraries(test_lua_rapidjson lua::lua)

# Export symbols so the Lua extension module (rapidjson.so) can resolve
# Lua API symbols from the host process at runtime.
set_target_properties(test_lua_rapidjson PROPERTIES ENABLE_EXPORTS ON)

target_compile_definitions(test_lua_rapidjson PRIVATE
    RAPIDJSON_LIB_DIR="${RAPIDJSON_LIB_DIR}")
