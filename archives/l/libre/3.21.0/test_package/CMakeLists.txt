cmake_minimum_required(VERSION 3.15)
project(libre_package_test C)

find_package(libre CONFIG REQUIRED)

file(GLOB TEST_SOURCES CONFIGURE_DEPENDS t_*.c)
foreach(src ${TEST_SOURCES})
  get_filename_component(exe ${src} NAME_WE)
  add_executable(${exe} ${src})
  target_link_libraries(${exe} PRIVATE libre::libre)
endforeach()
