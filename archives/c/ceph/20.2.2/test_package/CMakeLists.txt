cmake_minimum_required(VERSION 3.16)
project(test_ceph_crush LANGUAGES C)

find_package(ceph CONFIG REQUIRED)

add_executable(test_ceph_crush test_ceph_crush.c)
target_compile_features(test_ceph_crush PRIVATE c_std_99)
target_link_libraries(test_ceph_crush PRIVATE ceph::crush)
