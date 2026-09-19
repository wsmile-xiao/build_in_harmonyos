cmake_minimum_required(VERSION 3.15)
project(drogon_test CXX)

find_package(Drogon REQUIRED CONFIG)

add_executable(test_drogon test.cpp)
target_link_libraries(test_drogon PRIVATE Drogon::Drogon)
target_compile_features(test_drogon PRIVATE cxx_std_17)

# OHOS: link libc++ explicitly for stdlib symbols (toolchain only adds
# -stdlib=libc++ at compile time, not link time)
target_link_libraries(test_drogon PRIVATE c++)

enable_testing()
add_test(NAME drogon_test COMMAND test_drogon)
