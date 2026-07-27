cmake_minimum_required(VERSION 3.5)
project(test_openjpeg C)

find_package(OpenJPEG REQUIRED)

add_executable(test_openjpeg test_openjpeg.c)
target_link_libraries(test_openjpeg OPENJPEG::OpenJPEG)

enable_testing()
add_test(NAME openjpeg_version_test COMMAND test_openjpeg)
