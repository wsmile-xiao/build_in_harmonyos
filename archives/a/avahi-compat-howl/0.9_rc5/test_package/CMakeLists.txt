cmake_minimum_required(VERSION 3.15)
project(test_avahi_compat_howl C)

find_package(avahi-compat-howl REQUIRED CONFIG)
add_executable(howl_text_record test.c)
target_link_libraries(howl_text_record PRIVATE avahi-compat-howl::avahi-compat-howl)

enable_testing()
add_test(NAME howl_text_record COMMAND howl_text_record)
