cmake_minimum_required(VERSION 3.15)
project(test_lua_pc C)

# Find the package via Conan-generated CMakeDeps
find_package(lua-pc REQUIRED)

add_executable(test_lua_pc test.c)
target_link_libraries(test_lua_pc lua-pc::lua-pc)

enable_testing()
add_test(NAME test_lua_pc COMMAND test_lua_pc)
