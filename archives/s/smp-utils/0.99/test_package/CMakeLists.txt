cmake_minimum_required(VERSION 3.15)
project(smp_consumer_test LANGUAGES C)

find_package(smp-utils CONFIG REQUIRED)

add_executable(smp_consumer_test test_consumer.c)
target_link_libraries(smp_consumer_test PRIVATE smp-utils::smp-utils)

# Fully static test binary so it runs directly under qemu-user on the
# build host (OHOS musl interp is absent there) and needs no RPATH.
target_link_options(smp_consumer_test PRIVATE -static)
