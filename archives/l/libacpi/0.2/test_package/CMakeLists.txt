cmake_minimum_required(VERSION 3.15)
project(libacpi_consumer C)

enable_testing()

find_package(libacpi CONFIG REQUIRED)

add_executable(libacpi_consumer test_libacpi_consumer.c)
# libacpi.h defines the batteries/thermals/fans arrays instead of declaring
# them extern; clang 15 defaults to -fno-common, which would emit those
# symbols both here and in libacpi, so keep -fcommon for the consumer too.
target_compile_options(libacpi_consumer PRIVATE -fcommon)
target_link_libraries(libacpi_consumer PRIVATE libacpi::libacpi)

add_test(NAME consumer_assertions COMMAND libacpi_consumer)
