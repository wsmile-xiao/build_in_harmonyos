cmake_minimum_required(VERSION 3.15)
project(test_c11threads C)

find_package(c11threads CONFIG REQUIRED)

add_executable(test_c11threads test_c11threads.c)
target_link_libraries(test_c11threads PRIVATE c11threads::c11threads)
set_property(TARGET test_c11threads PROPERTY C_STANDARD 11)
# c11threads wraps pthreads; on OHOS/musl the pthread symbols live in libc,
# and on glibc Linux the explicit pthread flag is required.
find_package(Threads REQUIRED)
target_link_libraries(test_c11threads PRIVATE Threads::Threads)
