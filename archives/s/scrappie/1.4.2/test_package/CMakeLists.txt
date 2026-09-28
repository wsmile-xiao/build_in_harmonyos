cmake_minimum_required(VERSION 3.15)
project(test_scrappie C)

# Fully static consumer: OHOS HMDFS exec hardening forbids processes with
# their binary on /storage from loading DSOs from the conan store.
add_executable(test_scrappie test.c)
target_include_directories(test_scrappie PRIVATE
    "${SCRAPPIE_PKG}/include"
    "${SCRAPPIE_PKG}/include/sse2neon_compat")
target_link_libraries(test_scrappie ${SCRAPPIE_STATIC_LIBS} m)

enable_testing()
add_test(NAME test_scrappie COMMAND test_scrappie)
