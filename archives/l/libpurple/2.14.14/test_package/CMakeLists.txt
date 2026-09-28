cmake_minimum_required(VERSION 3.15)
project(libpurple_consumer C)

find_package(libpurple REQUIRED CONFIG)
find_package(glib REQUIRED CONFIG)
find_package(libxml2 REQUIRED CONFIG)

enable_testing()
add_executable(test_libpurple test_libpurple.c)
target_link_libraries(test_libpurple PRIVATE
    libpurple::libpurple
    glib::glib
    LibXml2::LibXml2
)
add_test(NAME libpurple_consumer COMMAND test_libpurple)
