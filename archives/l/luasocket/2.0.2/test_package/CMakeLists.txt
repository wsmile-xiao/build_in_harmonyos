cmake_minimum_required(VERSION 3.15)
project(test_luasocket C)

find_package(luasocket CONFIG REQUIRED)
find_package(lua CONFIG REQUIRED)

add_executable(test_luasocket test.c)
target_link_libraries(test_luasocket
    PRIVATE luasocket::luasocket lua::lua ${CMAKE_DL_LIBS})

# Lua is linked statically; its API symbols must be visible to the
# dlopen'd luasocket .so modules at runtime.  On HarmonyOS CMake treats the
# system as unknown, so ENABLE_EXPORTS does not emit --export-dynamic;
# pass -rdynamic explicitly.
set_target_properties(test_luasocket PROPERTIES ENABLE_EXPORTS TRUE)
target_link_options(test_luasocket PRIVATE "-rdynamic")

enable_testing()
add_test(NAME test_luasocket COMMAND test_luasocket)
