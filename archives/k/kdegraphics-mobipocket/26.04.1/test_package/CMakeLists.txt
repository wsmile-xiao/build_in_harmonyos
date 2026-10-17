cmake_minimum_required(VERSION 3.15)
project(test_mobipocket CXX)

find_package(QMobipocket6 REQUIRED)

add_executable(test_mobipocket test_mobipocket.cpp)
target_link_libraries(test_mobipocket QMobipocket6)

enable_testing()
add_test(NAME test_mobipocket COMMAND test_mobipocket)
