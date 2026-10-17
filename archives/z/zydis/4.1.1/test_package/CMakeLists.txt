cmake_minimum_required(VERSION 3.15)
project(test_zydis C)

find_package(zydis CONFIG REQUIRED)
find_package(zycore CONFIG REQUIRED)

add_executable(test_zydis test.c)
# HMBS: Zydis public headers include <Zycore/Defines.h>; link the namespaced
# Zycore target explicitly so consumer includes propagate even if transitive
# INTERFACE_LINK_LIBRARIES alone does not materialize on the true device.
target_link_libraries(test_zydis PRIVATE Zydis::Zydis Zycore::Zycore)
