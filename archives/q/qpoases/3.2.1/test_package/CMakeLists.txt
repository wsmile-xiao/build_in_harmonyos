cmake_minimum_required(VERSION 3.15)
project(test_qpoases CXX)

# The installed package exports only an include dir and libqpOASES.a; upstream
# ships no CMake config module, so locate the library directly.
find_path(QPOASES_INCLUDE_DIR qpOASES.hpp REQUIRED)
find_library(QPOASES_LIBRARY NAMES qpOASES REQUIRED)

add_executable(test_qpoases test_qpoases.cpp)
target_include_directories(test_qpoases PRIVATE ${QPOASES_INCLUDE_DIR})
target_link_libraries(test_qpoases PRIVATE ${QPOASES_LIBRARY})
set_target_properties(test_qpoases PROPERTIES
    CXX_STANDARD 11 CXX_STANDARD_REQUIRED ON CXX_EXTENSIONS OFF)
