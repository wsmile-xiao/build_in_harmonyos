cmake_minimum_required(VERSION 3.14)
project(libsee_consumer C)

find_package(libsee CONFIG REQUIRED)
add_executable(libsee_consumer test.c)
target_link_libraries(libsee_consumer PRIVATE libsee::libsee)
if(NOT OHOS)
    target_link_libraries(libsee_consumer PRIVATE dl)
endif()
# Keep the consumer's runtime lookup independent of a system installation.
set_target_properties(libsee_consumer PROPERTIES BUILD_RPATH "$<TARGET_FILE_DIR:libsee::libsee>")
