cmake_minimum_required(VERSION 3.15)
project(mecab_unidic_extended_test CXX)
find_package(mecab CONFIG REQUIRED)

# Generic MeCab consumer (platform-neutral): golden tokenization via libmecab
add_executable(test_package src/test_package.cpp)
target_link_libraries(test_package PRIVATE mecab::mecab)

# HarmonyOS PC (OHOS) specific test: OHOS target attributes, ELF64/AArch64/
# musl-loader identity, OHOS libmecab loading the packaged indices
add_executable(ohos_specific_test src/ohos_specific_test.cpp)
target_link_libraries(ohos_specific_test PRIVATE mecab::mecab)

enable_testing()
# Both binaries take <dicdir> <rcfile> arguments supplied by conanfile.py
# test() (dicdir differs per machine); the add_test entries below are for
# local ctest use and read the same arguments from environment variables
# set by the conan VirtualRunEnv (UNIDIC_EXT_DICDIR / MECAB_TEST_RCFILE).
add_test(NAME test_package COMMAND test_package
         $ENV{UNIDIC_EXT_DICDIR} $ENV{MECAB_TEST_RCFILE})
add_test(NAME ohos_specific_test COMMAND ohos_specific_test
         $ENV{UNIDIC_EXT_DICDIR} $ENV{MECAB_TEST_RCFILE})
