cmake_minimum_required(VERSION 3.15)
project(test_uuid C)

find_package(uuid REQUIRED)

add_executable(test_uuid test_uuid.c)
target_link_libraries(test_uuid uuid::uuid)