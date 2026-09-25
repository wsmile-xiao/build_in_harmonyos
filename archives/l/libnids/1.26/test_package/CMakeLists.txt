cmake_minimum_required(VERSION 3.15)
project(test_libnids C)

find_package(libnids REQUIRED)
find_package(libpcap REQUIRED)

add_executable(test_nids test_nids.c)
# nids.h publicly includes <pcap.h>, so the consumer must link libpcap
# explicitly for its include dir. Relying on transitive propagation via
# libnids::libnids alone leaves pcap.h not found on the true machine
# (2026-09-20 preflight: test_nids.c.o fatal error 'pcap.h' file not found
# even though find_package(libpcap) succeeded).
target_link_libraries(test_nids libnids::libnids libpcap::libpcap)

enable_testing()
add_test(NAME test_nids COMMAND test_nids)
