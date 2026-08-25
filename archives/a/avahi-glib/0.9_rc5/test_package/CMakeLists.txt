cmake_minimum_required(VERSION 3.15)
project(test_avahi_glib C)

find_package(avahi-glib CONFIG REQUIRED)

enable_testing()
add_executable(test_avahi_glib test.c)
target_link_libraries(test_avahi_glib PRIVATE avahi-glib::avahi-glib)
target_compile_features(test_avahi_glib PRIVATE c_std_99)

add_test(NAME test_avahi_glib COMMAND test_avahi_glib)
