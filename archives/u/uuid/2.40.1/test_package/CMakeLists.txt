cmake_minimum_required(VERSION 3.15)
project(test_uuid C)

find_package(uuid REQUIRED CONFIG)

add_executable(test_uuid_api test_uuid.c)
target_link_libraries(test_uuid_api PRIVATE uuid::uuid)
