cmake_minimum_required(VERSION 3.15)
project(rotter_consumer_test C)

# Consumer-use feasibility on HarmonyOS: link the same codec/file stacks that
# rotter uses, through the Conan-generated CMakeDeps.
find_package(SndFile REQUIRED)
find_package(lame REQUIRED)
find_package(twolame REQUIRED)

add_executable(rotter_consumer_test consumer_test.c)
target_link_libraries(rotter_consumer_test PRIVATE
    SndFile::sndfile
    lame::lame
    twolame::twolame)

enable_testing()
add_test(NAME rotter_consumer_test COMMAND rotter_consumer_test)
