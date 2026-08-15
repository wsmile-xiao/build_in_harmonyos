cmake_minimum_required(VERSION 3.16)
project(test_qthttpserver CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core Network)
# qtbase-gui and qthttpserver are separate Conan package prefixes.  Qt's
# umbrella Qt6Config.cmake only searches its own prefix for extra modules, so
# locate the module's native config package directly.
find_package(Qt6HttpServer 6.11.1 CONFIG REQUIRED)
add_executable(test_qthttpserver test_qthttpserver.cpp)
target_link_libraries(test_qthttpserver PRIVATE Qt6::HttpServer Qt6::Core Qt6::Network)
