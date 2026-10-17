cmake_minimum_required(VERSION 3.15)
project(kmousetool_test CXX)

find_package(X11 REQUIRED COMPONENTS Xtst)

add_executable(xtest_smoke xtest_smoke.cpp)
target_include_directories(xtest_smoke PRIVATE ${X11_INCLUDE_DIR})
target_link_libraries(xtest_smoke PRIVATE ${X11_Xtst_LIB} ${X11_X11_LIB})

enable_testing()
add_test(NAME xtest_smoke COMMAND xtest_smoke)
