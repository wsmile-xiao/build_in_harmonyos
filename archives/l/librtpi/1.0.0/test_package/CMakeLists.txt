cmake_minimum_required(VERSION 3.10)
project(test_librtpi C CXX)

find_package(librtpi CONFIG REQUIRED)

add_executable(test_rtpi test_rtpi.c)
target_link_libraries(test_rtpi PRIVATE librtpi::librtpi)

add_executable(consumer_checks consumer_checks.c)
target_link_libraries(consumer_checks PRIVATE librtpi::librtpi)

add_executable(consumer_cpp consumer_cpp.cpp)
target_link_libraries(consumer_cpp PRIVATE librtpi::librtpi)

enable_testing()
add_test(NAME rtpi_smoke COMMAND test_rtpi)
add_test(NAME rtpi_consumer_checks COMMAND consumer_checks)
add_test(NAME rtpi_consumer_cpp COMMAND consumer_cpp)
