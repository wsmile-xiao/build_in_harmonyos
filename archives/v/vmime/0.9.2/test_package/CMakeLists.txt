cmake_minimum_required(VERSION 3.15)
project(test_vmime CXX)

find_package(vmime REQUIRED)

add_executable(test_vmime test.cpp)
target_link_libraries(test_vmime vmime::vmime)
if(TARGET openssl::openssl)
  target_link_libraries(test_vmime openssl::openssl)
endif()
if(TARGET libiconv::libiconv)
  target_link_libraries(test_vmime libiconv::libiconv)
endif()

enable_testing()
add_test(NAME test_vmime COMMAND test_vmime)
