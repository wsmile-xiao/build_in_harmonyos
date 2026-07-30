cmake_minimum_required(VERSION 3.15)
project(test_lua_luv C)

find_package(lua-luv CONFIG REQUIRED)
find_package(lua CONFIG REQUIRED)
find_package(libuv CONFIG REQUIRED)

add_executable(test_lua_luv test.c)
target_link_libraries(test_lua_luv
    PRIVATE lua-luv::lua-luv lua::lua libuv::libuv ${CMAKE_DL_LIBS})

# Lua is linked statically; make its API symbols visible to the loaded module.
set_target_properties(test_lua_luv PROPERTIES ENABLE_EXPORTS TRUE)
