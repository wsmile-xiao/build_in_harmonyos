cmake_minimum_required(VERSION 3.14)
project(test_percona_server_client C)

find_package(percona-server CONFIG REQUIRED)

add_executable(test_percona_server_client test_percona_server_client.c)
target_link_libraries(test_percona_server_client PRIVATE percona-server::percona-server)
