cmake_minimum_required(VERSION 3.15)
project(test_libgeoip C)

# Find packages via Conan-generated CMakeDeps
find_package(libgeoip REQUIRED)

# Consumer functional test: mirrors upstream test-geoip.c flow against the
# conan-packaged libGeoIP (61-IP country vector set, memory + fs cache).
add_executable(test_geoip test_geoip.c)
target_link_libraries(test_geoip libgeoip::libgeoip)

# HarmonyOS-specific test (rule12): page size / musl stdio paths / custom dir
add_executable(test_geoip_ohos test_geoip_ohos.c)
target_link_libraries(test_geoip_ohos libgeoip::libgeoip)

enable_testing()
add_test(NAME test_geoip
         COMMAND test_geoip ${CMAKE_CURRENT_SOURCE_DIR}/GeoIP.dat
                              ${CMAKE_CURRENT_SOURCE_DIR}/country_test.txt)
add_test(NAME test_geoip_ohos
         COMMAND test_geoip_ohos ${CMAKE_CURRENT_SOURCE_DIR}/GeoIP.dat)
