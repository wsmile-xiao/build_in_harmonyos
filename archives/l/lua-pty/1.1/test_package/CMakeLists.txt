cmake_minimum_required(VERSION 3.15)
project(test_lua_pty C)

find_package(lua-pty REQUIRED)

add_executable(test_lua_pty test.c)
target_link_libraries(test_lua_pty lua-pty::lua-pty ${CMAKE_DL_LIBS})

# Export symbols so dlopen'd modules can resolve Lua API from main program
set_target_properties(test_lua_pty PROPERTIES ENABLE_EXPORTS TRUE)
