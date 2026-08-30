cmake_minimum_required(VERSION 3.15)
project(test_websocketpp CXX)

# Find the package via Conan-generated CMakeDeps
# (cmake_file_name = "Websocketpp", matching autobahn-cpp FindWebsocketpp usage)
find_package(Websocketpp REQUIRED)

add_executable(test_websocketpp test.cpp)
target_link_libraries(test_websocketpp PRIVATE websocketpp::websocketpp)

enable_testing()
add_test(NAME test_websocketpp COMMAND test_websocketpp)
