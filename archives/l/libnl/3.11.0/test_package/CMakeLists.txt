cmake_minimum_required(VERSION 3.15)
project(test_libnl C)

find_package(libnl CONFIG REQUIRED)

add_executable(test_libnl test_libnl.c)

# musl / linux-headers 兼容（继承 libnl/3.7.0 已验证的处置）：
# libnl 公开头会间接引入 <linux/netlink.h>，该头依赖 __kernel_sa_family_t；
# 用 _UAPI_LINUX_SOCKET_H 拦掉内核 socket 头、自行给出内核别名，避免与
# musl 的 <sys/socket.h> 冲突。
target_compile_definitions(test_libnl PRIVATE
    _UAPI_LINUX_SOCKET_H
    __kernel_sa_family_t=ushort
)

# 链接全部 6 个交付子库，逐个验证可消费
target_link_libraries(test_libnl PRIVATE
    libnl::nl-3
    libnl::nl-route-3
    libnl::nl-genl-3
    libnl::nl-nf-3
    libnl::nl-idiag-3
    libnl::nl-xfrm-3
)
