cmake_minimum_required(VERSION 3.15)
project(srtp_consumer_test LANGUAGES C)

find_package(libSRTP CONFIG REQUIRED)

add_executable(test_srtp test_srtp.c)
target_link_libraries(test_srtp PRIVATE libSRTP::srtp2)
