cmake_minimum_required(VERSION 3.15)
project(test_clxclient LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(clxclient CONFIG REQUIRED)

add_executable(test_clxclient test_clxclient.cpp)
target_compile_options(test_clxclient PRIVATE -Wall -Wextra -Werror)
target_link_libraries(test_clxclient PRIVATE clxclient::clxclient)
set_target_properties(test_clxclient PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    if(NOT DEFINED CLXCLIENT_TEST_RUNTIME_PATH OR
       NOT IS_DIRECTORY "${CLXCLIENT_TEST_RUNTIME_PATH}")
        message(FATAL_ERROR "CLXCLIENT_TEST_RUNTIME_PATH is missing")
    endif()
    target_link_options(
        test_clxclient
        PRIVATE
            "-Wl,--disable-new-dtags"
            "-Wl,-rpath,${CLXCLIENT_TEST_RUNTIME_PATH}"
    )
endif()
