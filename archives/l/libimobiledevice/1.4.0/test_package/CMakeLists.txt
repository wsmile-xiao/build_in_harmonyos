cmake_minimum_required(VERSION 3.15)
project(test_libimobiledevice C)

find_package(libimobiledevice REQUIRED)

add_executable(test_libimobiledevice test.c)
# static linking: link the whole closure explicitly (CMakeDeps does not
# propagate usage requirements through the aggregate target otherwise)
target_link_libraries(test_libimobiledevice PRIVATE
    libimobiledevice::libimobiledevice
    libusbmuxd::libusbmuxd
    libplist::libplist
    libimobiledevice-glue::libimobiledevice-glue
    libtatsu::libtatsu
    openssl::openssl
)

enable_testing()
add_test(NAME test_libimobiledevice COMMAND test_libimobiledevice)
