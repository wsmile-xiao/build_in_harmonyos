cmake_minimum_required(VERSION 3.16)
project(test_qtkeychain CXX)

find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(Qt6Keychain REQUIRED CONFIG)

add_executable(test_qtkeychain test_qtkeychain.cpp)
if(TARGET Qt6Keychain::Qt6Keychain)
    target_link_libraries(test_qtkeychain PRIVATE Qt6Keychain::Qt6Keychain Qt6::Core)
else()
    target_link_libraries(test_qtkeychain PRIVATE qt6keychain Qt6::Core)
endif()

enable_testing()
add_test(NAME test_qtkeychain COMMAND test_qtkeychain)
