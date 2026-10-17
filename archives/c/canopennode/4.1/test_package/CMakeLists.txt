cmake_minimum_required(VERSION 3.15)
project(test_canopennode C)

find_package(canopennode CONFIG REQUIRED)

# Consumer hardware abstraction layer: upstream "blank" generic CAN driver +
# sample Object Dictionary (same set upstream's example/Makefile compiles).
add_executable(test_canopennode
    test.c
    CO_driver_blank.c
    CO_storageBlank.c
    OD.c
)
target_include_directories(test_canopennode PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(test_canopennode PRIVATE canopennode::canopennode)

# R34: run the test binary during ctest (L1 test)
include(CTest)
if(BUILD_TESTING)
    add_test(NAME test_canopennode COMMAND test_canopennode)
endif()
