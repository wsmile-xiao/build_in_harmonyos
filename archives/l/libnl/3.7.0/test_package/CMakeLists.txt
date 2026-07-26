cmake_minimum_required(VERSION 3.15)
project(test_libnl C)

find_package(libnl CONFIG REQUIRED)

add_executable(test_libnl test_libnl.c)
target_compile_definitions(test_libnl PRIVATE
    _UAPI_LINUX_SOCKET_H
    __kernel_sa_family_t=ushort
)
target_link_libraries(test_libnl PRIVATE
    libnl::nl-3
    libnl::nl-route-3
    libnl::nl-genl-3
    libnl::nl-nf-3
    libnl::nl-idiag-3
    libnl::nl-xfrm-3
)
