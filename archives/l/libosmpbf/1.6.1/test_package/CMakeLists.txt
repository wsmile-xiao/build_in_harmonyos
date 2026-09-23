cmake_minimum_required(VERSION 3.15)
project(test_libosmpbf CXX)

# Registry protobuf exports cmake_find_mode=none: CMakeDeps generates no
# config/target for it and libosmpbf declares no cpp_info.requires (brpc
# precedent), so load the upstream protobuf config directly (Protobuf_DIR
# injected by the test conanfile) and link it explicitly.
find_package(Protobuf CONFIG REQUIRED)
if(NOT TARGET protobuf::protobuf)
    add_library(protobuf::protobuf INTERFACE IMPORTED)
    set_target_properties(protobuf::protobuf PROPERTIES
        INTERFACE_LINK_LIBRARIES protobuf::libprotobuf)
endif()

find_package(libosmpbf CONFIG REQUIRED)

add_executable(test_libosmpbf test.cpp)
target_compile_features(test_libosmpbf PRIVATE cxx_std_17)
target_link_libraries(test_libosmpbf PRIVATE libosmpbf::libosmpbf protobuf::libprotobuf)

enable_testing()
add_test(NAME test_libosmpbf COMMAND test_libosmpbf)
