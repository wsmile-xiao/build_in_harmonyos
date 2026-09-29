cmake_minimum_required(VERSION 3.15)
project(test_kanzi_cpp CXX)

find_package(kanzi-cpp CONFIG REQUIRED)

add_executable(test_kanzi_roundtrip test_kanzi_roundtrip.cpp)
target_link_libraries(test_kanzi_roundtrip PRIVATE kanzi-cpp::kanzi-cpp)
target_compile_features(test_kanzi_roundtrip PRIVATE cxx_std_17)

# KANZI_BIN: full path of the packaged kanzi executable, injected by the
# test_package conanfile (conanrun PATH is not active at configure time,
# so the lookup happens in Python, not here).
enable_testing()
add_test(NAME roundtrip COMMAND test_kanzi_roundtrip)
add_test(NAME cli_roundtrip
         COMMAND ${CMAKE_COMMAND}
                 -DKANZI_BIN=${KANZI_BIN}
                 -DWORK_DIR=${CMAKE_CURRENT_BINARY_DIR}/cli_work
                 -P ${CMAKE_CURRENT_SOURCE_DIR}/cli_test.cmake)
