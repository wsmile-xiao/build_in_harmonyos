cmake_minimum_required(VERSION 3.15)
project(opusfile_consumer C)

find_package(OpusFile CONFIG REQUIRED)
find_package(Ogg CONFIG REQUIRED)
find_package(Opus CONFIG REQUIRED)

add_executable(opusfile_consumer test_package.c)
target_compile_features(opusfile_consumer PRIVATE c_std_99)
target_include_directories(
    opusfile_consumer
    PRIVATE
        "${OPUSFILE_TEST_OGG_INCLUDE}"
        "${OPUSFILE_TEST_OPUS_INCLUDE}"
        "${OPUSFILE_TEST_OPUS_INCLUDE}/opus"
)
target_link_libraries(
    opusfile_consumer
    PRIVATE
        OpusFile::opusfile
        OpusFile::opusurl
        Ogg::ogg
        Opus::opus
        "${OPUSFILE_TEST_OGG_LIBRARY}"
        "${OPUSFILE_TEST_OPUS_LIBRARY}"
)
