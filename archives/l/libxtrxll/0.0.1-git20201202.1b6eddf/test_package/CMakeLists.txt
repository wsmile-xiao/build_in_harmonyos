cmake_minimum_required(VERSION 3.15)
project(test_libxtrxll C)

# Package discovery is provided by the Conan-generated CMakeDeps files
# (find_package(libxtrxll) + libxtrxll::libxtrxll).
find_package(libxtrxll REQUIRED)

# Consumer integration test: public API surface, device independent.
add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer PRIVATE libxtrxll::libxtrxll)

# HarmonyOS-specific test: static plugin registration and operation on a host
# without the XTRX kernel driver / hardware.
add_executable(test_ohos_offline test_ohos_offline.c)
target_link_libraries(test_ohos_offline PRIVATE libxtrxll::libxtrxll ${CMAKE_DL_LIBS})
