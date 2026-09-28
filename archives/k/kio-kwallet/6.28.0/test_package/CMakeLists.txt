cmake_minimum_required(VERSION 3.16)
project(test_kio_kwallet CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KF6Wallet REQUIRED CONFIG)

add_executable(test_kio_kwallet test_kio_kwallet.cpp)
target_link_libraries(test_kio_kwallet PRIVATE Qt6::Core Qt6::Gui KF6::Wallet)

enable_testing()
add_test(NAME test_kio_kwallet COMMAND test_kio_kwallet)
