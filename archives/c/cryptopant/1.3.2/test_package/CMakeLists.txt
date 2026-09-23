cmake_minimum_required(VERSION 3.15)
project(test_cryptopant C)

find_package(cryptopant CONFIG REQUIRED)

add_executable(test_cryptopant test_cryptopant.c)
target_link_libraries(test_cryptopant PRIVATE cryptopant::cryptopant)
# Also link crypto explicitly for static case (Conan deps bring it, but ensure)
find_package(OpenSSL REQUIRED)
target_link_libraries(test_cryptopant PRIVATE OpenSSL::Crypto)
