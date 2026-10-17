cmake_minimum_required(VERSION 3.15)
project(consumer_vmime CXX)

find_package(vmime REQUIRED)

add_executable(consumer_vmime consumer_vmime.cpp)
target_link_libraries(consumer_vmime vmime::vmime)
if(TARGET openssl::openssl)
  target_link_libraries(consumer_vmime openssl::openssl)
endif()
if(TARGET libiconv::libiconv)
  target_link_libraries(consumer_vmime libiconv::libiconv)
endif()
