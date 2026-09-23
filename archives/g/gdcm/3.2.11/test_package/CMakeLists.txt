cmake_minimum_required(VERSION 3.15)
project(test_gdcm CXX)

find_package(GDCM REQUIRED)

add_executable(test_gdcm test_gdcm.cpp)
if(TARGET GDCM::GDCM)
    target_link_libraries(test_gdcm PRIVATE GDCM::GDCM)
else()
    target_include_directories(test_gdcm PRIVATE ${GDCM_INCLUDE_DIRS})
    target_link_libraries(test_gdcm PRIVATE ${GDCM_LIBRARIES})
endif()
