cmake_minimum_required(VERSION 3.15)
project(libopusenc_consumer C)

find_package(libopusenc CONFIG REQUIRED)
find_package(Opus CONFIG REQUIRED)

add_executable(libopusenc_consumer test_package.c)
target_compile_features(libopusenc_consumer PRIVATE c_std_99)
target_include_directories(
    libopusenc_consumer
    PRIVATE
        "${LIBOPUSENC_TEST_OPUS_INCLUDE}"
        "${LIBOPUSENC_TEST_OPUS_INCLUDE}/opus"
)
target_link_libraries(
    libopusenc_consumer
    PRIVATE
        libopusenc::libopusenc
        Opus::opus
)
