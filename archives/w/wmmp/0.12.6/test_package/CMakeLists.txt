cmake_minimum_required(VERSION 3.20)
project(wmmp_test_package C)

# wmmp exposes no headers or libraries (pure CLI tool); the CONFIG dependency
# makes the build fail hard if the package is missing or its CMakeDeps config
# is broken.  The consumer driver locates WMmp through the WMMP_BIN
# environment variable set by test_package/conanfile.py at run time.
find_package(wmmp CONFIG REQUIRED)

add_executable(wmmp_consumer wmmp_consumer.c)
target_compile_options(wmmp_consumer PRIVATE -Werror)
