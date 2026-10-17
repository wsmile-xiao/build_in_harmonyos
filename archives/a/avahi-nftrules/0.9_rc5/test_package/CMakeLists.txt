cmake_minimum_required(VERSION 3.15)
project(test_avahi_nftrules CXX)

find_package(avahi-nftrules REQUIRED CONFIG)

add_executable(test_avahi_nftrules test_avahi_nftrules.cpp)
target_link_libraries(test_avahi_nftrules avahi-nftrules::avahi-nftrules)
