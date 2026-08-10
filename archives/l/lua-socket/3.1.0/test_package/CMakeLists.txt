cmake_minimum_required(VERSION 3.15)
project(test_lua_socket C)

find_package(lua-socket CONFIG REQUIRED)
find_package(lua CONFIG REQUIRED)

add_executable(test_lua_socket test.c)
target_link_libraries(test_lua_socket
    PRIVATE lua-socket::lua-socket lua::lua ${CMAKE_DL_LIBS})

# Lua is linked statically; its API symbols must be visible to the
# dlopen'd lua-socket .so modules at runtime.
set_target_properties(test_lua_socket PROPERTIES ENABLE_EXPORTS TRUE)
