# intx test_package CMakeLists — 消费者视角验证
cmake_minimum_required(VERSION 3.16)
project(test_package_intx LANGUAGES CXX)

find_package(intx CONFIG REQUIRED)

add_executable(test_intx test_intx.cpp)
target_link_libraries(test_intx PRIVATE intx::intx)

include(CTest)
if(BUILD_TESTING)
    add_test(NAME test_intx COMMAND test_intx)
endif()
