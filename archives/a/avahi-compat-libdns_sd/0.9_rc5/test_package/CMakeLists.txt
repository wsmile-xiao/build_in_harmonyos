cmake_minimum_required(VERSION 3.15)
project(test_avahi_compat_libdns_sd C)

find_package(avahi-compat-libdns_sd CONFIG REQUIRED)

add_executable(test_dns_sd test.c)
target_link_libraries(test_dns_sd avahi-compat-libdns_sd::avahi-compat-libdns_sd)

add_test(NAME test_dns_sd COMMAND test_dns_sd)
