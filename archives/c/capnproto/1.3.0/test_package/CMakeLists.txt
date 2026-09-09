cmake_minimum_required(VERSION 3.6)
project(test_capnproto CXX)

find_package(CapnProto CONFIG REQUIRED)

add_executable(test_capnproto test.cpp)
target_link_libraries(test_capnproto CapnProto::capnp CapnProto::kj)
set_target_properties(test_capnproto PROPERTIES
    CXX_STANDARD 14
    CXX_STANDARD_REQUIRED ON
)