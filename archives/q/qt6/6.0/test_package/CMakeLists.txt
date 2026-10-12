cmake_minimum_required(VERSION 3.16)
project(test_qt6 LANGUAGES CXX)

find_package(Qt6 6.0 REQUIRED COMPONENTS Core Network Gui Widgets Xml)

add_executable(test_qt6 test_qt6.cpp)
target_compile_features(test_qt6 PRIVATE cxx_std_17)
target_link_libraries(test_qt6 PRIVATE
    Qt6::Core
    Qt6::Network
    Qt6::Gui
    Qt6::Widgets
    Qt6::Xml
)

add_executable(qt6_cross_uid_server cross_uid_server.cpp)
target_compile_features(qt6_cross_uid_server PRIVATE cxx_std_17)
target_link_libraries(qt6_cross_uid_server PRIVATE Qt6::Core Qt6::Network)

configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/testdata/selfsigned-server.crt"
    "${CMAKE_CURRENT_BINARY_DIR}/selfsigned-server.crt"
    COPYONLY
)
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/testdata/selfsigned-server.key"
    "${CMAKE_CURRENT_BINARY_DIR}/selfsigned-server.key"
    COPYONLY
)
