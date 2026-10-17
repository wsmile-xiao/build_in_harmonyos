cmake_minimum_required(VERSION 3.15)
project(test_itk_consumer CXX)

find_package(ITK REQUIRED CONFIG COMPONENTS ITKCommon)
include(${ITK_USE_FILE})

add_executable(test_itk_consumer test_itk.cpp)
target_link_libraries(test_itk_consumer PRIVATE ${ITK_LIBRARIES})
