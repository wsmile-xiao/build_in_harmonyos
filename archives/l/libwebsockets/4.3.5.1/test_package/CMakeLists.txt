cmake_minimum_required(VERSION 3.15)
project(test_libwebsockets LANGUAGES C)

find_package(libwebsockets CONFIG REQUIRED)
find_package(openssl CONFIG REQUIRED)
find_package(libuv CONFIG REQUIRED)

add_executable(lws_consumer test.c)
target_link_libraries(
    lws_consumer PRIVATE
    libwebsockets::libwebsockets
    openssl::openssl
    libuv::libuv
)
