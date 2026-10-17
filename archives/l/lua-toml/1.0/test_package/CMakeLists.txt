cmake_minimum_required(VERSION 3.15)
project(test_lua_toml LANGUAGES C)

find_package(lua CONFIG REQUIRED)
add_executable(test_lua_toml test_lua_toml.c)
target_link_libraries(test_lua_toml PRIVATE lua::lua)
