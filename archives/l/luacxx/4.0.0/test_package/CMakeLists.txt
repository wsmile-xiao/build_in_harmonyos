cmake_minimum_required(VERSION 3.15)
project(test_luacxx CXX)

# Find the package via Conan-generated CMakeDeps
find_package(luacxx CONFIG REQUIRED)

add_executable(test_luacxx test_consumer.cpp)
target_compile_features(test_luacxx PRIVATE cxx_std_20)
# Lua C headers are needed because luacxx public headers include <lua.hpp>.
target_include_directories(test_luacxx PRIVATE ${LUA_INCLUDE_DIR})
# Default metatables are not provided automatically by luacxx.
target_compile_definitions(test_luacxx PRIVATE LUACXX_AUTO_METATABLE)
target_link_libraries(test_luacxx PRIVATE luacxx::luacxx)