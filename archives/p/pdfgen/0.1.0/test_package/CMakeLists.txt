cmake_minimum_required(VERSION 3.15)
project(test_pdfgen C)

find_package(pdfgen REQUIRED)

add_executable(test_pdfgen test_pdfgen.c)
target_link_libraries(test_pdfgen PRIVATE pdfgen::pdfgen)
