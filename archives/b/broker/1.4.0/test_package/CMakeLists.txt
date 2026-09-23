cmake_minimum_required(VERSION 3.16)
project(test_broker LANGUAGES CXX)
# Consumer test cases for broker/1.4.0: 7 cases, 30 assertions total
# (counts synced with test_broker.cpp header, MANIFEST.yml, conanfile.py
# docstring and the PR description).

find_package(broker CONFIG REQUIRED)
find_package(Threads REQUIRED)

add_executable(test_broker test_broker.cpp)
target_compile_features(test_broker PRIVATE cxx_std_17)
target_link_libraries(test_broker PRIVATE broker::broker Threads::Threads)

enable_testing()
add_test(NAME t_broker_version COMMAND test_broker version)
add_test(NAME t_broker_roundtrip COMMAND test_broker roundtrip)
add_test(NAME t_broker_filter COMMAND test_broker filter)
add_test(NAME t_broker_burst COMMAND test_broker burst)
add_test(NAME t_broker_store COMMAND test_broker store)
add_test(NAME t_broker_peer_error COMMAND test_broker peer_error)
add_test(NAME t_broker_status COMMAND test_broker status)
set_tests_properties(
  t_broker_roundtrip t_broker_filter t_broker_burst
  t_broker_store t_broker_peer_error t_broker_status
  PROPERTIES TIMEOUT 60)
