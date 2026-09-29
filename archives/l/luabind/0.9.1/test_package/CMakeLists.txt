cmake_minimum_required(VERSION 3.16)
project(test_package CXX)

find_package(luabind CONFIG REQUIRED)
find_package(lua CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE luabind::luabind lua::lua)
target_include_directories(test_package PRIVATE ${LUA_INCLUDE_DIR} ${BOOST_INCLUDE_DIR})