cmake_minimum_required(VERSION 3.15)
project(tdlib_test_package CXX)

# Consumes the upstream "Td" CMake package installed by the recipe
# (lib/cmake/Td/TdConfig.cmake, located through the Td_DIR cache variable set
# in test_package/conanfile.py generate()).
find_package(Td CONFIG REQUIRED)

add_executable(test_tdlib test_tdlib.cpp)
target_link_libraries(test_tdlib PRIVATE Td::TdJson ${CMAKE_DL_LIBS})
# The test resolves the packaged shared object itself (dlopen/dladdr) and
# compares it against the artifact the build actually linked.
target_compile_definitions(test_tdlib PRIVATE
    EXPECTED_TDJSON_PATH="$<TARGET_FILE:Td::tdjson>")
target_link_options(test_tdlib PRIVATE
    "$<$<PLATFORM_ID:HarmonyOS>:-Wl,-rpath,$<TARGET_FILE_DIR:Td::tdjson>>")
set_target_properties(test_tdlib PROPERTIES CXX_STANDARD 14 CXX_STANDARD_REQUIRED ON)
