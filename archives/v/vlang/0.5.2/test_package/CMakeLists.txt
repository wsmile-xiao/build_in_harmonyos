cmake_minimum_required(VERSION 3.16)
project(test_v_metadata CXX)

add_executable(test_v_metadata test_v_metadata.cpp)
target_compile_features(test_v_metadata PRIVATE cxx_std_17)

enable_testing()
set(VLANG_EXECUTABLE "" CACHE FILEPATH "Installed V compiler wrapper")
set(VLANG_LAUNCHER "" CACHE STRING "Optional launcher for the V wrapper")
if(NOT VLANG_EXECUTABLE)
    message(FATAL_ERROR "VLANG_EXECUTABLE must point to the installed v wrapper")
endif()

if(VLANG_LAUNCHER)
    add_test(NAME test_v_metadata COMMAND test_v_metadata "${VLANG_LAUNCHER}" "${VLANG_EXECUTABLE}" version)
else()
    add_test(NAME test_v_metadata COMMAND test_v_metadata "${VLANG_EXECUTABLE}" version)
endif()
