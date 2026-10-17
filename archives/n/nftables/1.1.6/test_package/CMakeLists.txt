cmake_minimum_required(VERSION 3.15)
project(test_libnft C)

find_package(nftables REQUIRED)

add_executable(test_libnft test_libnft.c)
target_link_libraries(test_libnft nftables::nftables)

# Native socket-free smoke: links the packaged static libnftnl.a (via
# nftables::nftables which carries -lnftables -lnftnl + transitive libmnl)
# and exercises pure-userspace alloc/free for table/chain/rule/set.
# No kernel/root/netlink; see test_nftnl_smoke.c.
add_executable(test_nftnl_smoke test_nftnl_smoke.c)
target_link_libraries(test_nftnl_smoke nftables::nftables)
