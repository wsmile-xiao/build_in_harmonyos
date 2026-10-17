cmake_minimum_required(VERSION 3.15)
project(trantor_test CXX)

find_package(Trantor REQUIRED CONFIG)

add_executable(test_trantor test.cpp)
target_link_libraries(test_trantor PRIVATE Trantor::Trantor)
target_compile_features(test_trantor PRIVATE cxx_std_17)

# OHOS: link libc++ explicitly for stdlib symbols (toolchain only adds
# -stdlib=libc++ at compile time, not link time)
target_link_libraries(test_trantor PRIVATE c++)

enable_testing()
add_test(NAME trantor_test COMMAND test_trantor)
