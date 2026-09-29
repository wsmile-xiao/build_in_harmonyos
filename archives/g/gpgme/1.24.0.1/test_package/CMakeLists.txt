cmake_minimum_required(VERSION 3.16)
project(test_gpgme C CXX)

find_package(gpgme REQUIRED)
find_package(Gpgmepp REQUIRED CONFIG)
find_package(QGpgmeQt6 REQUIRED CONFIG)
find_package(Qt6 REQUIRED COMPONENTS Core)

add_executable(test_gpgme test_gpgme.cpp)
target_link_libraries(test_gpgme PRIVATE gpgme::gpgme Gpgmepp QGpgmeQt6 Qt6::Core)

enable_testing()
add_test(NAME test_gpgme COMMAND test_gpgme)
