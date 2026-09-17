cmake_minimum_required(VERSION 3.16)
project(test_phonon4qt6 CXX)

find_package(Phonon4Qt6 REQUIRED)

add_executable(test_phonon4qt6 test_phonon.cpp)
target_link_libraries(test_phonon4qt6 Phonon::phonon4qt6)

enable_testing()
add_test(NAME test_phonon4qt6 COMMAND test_phonon4qt6)
