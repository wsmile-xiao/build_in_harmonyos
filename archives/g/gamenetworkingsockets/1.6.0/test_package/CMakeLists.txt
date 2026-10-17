cmake_minimum_required(VERSION 3.15)
project(test_gns CXX)

# The registry protobuf package is cmake_find_mode=none: CMakeDeps does not
# generate a config/target for it, yet gamenetworkingsockets_DEPS_TARGET's
# link interface references protobuf::protobuf. Load the protobuf package's
# own installed config first (protobuf_DIR injected via conan_toolchain) and
# create the aggregate alias the DEPS_TARGET expects (brpc recipe pattern).
find_package(Protobuf CONFIG REQUIRED)
if(NOT TARGET protobuf::protobuf)
    add_library(protobuf::protobuf INTERFACE IMPORTED)
    set_target_properties(protobuf::protobuf PROPERTIES
        INTERFACE_LINK_LIBRARIES protobuf::libprotobuf)
endif()

# openssl resolves via CMakeDeps' generated config (openssl::openssl).
find_package(GameNetworkingSockets REQUIRED)

add_executable(test_gns test_package.cpp)
target_link_libraries(test_gns
    GameNetworkingSockets::GameNetworkingSockets_s
    protobuf::libprotobuf
)
target_compile_features(test_gns PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_gns COMMAND test_gns)
