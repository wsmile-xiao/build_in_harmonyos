cmake_minimum_required(VERSION 3.15)
project(test_libmeshb_consumer C)

find_package(libmeshb REQUIRED)

add_executable(test_libmeshb_consumer test_libmeshb_consumer.c)
target_link_libraries(test_libmeshb_consumer libmeshb::libmeshb)
